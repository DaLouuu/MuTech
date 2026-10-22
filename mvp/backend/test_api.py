import time, json, glob
from fastapi.testclient import TestClient
t0=time.time()
import app as A
with TestClient(A.app) as c:
    print("startup+load %.1fs"%(time.time()-t0))
    print(c.get("/health").json())
    w=f"{A.__file__.rsplit('/',1)[0]}/../eval/data/B01.wav"
    for thr,hop in [(0.5,1),(0.7,1)]:
        t=time.time(); r=c.post(f"/transcribe?threshold={thr}&hop={hop}",files={"file":("B01.wav",open(w,"rb"),"audio/wav")}); el=time.time()-t
        j=r.json(); print(r.status_code,"thr",thr,"frames",j["n_frames"],"process_s",j["process_s"],"roundtrip %.1fs"%el,"bytes",len(r.content))
    print(json.dumps(j["frames"][1000:1003]))
    r=c.post("/transcribe",files={"file":("x.txt",b"hi","text/plain")}); print("bad type",r.status_code)
