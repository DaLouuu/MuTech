import os, glob, pickle, numpy as np, soundfile as sf, librosa, scipy.signal, time
import os
D=os.environ.get("CSD_DIR","./umss/Datasets/ChoralSingingDataset")
OUT=os.path.dirname(os.path.abspath(__file__))+"/data"
SR=22050; HOP=256; CROP=30.0
rng=np.random.default_rng(7)
songs={"locus":"Locus_Iste","rossinyol":"El_Rossinyol","nino":"Nino_Dios"}
parts={"S":"soprano","A":"contraalt","T":"tenor","B":"bajos"}
def stems(song):
    fs=glob.glob(f"{D}/{songs[song]}/audio_16kHz/*.wav")
    return {p:sorted(f for f in fs if parts[p] in os.path.basename(f).lower()) for p in parts}
def load(f,start):
    x,sr=sf.read(f,dtype="float32"); x=librosa.resample(x,orig_sr=sr,target_sr=SR)
    a=int(start*SR); return x[a:a+int(CROP*SR)]
gt_cache={}
def gt_f0(f,start):
    k=(f,start)
    if k not in gt_cache:
        x=load(f,start)
        f0,vf,vp=librosa.pyin(x,fmin=librosa.note_to_hz("C2"),fmax=librosa.note_to_hz("C6"),sr=SR,frame_length=2048,hop_length=HOP,fill_na=np.nan)
        f0=np.where(vf&(vp>0.7),f0,np.nan); gt_cache[k]=f0
    return gt_cache[k]
def mix(xs): 
    n=min(len(x) for x in xs); m=sum(x[:n] for x in xs); return m/ (np.abs(m).max()+1e-9)*0.5
def ir(rt60=1.2,sr=SR):
    n=int(rt60*sr); t=np.arange(n)/sr; h=np.random.default_rng(1).standard_normal(n)*10**(-3*t/rt60); h[0]=1.0; return h/np.abs(h).max()
def reverb(x,wet=0.4):
    y=scipy.signal.fftconvolve(x,ir())[:len(x)]; y=(1-wet)*x+wet*y*np.std(x)/ (np.std(y)+1e-9); return y/np.abs(y).max()*0.5
def noise(x,snr):
    p=np.mean(x**2); n=np.random.default_rng(3).standard_normal(len(x))*np.sqrt(p/10**(snr/10)); y=x+n; return y/np.abs(y).max()*0.5
def detune(x,cents): return librosa.effects.pitch_shift(x,sr=SR,n_steps=cents/100.0)
tests={}   # name -> dict(wav, gt: list of (part, f0 array), info)
def build(name,song,singers,start,voices=("S","A","T","B"),shift=None,post=None,info=""):
    st=stems(song); xs=[]; gts=[]
    for p in voices:
        f=st[p][singers[p]]; x=load(f,start); g=gt_f0(f,start).copy()
        if shift and p in shift: x=detune(x,shift[p]); g=g*2**(shift[p]/1200)
        xs.append(x); gts.append((p,g))
    m=mix(xs)
    if post: m=post(m)
    wav=f"{OUT}/{name}.wav"; sf.write(wav,m,SR)
    tests[name]=dict(wav=wav,gt=gts,info=info,song=song,voices=voices)
    print(name,info,flush=True)
t0=time.time()
base=[]
for i,song in enumerate(["locus","rossinyol","nino","locus","rossinyol","nino"]):
    sing={p:int(rng.integers(0,4)) for p in parts}; start=float(rng.integers(12,60))
    nm=f"B{i+1:02d}"; build(nm,song,sing,start,info=f"clean SATB {song} singers={sing} start={start}"); base.append((nm,song,sing,start))
b1,b2,b3,b4=base[0],base[1],base[2],base[3]
def re(b,name,**kw): build(name,b[1],b[2],b[3],**kw)
re(b1,"N20",post=lambda m:noise(m,20),info="B01 + white noise 20 dB SNR")
re(b1,"N10",post=lambda m:noise(m,10),info="B01 + white noise 10 dB SNR")
re(b1,"N00",post=lambda m:noise(m,0),info="B01 + white noise 0 dB SNR")
re(b1,"R12",post=reverb,info="B01 + synthetic reverb RT60 1.2 s")
re(b4,"R12b",post=reverb,info="B04 + synthetic reverb RT60 1.2 s")
re(b2,"DET",shift={"A":+30,"B":-25},info="B02 with alto +30 cents, bass -25 cents")
re(b3,"P2",voices=("S","B"),info="B03 two voices S+B")
re(b3,"P3",voices=("S","T","B"),info="B03 three voices S+T+B")
pickle.dump(tests,open(f"{OUT}/tests.pkl","wb"))
print("done",len(tests),"tests in %.0fs"%(time.time()-t0))
