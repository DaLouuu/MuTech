# Security, Concurrency & API Review Checklist for MuTech

This checklist is used when reviewing FastAPI endpoints, SSE streaming, file uploads, concurrency management, and container security.

---

## 1. FastAPI Route Architecture & Concurrency (`app.py`, `job_manager.py`)
- [ ] **Thread Pool Offloading for Sync Work**:
  Heavy DSP/ML tasks must never run synchronously on the async event loop.
  ```python
  # Good:
  result = await asyncio.to_thread(mf0_service.predict, audio_data)
  # Bad (blocks the entire server):
  result = mf0_service.predict(audio_data)
  ```
- [ ] **Concurrency Throttling**:
  - Multi-pitch estimation is GPU/CPU-intensive. Verify that a semaphore (e.g. `asyncio.Semaphore(2)`) restricts simultaneous model inferences to prevent server out-of-memory (OOM) crashes.
- [ ] **Server-Sent Events (SSE) Resilience**:
  - SSE endpoint (`/jobs/{id}/events`) must stream ping/heartbeat frames every 15–30 seconds to prevent reverse proxy timeouts (e.g. Nginx `proxy_read_timeout`).
  - Generators must handle client disconnects cleanly without raising unhandled `GeneratorExit` or leaking background tasks.
- [ ] **In-Memory Store Cleanup**:
  - Completed and failed jobs in `job_manager` must have a Time-To-Live (TTL, e.g. 1 hour).
  - Background task or periodic sweep must evict stale entries to prevent unbounded RAM growth.

---

## 2. Input Validation & File Handling
- [ ] **Payload Size Verification**:
  - HTTP `413 Payload Too Large` returned if upload exceeds `MAX_CONTENT_LENGTH` (e.g. 50 MB).
  - Check Content-Length header early before streaming large request bodies into memory.
- [ ] **MIME Type & Magic Byte Whitelist**:
  - Disallow arbitrary binary uploads. Validate MIME types: `audio/wav`, `audio/x-wav`, `audio/mpeg`, `audio/ogg`, `audio/flac`, `audio/mp4`.
  - Validate magic bytes header for `.wav` (`RIFF...WAVE`) and `.mp3` (`ID3` or `\xFF\xFB`).
- [ ] **Path Traversal Protection**:
  - Never trust filenames supplied by the client (`UploadFile.filename`).
  - Extract only sanitized extensions (`.wav`) and generate cryptographic or UUID names (`f"{uuid.uuid4()}{ext}"`).
  - Never format unvalidated strings into disk paths.

---

## 3. Error Handling & HTTP Status Codes
- [ ] **No Raw Tracebacks**:
  - Never allow unhandled Python tracebacks to leak internal directory paths, library versions, or environment keys in production responses.
- [ ] **Correct Status Codes**:
  - `400 Bad Request`: Invalid parameter (e.g., threshold outside $[0.0, 1.0]$).
  - `404 Not Found`: Non-existent job ID.
  - `413 Payload Too Large`: Audio file exceeding max size limit.
  - `415 Unsupported Media Type`: Non-audio file format.
  - `422 Unprocessable Entity`: Corrupt, un-decodable audio file.
  - `503 Service Unavailable`: Model weights missing or offline, returning remediation advice (`python download_weights.py`).

---

## 4. Docker & Infrastructure Security
- [ ] **Non-Root Execution**:
  - Multi-stage Dockerfile must define an unprivileged user (`appuser` with UID 1000) and switch via `USER appuser`.
- [ ] **Minimal Base Images**:
  - Use `python:3.11-slim` or `python:3.12-slim` to avoid unnecessary system binaries (compilers, debuggers) in production runtime.
- [ ] **CORS Configuration**:
  - Explicit origins whitelist. Avoid wildcard `allow_origins=["*"]` when credentials or cookies are enabled.
