"""FastAPI MIR MVP Backend Server (multif0 Port & Choir Intonation Studio).

Implements Checklist Phase 1.4 & Phase 3.4 with production hardening:
- 1.4.1 Worker threadpool offloading and inference concurrency limiter
- 1.4.2 In-memory job manager, rate/capacity guards, and GET /jobs/{job_id}
- 1.4.3 Modern @asynccontextmanager lifespan & detailed /health probe
- 3.4.1 Structured CSV export endpoint POST /export/csv
- 3.4.2 Standard MIDI Type 1 export endpoint POST /export/midi
- Memory exhaustion DoS guards (streaming chunk reader) and CORS security
"""

import os
import time
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Any

import psutil
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, BackgroundTasks, Response
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import mf0_service as svc
from audio_processor import AudioProcessingError, MAX_FILE_SIZE_BYTES
from job_manager import job_manager, JobLimitExceededError
from analytics import generate_csv_export
from midi_exporter import generate_midi_type1

START_TIME = time.time()
MAX_CONCURRENT_INFERENCE = int(os.environ.get("MAX_CONCURRENT_INFERENCE", "2"))
_inference_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INFERENCE)


class ExportCsvRequest(BaseModel):
    frames: list[dict[str, Any]] = Field(..., max_length=60000, description="List of transcription frames")
    contours: Optional[list[dict[str, Any]]] = Field(default=None, max_length=500, description="Linked contour tracks")


class ExportMidiRequest(BaseModel):
    contours: list[dict[str, Any]] = Field(..., min_length=1, max_length=500, description="List of vocal contours")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan context manager to initialize model and run background cleanups."""
    try:
        # Pre-warm model in background thread
        await asyncio.to_thread(svc.load)
    except Exception as e:
        print(f"Startup warning (multif0 weights): {e}")

    # Background task for periodic job TTL memory cleanup (every 5 minutes)
    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(300)
            try:
                job_manager.cleanup_expired()
            except Exception:
                pass

    cleanup_task = asyncio.create_task(_periodic_cleanup())
    yield
    cleanup_task.cancel()


app = FastAPI(
    title="Choir Pitch Tracker & Intonation Studio API",
    description="multif0 polyphonic vocal pitch tracking and ensemble intonation analytics backend.",
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Inference", "description": "Polyphonic choral multi-pitch transcription"},
        {"name": "Jobs", "description": "Asynchronous job polling and progress tracking"},
        {"name": "Presets", "description": "Pre-computed benchmark demonstrations for instant exploration"},
        {"name": "Export", "description": "Structured CSV and Standard MIDI (Type 1) data export"},
        {"name": "System", "description": "Health checks, resource utilization, and model diagnostics"},
    ],
)

# CORS Configuration with browser security standards
_origins_env = os.environ.get("CORS_ORIGINS", "*").strip()
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
_allow_credentials = False if _origins == ["*"] else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health():
    """Detailed health probe returning system resources, uptime, model state, and queue depth."""
    mem = psutil.virtual_memory()
    proc = psutil.Process()
    return {
        "status": "ok",
        "service": "Choir Pitch Tracker & Intonation Studio",
        "uptime_s": round(time.time() - START_TIME, 1),
        "model": svc.get_model_status(),
        "concurrency": {
            "max_concurrent_inferences": MAX_CONCURRENT_INFERENCE,
            "active_async_jobs": job_manager.active_job_count(),
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": mem.percent,
            "memory_available_mb": round(mem.available / (1024 * 1024), 1),
            "process_memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
        },
    }


def _process_transcription_job(
    job_id: str,
    file_bytes: bytes,
    filename: str,
    threshold: float,
    hop: int,
    link_contours: bool,
):
    """Background worker for asynchronous transcription processing with incremental progress reporting."""
    try:
        def on_progress(pct: float):
            job_manager.update_progress(job_id, pct, "processing")

        result = svc.transcribe(
            file_bytes,
            filename=filename,
            threshold=threshold,
            hop=hop,
            link_voice_contours=link_contours,
            progress_callback=on_progress,
        )
        job_manager.complete_job(job_id, result)
    except Exception as e:
        job_manager.fail_job(job_id, str(e))


async def _read_file_safely(file: UploadFile) -> bytes:
    """Read upload stream in chunks with size limit to prevent memory exhaustion DoS."""
    chunk_size = 1024 * 1024  # 1 MB chunk
    chunks = []
    total_bytes = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size limit ({MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB).",
            )
        chunks.append(chunk)

    return b"".join(chunks)


@app.post("/transcribe", tags=["Inference"])
async def transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    threshold: float = Query(0.5, ge=0.1, le=0.95, description="Salience peak threshold"),
    hop: int = Query(1, ge=1, le=20, description="Frame hop sub-sampling factor"),
    link_contours: bool = Query(True, description="Whether to compute linked vocal trajectories"),
    async_mode: bool = Query(False, description="Run in background and poll via /jobs/{job_id}"),
):
    """Transcribe polyphonic choir audio file.

    Supports synchronous response or async job polling for long files.
    """
    safe_filename = os.path.basename(file.filename or "audio.wav")
    file_bytes = await _read_file_safely(file)

    if async_mode:
        try:
            job = job_manager.create_job()
        except JobLimitExceededError as e:
            raise HTTPException(status_code=429, detail=str(e))

        background_tasks.add_task(
            _process_transcription_job,
            job.job_id,
            file_bytes,
            safe_filename,
            threshold,
            hop,
            link_contours,
        )
        return {"job_id": job.job_id, "status": "processing", "poll_url": f"/jobs/{job.job_id}"}

    # Synchronous processing with concurrency semaphore
    async with _inference_semaphore:
        try:
            result = await asyncio.to_thread(
                svc.transcribe,
                file_bytes,
                filename=safe_filename,
                threshold=threshold,
                hop=hop,
                link_voice_contours=link_contours,
            )
            return result
        except AudioProcessingError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except RuntimeError as e:
            err_msg = str(e)
            if "model is not loaded" in err_msg.lower() or "weights" in err_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail=f"multif0 model weights are not loaded. Run 'python download_weights.py' to acquire weights. Details: {err_msg}",
                )
            raise HTTPException(status_code=500, detail=err_msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}", tags=["Jobs"])
def get_job_status(job_id: str):
    """Poll the status and result of an asynchronous transcription job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job.to_dict()


