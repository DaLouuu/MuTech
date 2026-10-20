import os, sys, time, pickle, numpy as np, h5py
os.environ["TF_CPP_MIN_LOG_LEVEL"]="3"
import keras, tensorflow as tf
from keras import layers
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.environ.get("MF0_REPO","./multif0-estimation-polyvocals")
bn=[0]
def BN():
    bn[0]+=1; return layers.BatchNormalization(name=f"batch_normalization_{bn[0]}")
def base(x,let):
    x=BN()(x)
    for nm,f,k in [("conv1",16,(5,5)),("conv2",32,(5,5)),("conv3",32,(5,5)),("conv4",32,(5,5)),("harm1",32,(70,3)),("harm2",32,(70,3))]:
        x=layers.Conv2D(f,k,padding="same",activation="relu",name=nm+let)(x); x=BN()(x)
    return x
def build():
    i1=keras.Input((None,None,5)); i2=keras.Input((None,None,5))
    c=layers.Concatenate()([base(i1,"a"),base(i2,"b")])
    x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv7")(c); x=BN()(x)
    x=layers.Conv2D(64,(3,3),padding="same",activation="relu",name="conv8")(x); x=BN()(x)
    x=layers.Conv2D(8,(360,1),padding="same",activation="relu",name="distribution")(x); x=BN()(x)
    x=layers.Conv2D(1,(1,1),padding="same",activation="sigmoid",name="squishy")(x)
    return keras.Model([i1,i2],layers.Lambda(lambda z: tf.squeeze(z,axis=3))(x))
m=build(); f=h5py.File(f"{REPO}/models/exp3multif0.pkl","r")["model_weights"]
for L in m.layers:
    if L.name in f:
        g=f[L.name][L.name]
        if isinstance(L,layers.Conv2D): L.set_weights([g["kernel:0"][()],g["bias:0"][()]])
        elif isinstance(L,layers.BatchNormalization): L.set_weights([g["gamma:0"][()],g["beta:0"][()],g["moving_mean:0"][()],g["moving_variance:0"][()]])
import pumpp
pump=pumpp.Pump(pumpp.feature.HCQTPhaseDiff(name='dphase',sr=22050,hop_length=256,fmin=32.7,n_octaves=6,over_sample=5,harmonics=[1,2,3,4,5],log=True))
tests=pickle.load(open(f"{HERE}/data/tests.pkl","rb")); res={}
for name,t in tests.items():
    t0=time.time(); d=pump(audio_f=t["wav"]); t1=time.time()
    mag=d['dphase/mag'][0].transpose(1,2,0)[None]; dph=d['dphase/dphase'][0].transpose(1,2,0)[None]
    outs=[m.predict([np.transpose(mag[:,:,s:s+5000,:],(0,1,3,2)),np.transpose(dph[:,:,s:s+5000,:],(0,1,3,2))],verbose=0)[0] for s in range(0,mag.shape[2],5000)]
    act=np.hstack(outs).astype(np.float16); t2=time.time()
    np.savez_compressed(f"{HERE}/out/mf0_{name}.npz",act=act,feat_s=t1-t0,infer_s=t2-t1)
    print(name,act.shape,"feat %.1fs infer %.1fs"%(t1-t0,t2-t1),flush=True)
