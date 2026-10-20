"""Ported multif0 (Cuesta et al. 2020, model3) as a reusable service."""
import os, time, numpy as np, h5py, scipy.signal, librosa
os.environ["TF_CPP_MIN_LOG_LEVEL"]="3"
import keras, tensorflow as tf
from keras import layers
import pumpp
REPO=os.environ.get("MF0_REPO","./multif0-estimation-polyvocals")
FREQS=librosa.cqt_frequencies(360,fmin=32.7,bins_per_octave=60); HOP=256; SR=22050
def _build():
    bn=[0]
    def BN():
        bn[0]+=1; return layers.BatchNormalization(name=f"batch_normalization_{bn[0]}")
    def base(x,let):
        x=BN()(x)
        for nm,f,k in [("conv1",16,(5,5)),("conv2",32,(5,5)),("conv3",32,(5,5)),("conv4",32,(5,5)),("harm1",32,(70,3)),("harm2",32,(70,3))]:
            x=layers.Conv2D(f,k,padding="same",activation="relu",name=nm+let)(x); x=BN()(x)
        return x
    i1=keras.Input((None,None,5)); i2=keras.Input((None,None,5))
    c=layers.Concatenate()([base(i1,"a"),base(i2,"b")])
    x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv7")(c); x=BN()(x)
    x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv8")(x); x=BN()(x)
    x=layers.Conv2D(8,(360,1),padding="same",activation="relu",name="distribution")(x); x=BN()(x)
    x=layers.Conv2D(1,(1,1),padding="same",activation="sigmoid",name="squishy")(x)
    return keras.Model([i1,i2],layers.Lambda(lambda z: tf.squeeze(z,axis=3))(x))
_model=None; _pump=None
def load():
    global _model,_pump
    if _model is not None: return
    m=_build(); f=h5py.File(f"{REPO}/models/exp3multif0.pkl","r")["model_weights"]
    for L in m.layers:
        if L.name in f:
            g=f[L.name][L.name]
            if isinstance(L,layers.Conv2D): L.set_weights([g["kernel:0"][()],g["bias:0"][()]])
            elif isinstance(L,layers.BatchNormalization): L.set_weights([g["gamma:0"][()],g["beta:0"][()],g["moving_mean:0"][()],g["moving_variance:0"][()]])
    _model=m
    _pump=pumpp.Pump(pumpp.feature.HCQTPhaseDiff(name='dphase',sr=SR,hop_length=HOP,fmin=32.7,n_octaves=6,over_sample=5,harmonics=[1,2,3,4,5],log=True))
def activations(path_or_y):
    load()
    d=_pump(audio_f=path_or_y) if isinstance(path_or_y,str) else _pump(y=path_or_y,sr=SR)
    mag=d['dphase/mag'][0].transpose(1,2,0)[None]; dph=d['dphase/dphase'][0].transpose(1,2,0)[None]
    outs=[_model.predict([np.transpose(mag[:,:,s:s+5000,:],(0,1,3,2)),np.transpose(dph[:,:,s:s+5000,:],(0,1,3,2))],verbose=0)[0] for s in range(0,mag.shape[2],5000)]
    return np.hstack(outs)
def peaks(act,thr=0.5):
    pk=scipy.signal.argrelmax(act,axis=0); m=np.zeros_like(act); m[pk]=act[pk]
    fb,tb=np.where(m>=thr); est=[[] for _ in range(act.shape[1])]
    for f,t in zip(fb,tb): est[t].append(float(FREQS[f]))
    return est
def transcribe(path,thr=0.5,hop=1):
    t0=time.time(); act=activations(path); est=peaks(act,thr); dt=time.time()-t0
    times=librosa.frames_to_time(np.arange(act.shape[1]),sr=SR,hop_length=HOP)
    return {"sample_rate":SR,"hop_s":HOP/SR,"threshold":thr,"n_frames":int(act.shape[1]),
            "frames":[{"t":round(float(times[i]),4),"f0":[round(x,2) for x in est[i]]} for i in range(0,len(est),hop)],
            "process_s":round(dt,2)}
