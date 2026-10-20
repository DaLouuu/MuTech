# Back end guide

Audience: whoever builds and deploys the API (back end owner). Everything here describes code in [`../backend/`](../backend) as it stands today. Items marked **not built** are suggestions, not working code.

## 1. What the service does

```
audio file ──► load + resample to 22,050 Hz ──► features (harmonic CQT + phase differentials)
          ──► neural network (multif0 "model3") ──► salience map: 360 pitch bins x frames
          ──► pick local peaks above a threshold ──► per frame list of F0 values in Hz ──► JSON
```

- **Model.** multif0 Late/Deep ("model3"), about 1.25 million parameters, from Cuesta, McFee and Gómez (ISMIR 2020).
- **Frame rate.** One frame every 256 samples at 22,050 Hz, so 11.61 ms. 86.13 frames per second.
- **Pitch grid.** 360 bins, 60 per octave (20 cents each), starting at 32.7 Hz (C1) and spanning 6 octaves up to about 2,093 Hz.
- **Output.** For each frame, zero or more F0 values in Hz. It does not say which singer sang which pitch.

## 2. Files

| File | Role |
|---|---|
| `backend/mf0_service.py` | The model. `load()`, `activations()`, `peaks()`, `transcribe()` |
| `backend/app.py` | FastAPI app that exposes the service over HTTP |
| `backend/test_api.py` | Smoke test using FastAPI's test client |

### `mf0_service.py` in detail

| Function | What it does |
|---|---|
| `load()` | Builds the Keras 3 network, loads the weights from `$MF0_REPO/models/exp3multif0.pkl`, creates the feature extractor. Runs once; later calls do nothing |
| `activations(path_or_y)` | Audio path (or a waveform array) in, salience map `(360, n_frames)` out, values 0 to 1. Runs the network in blocks of 5,000 frames (about 58 s) |
| `peaks(act, thr=0.5)` | Keeps local maxima along the frequency axis whose value is at least `thr`. Returns a list (one entry per frame) of lists of Hz |
| `transcribe(path, thr=0.5, hop=1)` | The whole chain. Returns the JSON-ready dictionary described in section 4 |

## 3. Setup

Requirements: Python 3.12, Linux (tested), about 3 GB disk for TensorFlow. No GPU needed. Versions are pinned in [`../requirements.txt`](../requirements.txt).

```bash
git clone --depth 1 https://github.com/helenacuesta/multif0-estimation-polyvocals
export MF0_REPO="$PWD/multif0-estimation-polyvocals"     # where the weights are

python3.12 -m venv .venv && source .venv/bin/activate
pip install -r mvp/requirements.txt

cd mvp/backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

Interactive API docs are generated automatically at `http://localhost:8000/docs`.

### Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `MF0_REPO` | `./multif0-estimation-polyvocals` | Folder of the cloned original repo. Must contain `models/exp3multif0.pkl` |
| `CORS_ORIGINS` | `*` | Comma separated list of web origins allowed to call the API from a browser. **Set this to the real front end address before deploying** |

Limits hard coded in `app.py`: file types `.wav .flac .ogg .mp3`; maximum upload 30,000,000 bytes; `threshold` between 0.1 and 0.95; `hop` between 1 and 20.

## 4. API reference

### `GET /health`

Returns `{"status": "ok", "model": "multif0 model3 (Keras 3 port)"}`. Use it for liveness checks.

### `POST /transcribe`

Multipart form upload.

| Part | Where | Type | Default | Meaning |
|---|---|---|---|---|
| `file` | form field | file | required | Audio file |
| `threshold` | query | float 0.1 to 0.95 | 0.5 | Minimum salience for a peak to count as a pitch. Higher = fewer false pitches, more missed ones |
| `hop` | query | int 1 to 20 | 1 | Keep every n-th frame in the response. Use 2 to 4 to shrink the JSON |

Example:

```bash
curl -F "file=@choir.wav" "http://localhost:8000/transcribe?threshold=0.6&hop=2"
```

Response (shortened; the values in `frames` are illustrative):

```json
{
  "sample_rate": 22050,
  "hop_s": 0.011609977324263039,
  "threshold": 0.6,
  "n_frames": 2583,
  "frames": [
    {"t": 0.0,    "f0": []},
    {"t": 0.0232, "f0": [196.9, 392.4]},
    {"t": 0.0465, "f0": [196.9, 261.1, 392.4]}
  ],
  "process_s": 21.9
}
```

| Field | Meaning |
|---|---|
| `sample_rate` | Rate the audio was analysed at |
| `hop_s` | Seconds between analysis frames (before `hop` is applied) |
| `threshold` | Echo of the setting used |
| `n_frames` | Total frames in the file (before `hop`) |
| `frames[].t` | Time in seconds |
| `frames[].f0` | Pitches in Hz sounding at that time. Empty list = silence or nothing detected. Order is by frequency bin, low to high |
| `process_s` | Seconds the server spent on this request |

Errors: `415` unsupported file type, `413` file larger than 30 MB, `422` bad parameter.

