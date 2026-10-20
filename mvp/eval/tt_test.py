import os,sys,time,numpy as np,torch,soundfile as sf,librosa
sys.path.insert(0,os.environ.get("TT_REPO","./timbre-trap"))
from timbre_trap.framework import TimbreTrap
model=TimbreTrap(sample_rate=22050,n_octaves=9,bins_per_octave=60,secs_per_block=3,latent_size=128,model_complexity=2,skip_connections=False)
sd=torch.load(os.environ.get("TT_WEIGHTS","tt-orig.pt"),map_location="cpu"); print("keys ok:",model.load_state_dict(sd))
model.eval()
audio,sr=sf.read("../test_chord.wav"); audio=librosa.resample(audio.astype(np.float32),orig_sr=sr,target_sr=22050) if sr!=22050 else audio.astype(np.float32)
x=torch.from_numpy(audio)[None,None]  # (B,C,T)
t0=time.time()
with torch.no_grad(): tr=model.transcribe(x)
print("transcribe out",tuple(tr.shape),"max %.3f"%float(tr.max()),"time %.1fs"%(time.time()-t0))
act=tr[0].numpy() if tr.ndim==3 else tr.numpy()
act=np.squeeze(act); print("act",act.shape)
fmin=11025/2**9; freqs=fmin*2**(np.arange(540)/60)
print("freq bins:",None if freqs is None else (len(freqs),freqs[0],freqs[-1]))
if freqs is not None:
    freqs=np.asarray(freqs); T=act.shape[-1]; mid=slice(T//4,3*T//4)
    for tgt in [130.81,196.0,261.63,329.63]:
        b=np.argmin(np.abs(freqs-tgt)); lo=max(0,b-3); hi=b+4
        print(f"target {tgt:7.2f}: mean activation near bin {act[lo:hi,mid].max(axis=0).mean():.2f}")
    thr=act[:,mid]>0.5; print("mean #bins active/frame:",thr.sum(0).mean())
