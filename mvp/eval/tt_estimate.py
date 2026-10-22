import os, sys, time, pickle, numpy as np, torch, soundfile as sf
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.environ.get("TT_REPO","./timbre-trap"))
from timbre_trap.framework import TimbreTrap
model=TimbreTrap(sample_rate=22050,n_octaves=9,bins_per_octave=60,secs_per_block=3,latent_size=128,model_complexity=2,skip_connections=False)
model.load_state_dict(torch.load(os.environ.get("TT_WEIGHTS",f"{HERE}/tt-orig.pt"),map_location="cpu")); model.eval()
tests=pickle.load(open(f"{HERE}/data/tests.pkl","rb"))
for name,t in tests.items():
    x,sr=sf.read(t["wav"],dtype="float32"); assert sr==22050
    t0=time.time()
    with torch.no_grad(): tr=model.transcribe(torch.from_numpy(x)[None,None])
    dt=time.time()-t0; act=tr[0].numpy().astype(np.float16)
    np.savez_compressed(f"{HERE}/out/tt_{name}.npz",act=act,infer_s=dt)
    print(name,act.shape,"infer %.1fs"%dt,flush=True)