Size and speed (measured, 2 CPU cores): a 30 second clip gives 2,583 frames and about 100 KB of JSON at `hop=1`, and takes about 22 seconds.

## 5. Tests that exist

`backend/test_api.py` starts the app in-process, checks `/health`, posts a 30 second clip at two thresholds, and checks that a `.txt` upload is rejected with 415. It expects the clip at `mvp/eval/data/B01.wav`, which `eval/prep_data.py` creates (see the [evaluation guide](EVALUATION_GUIDE.md)). Any WAV works if you edit the path.

```bash
cd mvp/backend && PYTHONPATH=. python test_api.py
```

## 6. How the port works (read before changing the model code)

The original code is Keras 2.3.1 on TensorFlow 1.15 and cannot run on Python 3.8 or newer. We did **not** change the model; we rebuilt the same layers in Keras 3 and loaded the original weights.

1. **Architecture** is rebuilt in `_build()`: two input branches (harmonic magnitude and phase differential), each with batch norm, four 5x5 convolutions and two harmonic convolutions (70x3 kernels), concatenated, then two 3x3 convolutions, a 360x1 "distribution" convolution, and a 1x1 sigmoid output.
2. **Weights** are in an HDF5 file with a `.pkl` extension (`models/exp3multif0.pkl`). Convolution layers are matched **by name** (`conv1a`, `conv1b`, `harm1a`, ...).
3. **Batch normalisation layers** are matched by name too, but their names (`batch_normalization_1` to `_17`) depend on **creation order** in the original. `_build()` creates them in the same order, using a counter. Do not reorder layer creation or the wrong statistics will load silently.
4. **Output squeeze** is a `Lambda` calling `tf.squeeze(axis=3)`.
5. **Features** come from `pumpp`'s `HCQTPhaseDiff` with: 22,050 Hz, hop 256, fmin 32.7 Hz, 6 octaves, oversampling 5, harmonics 1 to 5, log magnitude.

How we know it works: all 33 layers loaded (1,252,697 parameters); on a synthetic four voice chord every target pitch was found in 100% of frames within 50 cents; on real choir audio it reached F-measure 0.83 against pYIN references. We have **not** compared outputs frame by frame with the original TensorFlow 1.15 code, which could not be run. If anyone gets the original running, that comparison is the strongest remaining check (see [next steps](DECISIONS_AND_NEXT_STEPS.md)).

## 7. Known limitations and what to build next

| Limitation | Why it matters | Suggested fix |
|---|---|---|
| **No block overlap.** Files longer than about 58 s are processed in 5,000 frame blocks with no overlap | Possible glitches at block edges; never tested | Process blocks of about 30 s with a few seconds of overlap and cross-fade the activations |
| **One request blocks the server.** `transcribe()` is synchronous inside an async handler | While one clip is processing, others wait, including `/health` | Run the work in a thread pool, or better a job queue (submit, poll, fetch result) |
| **CPU cost** about 0.7x real time on 2 cores | A 5 minute song takes about 3.5 minutes | Queue plus a worker, or a GPU build of TensorFlow |
| **No authentication, no rate limit** | Anyone who can reach it can upload | Add before any public deployment |
| **CORS is `*` by default** | Convenient for development only | Set `CORS_ORIGINS` |
| **20 cent pitch grid** | Cents offsets can only be resolved to roughly 10 cents | Interpolate around each peak bin (parabolic fit on the three bins around the peak). Untested |
| **Output is unordered per frame** | Cannot draw one line per singer | Link pitches across frames into tracks (nearest pitch matching) as a first step; true voice assignment is research level |
| **Fixed global threshold** | Quiet passages lose notes | Expose per request (already done) and consider adaptive thresholds |
| `@app.on_event("startup")` is deprecated in newer FastAPI | Only a warning today | Move to a lifespan handler |

### Docker (suggestion, **untested**)

No Docker image has been built or run. A starting point:

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git clone --depth 1 https://github.com/helenacuesta/multif0-estimation-polyvocals /app/multif0-estimation-polyvocals
COPY mvp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY mvp/backend /app/backend
ENV MF0_REPO=/app/multif0-estimation-polyvocals
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

`libsndfile1` is needed for audio decoding; `ffmpeg` is included in case MP3 decoding needs it (**MP3 uploads have not been tested**, only WAV). Expect an image of several GB because of TensorFlow.

## 8. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `OSError`/`KeyError` while loading weights | `MF0_REPO` wrong, or the clone is missing `models/exp3multif0.pkl` |
| Output looks random | Layer creation order in `_build()` was changed (see section 6, point 3) |
| `ModuleNotFoundError: pumpp` or `jams` | Install from `requirements.txt` exactly; `pumpp` needs `jams` |
| MP3 uploads fail | Untested format. Check system `libsndfile` (version 1.1 or newer) and `ffmpeg` |
| Browser says "blocked by CORS policy" | Set `CORS_ORIGINS` to include the front end's address |
| Very slow first request | The model loads at startup; if you start with `--reload` it reloads on every code change |
| Requests hang while another is running | See "One request blocks the server" above |
