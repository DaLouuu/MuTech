import time, json, os, sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

t0 = time.time()
import app as A

with TestClient(A.app) as c:
    print("startup+load %.1fs" % (time.time() - t0))
    print(c.get("/health").json())

    base = BACKEND_DIR
    candidates = [
        base / ".." / "frontend" / "sample_audio.wav",
        base / ".." / "eval" / "data" / "B01.wav",
    ]
    w = next((p for p in candidates if p.is_file()), None)

    if w:
        for thr, hop in [(0.5, 1), (0.7, 1)]:
            t = time.time()
            with open(w, "rb") as f:
                r = c.post(
                    f"/transcribe?threshold={thr}&hop={hop}",
                    files={"file": (w.name, f, "audio/wav")},
                )
            el = time.time() - t
            if r.status_code == 200:
                j = r.json()
                print(r.status_code, "thr", thr, "frames", j["n_frames"], "process_s", j["process_s"], "roundtrip %.1fs" % el, "bytes", len(r.content))
            else:
                print("Transcribe status:", r.status_code, r.text)

    r = c.post("/transcribe", files={"file": ("x.txt", b"hi", "text/plain")})
    print("bad type status (expected 415):", r.status_code)
