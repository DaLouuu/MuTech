import os, sys, time, numpy as np, h5py, soundfile as sf
os.environ["TF_CPP_MIN_LOG_LEVEL"]="3"
import keras
from keras import layers
import tensorflow as tf
S=os.path.dirname(os.path.abspath(__file__))
REPO=os.environ.get("MF0_REPO","./multif0-estimation-polyvocals")
# ---------- synthetic 4-voice test audio (runnability check only) ----------
sr=22050; dur=6.0; t=np.arange(int(sr*dur))/sr
notes=[130.81,196.00,261.63,329.63]  # C3 G3 C4 E4
mix=np.zeros_like(t)
rng=np.random.default_rng(0)
for f0 in notes:
    vib=1+0.0086*np.sin(2*np.pi*(5.3+rng.random()*0.6)*t+rng.random()*6)  # ~±15 cents
    ph=2*np.pi*np.cumsum(f0*vib)/sr
    v=sum(np.sin(h*ph)/h**1.1 for h in range(1,9))
    mix+=v*np.minimum(1,t/0.2)
mix=0.3*mix/np.abs(mix).max()
wav=f"{S}/test_chord.wav"; sf.write(wav,mix.astype(np.float32),sr)
# ---------- model3 rebuilt in Keras 3 ----------
bn_i=[0]
def BN():
    bn_i[0]+=1; return layers.BatchNormalization(name=f"batch_normalization_{bn_i[0]}")
def base(x,let):
    x=BN()(x)
    for nm,f,k in [("conv1",16,(5,5)),("conv2",32,(5,5)),("conv3",32,(5,5)),("conv4",32,(5,5)),("harm1",32,(70,3)),("harm2",32,(70,3))]:
        x=layers.Conv2D(f,k,padding="same",activation="relu",name=nm+let)(x); x=BN()(x)
    return x
i1=keras.Input((None,None,5)); i2=keras.Input((None,None,5))
a=base(i1,"a"); b=base(i2,"b"); c=layers.Concatenate()([a,b])
x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv7")(c); x=BN()(x)
x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv8")(x); x=BN()(x)
x=layers.Conv2D(8,(360,1),padding="same",activation="relu",name="distribution")(x); x=BN()(x)
x=layers.Conv2D(1,(1,1),padding="same",activation="sigmoid",name="squishy")(x)
out=layers.Lambda(lambda z: tf.squeeze(z,axis=3))(x)
model=keras.Model([i1,i2],out)
# ---------- load legacy weights by name ----------
f=h5py.File(f"{REPO}/models/exp3multif0.pkl","r")["model_weights"]
n=0
for L in model.layers:
    if L.name in f:
        g=f[L.name][L.name]
        if isinstance(L,layers.Conv2D):
            L.set_weights([g["kernel:0"][()],g["bias:0"][()]])
        elif isinstance(L,layers.BatchNormalization):
            L.set_weights([g["gamma:0"][()],g["beta:0"][()],g["moving_mean:0"][()],g["moving_variance:0"][()]])
        n+=1
print("layers loaded:",n,"params:",model.count_params())
# ---------- features (original pumpp pipeline) ----------
sys.path.insert(0,REPO)
t0=time.time()
import pumpp
p=pumpp.Pump(pumpp.feature.HCQTPhaseDiff(name='dphase',sr=22050,hop_length=256,fmin=32.7,n_octaves=6,over_sample=5,harmonics=[1,2,3,4,5],log=True))
data=p(audio_f=wav)
mag=data['dphase/mag'][0].transpose(1,2,0)[None]; dph=data['dphase/dphase'][0].transpose(1,2,0)[None]
print("feature shapes",mag.shape,dph.shape,"feat time %.1fs"%(time.time()-t0))
t0=time.time()
outs=[]
for s in range(0,mag.shape[2],5000):
    outs.append(model.predict([np.transpose(mag[:,:,s:s+5000,:],(0,1,3,2)),np.transpose(dph[:,:,s:s+5000,:],(0,1,3,2))],verbose=0)[0])
act=np.hstack(outs).astype(np.float32); print("activation",act.shape,"max %.3f"%act.max(),"infer %.1fs"%(time.time()-t0))
# ---------- peak-pick like original ----------
import scipy.signal, librosa
freqs=librosa.cqt_frequencies(6*12*5,fmin=32.7,bins_per_octave=60)
peaks=scipy.signal.argrelmax(act,axis=0); m=np.zeros_like(act); m[peaks]=act[peaks]
idx=np.where(m>=0.5); est=[[] for _ in range(act.shape[1])]
for fb,tb in zip(*idx): est[tb].append(freqs[fb])
mid=slice(act.shape[1]//4,3*act.shape[1]//4)
cnt=[len(e) for e in est[mid]]; print("median #F0 per frame (mid segment):",np.median(cnt))
allf=np.concatenate([np.array(e) for e in est[mid] if len(e)])
for tgt in notes:
    near=allf[np.abs(1200*np.log2(allf/tgt))<50]
    print(f"target {tgt:7.2f} Hz -> detected in {len(near)/len(est[mid])*100:5.1f}% of frames, median {np.median(near) if len(near) else float('nan'):.2f} Hz")
