import tempfile, os, time
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mf0_service as svc
app=FastAPI(title="MIR MVP backend (multif0 ported)")
# Browsers block cross origin calls unless the origin is allowed. Set CORS_ORIGINS="http://localhost:5173,https://your.site" in production.
_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS","*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware,allow_origins=_origins,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def _warm(): svc.load()
@app.get("/health")
def health(): return {"status":"ok","model":"multif0 model3 (Keras 3 port)"}
@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), threshold: float = Query(0.5,ge=0.1,le=0.95), hop: int = Query(1,ge=1,le=20)):
    if not file.filename.lower().endswith((".wav",".flac",".ogg",".mp3")): raise HTTPException(415,"use wav/flac/ogg/mp3")
    data=await file.read()
    if len(data)>30_000_000: raise HTTPException(413,"file too large")
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1],delete=False) as f: f.write(data); p=f.name
    try: return svc.transcribe(p,threshold,hop)
    finally: os.unlink(p)
