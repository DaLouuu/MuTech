import os, pickle, json, numpy as np, scipy.signal, librosa, mir_eval, sys
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=f"{HERE}/out"
tests=pickle.load(open(f"{HERE}/data/tests.pkl","rb"))
MF_FREQS=librosa.cqt_frequencies(360,fmin=32.7,bins_per_octave=60)
TT_FREQS=(11025/2**9)*2**(np.arange(540)/60)
TT_HOP=6/2048*4   # max-pooled by 4 frames
def peaks(act,thr,freqs):
    a=act.astype(np.float32)
    pk=scipy.signal.argrelmax(a,axis=0); m=np.zeros_like(a); m[pk]=a[pk]
    fb,tb=np.where(m>=thr); est=[[] for _ in range(a.shape[1])]
    for f,t in zip(fb,tb): est[t].append(freqs[f])
    return [np.array(e) for e in est]
def load_est(model,name):
    z=np.load(f"{OUT}/{model}_{name}.npz"); a=z["act"]
    if model=="tt":
        T=a.shape[1]//4*4; a=a[:,:T].reshape(a.shape[0],-1,4).max(axis=2); times=np.arange(a.shape[1])*TT_HOP; fr=TT_FREQS
    else:
        times=librosa.frames_to_time(np.arange(a.shape[1]),sr=22050,hop_length=256); fr=MF_FREQS
    return a,times,fr,float(z["infer_s"]),float(z["feat_s"]) if "feat_s" in z else 0.0
def ref_of(t):
    n=max(len(g) for _,g in t["gt"]); times=librosa.frames_to_time(np.arange(n),sr=22050,hop_length=256)
    fr=[]
    for i in range(n):
        v=[g[i] for _,g in t["gt"] if i<len(g) and not np.isnan(g[i])]
        fr.append(np.array(v,dtype=float))
    return times,fr
def score(rt,rf,et,ef,tol=50):
    r=mir_eval.multipitch.evaluate(rt,rf,et,ef,cent_tolerance=tol) if tol!=50 else mir_eval.multipitch.evaluate(rt,rf,et,ef)
    P,R=r["Precision"],r["Recall"]; F=2*P*R/(P+R) if P+R>0 else 0.0
    return dict(P=P,R=R,F=F,Acc=r["Accuracy"],ChromaAcc=r["Chroma Accuracy"],Esub=r["Substitution Error"],Emiss=r["Miss Error"],Efa=r["False Alarm Error"])
def cents_err(t,rt,et,ef,tol=100):
    res={}
    est_t=np.asarray(et)
    for p,g in t["gt"]:
        errs=[]
        for i,f0 in enumerate(g):
            if np.isnan(f0): continue
            j=np.searchsorted(est_t,rt[i]); j=min(max(j,0),len(est_t)-1)
            e=ef[j]
            if len(e)==0: continue
            c=1200*np.log2(e/f0); k=np.argmin(np.abs(c))
            if abs(c[k])<=tol: errs.append(c[k])
        res[p]=np.array(errs)
    return res
results={"mf0":{}, "tt":{}}
THR={"mf0":[0.3,0.4,0.5,0.6,0.7],"tt":[0.3,0.5,0.7,0.8,0.9]}; DEF={"mf0":0.5,"tt":0.5}
for model in ["mf0","tt"]:
    for name,t in tests.items():
        if not os.path.exists(f"{OUT}/{model}_{name}.npz"): continue
        a,et,fr,inf,feat=load_est(model,name); rt,rf=ref_of(t)
        entry={"infer_s":inf,"feat_s":feat,"dur_s":30.0,"ref_poly":float(np.mean([len(x) for x in rf]))}
        entry["sweep"]={}
        for thr in THR[model]:
            ef=peaks(a,thr,fr); s=score(rt,rf,et,ef); s["est_poly"]=float(np.mean([len(x) for x in ef])); entry["sweep"][thr]=s
            if thr==DEF[model]:
                s100=score(rt,rf,et,ef,tol=100); entry["tol100"]=s100
                ce=cents_err(t,rt,et,ef)
                entry["cents"]={p:dict(n=int(len(v)),median=float(np.median(v)) if len(v) else None,mae=float(np.mean(np.abs(v))) if len(v) else None,std=float(np.std(v)) if len(v) else None) for p,v in ce.items()}
                entry["ref_frames_matched"]={p:float(len(ce[p])/max(1,np.sum(~np.isnan(dict(t['gt'])[p])))) for p in ce}
        results[model][name]=entry; print(model,name,"F@%.1f=%.3f"%(DEF[model],entry["sweep"][DEF[model]]["F"]),flush=True)
json.dump(results,open(f"{HERE}/results.json","w"),indent=1,default=float)