@app.get("/jobs/{job_id}/events", tags=["Jobs"])
async def stream_job_events(job_id: str):
    """Stream real-time job progress and completion events via Server-Sent Events (SSE).

    Allows web clients to listen to progress changes via browser EventSource.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    import json

    async def event_generator():
        last_progress = -1.0
        last_status = ""
        while True:
            current_job = job_manager.get_job(job_id)
            if not current_job:
                yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            # If progress or status changed, yield event
            if current_job.progress != last_progress or current_job.status != last_status:
                last_progress = current_job.progress
                last_status = current_job.status
                payload = {
                    "job_id": current_job.job_id,
                    "status": current_job.status,
                    "progress": round(current_job.progress, 1),
                }

                if current_job.status == "completed":
                    payload["result"] = current_job.result
                    yield f"event: complete\ndata: {json.dumps(payload)}\n\n"
                    break
                elif current_job.status == "failed":
                    payload["error"] = current_job.error
                    yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                    break
                else:
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/export/csv", response_class=PlainTextResponse, tags=["Export"])
def export_csv(req: ExportCsvRequest):
    """Generate structured CSV from validated transcription JSON payload."""
    csv_text = generate_csv_export(req.frames, req.contours)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transcription.csv"'},
    )


@app.post("/export/midi", tags=["Export"])
def export_midi(req: ExportMidiRequest, tempo_bpm: int = Query(120, ge=40, le=240)):
    """Generate multi-track Standard MIDI Type 1 file from vocal contours."""
    midi_bytes = generate_midi_type1(req.contours, tempo_bpm=tempo_bpm)
    return Response(
        content=midi_bytes,
        media_type="audio/midi",
        headers={"Content-Disposition": 'attachment; filename="transcription.mid"'},
    )


# Directory containing preloaded demo files
PRESETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


@app.get("/presets", tags=["Presets"])
def list_presets():
    """List preloaded demonstration audio and transcription presets (Checklist 2.6.1)."""
    return [
        {
            "id": "bach_chorale_satb",
            "title": "CSD Bach Chorale (SATB 4-part Choir)",
            "description": "Polyphonic choral testing benchmark from the Choral Singing Dataset",
            "duration_s": 6.0,
            "has_audio": os.path.exists(os.path.join(PRESETS_DIR, "sample_audio.wav")),
            "audio_url": "/presets/bach_chorale_satb/audio",
        }
    ]


@app.get("/presets/{preset_id}", tags=["Presets"])
def get_preset_transcription(preset_id: str):
    """Fetch pre-computed transcription JSON for instant zero-compute exploration."""
    if preset_id != "bach_chorale_satb":
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found.")

    json_path = os.path.join(PRESETS_DIR, "sample_transcription.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Preset transcription file missing.")

    import json
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/presets/{preset_id}/audio", tags=["Presets"])
def get_preset_audio(preset_id: str):
    """Stream demonstration audio file."""
    if preset_id != "bach_chorale_satb":
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found.")

    audio_path = os.path.join(PRESETS_DIR, "sample_audio.wav")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Preset audio file missing.")

    return FileResponse(audio_path, media_type="audio/wav", filename="bach_chorale_satb.wav")

