# MVP: Choir pitch tracking (MIR SLR follow up)

Starting point for the group's MVP. It came out of **Task 1**: find an open source solution from the studies in our systematic literature review (*Intelligent Music Processing for Singing, Ensembles, and Instrumental Performance*, 365 studies) that we can continue and expand.

**Result in one paragraph.** We build on **multif0-estimation-polyvocals** (Cuesta, McFee and Gómez, ISMIR 2020), a model that finds every pitch sounding in a choir or vocal quartet recording. The original code needs Python 3.6 and TensorFlow 1.15, so it was ported to modern libraries (Python 3.12, Keras 3) and wrapped in a small web API. **Timbre-Trap** (Cwitkowitz et al., ICASSP 2024) is the fallback. On real choir test audio, multif0 scored an F-measure of 0.83 against 0.65 for Timbre-Trap. See [the research report](docs/RESEARCH_REPORT.md) for the evidence and its caveats.

> **Read this before trusting any number.** The test audio comes from a dataset that multif0 was trained on, and the reference pitches come from an automatic tracker. The scores rank the models; they are not accuracy claims for the finished product. See [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md#headline-results).

## Where to start

| You are... | Read this first |
|---|---|
| Anyone new to the project | This page, then [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md) |
| Developer / Engineer (Back & Front) | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) |
| Tracking Delivery & Tasks | [docs/IMPLEMENTATION_CHECKLIST.md](docs/IMPLEMENTATION_CHECKLIST.md) |
| Re-running or extending the tests | [docs/EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md) |

## What is in this folder

```
mvp/
├── README.md                    this page
├── requirements.txt             Python packages for the back end and evaluation
├── requirements-timbretrap.txt  extra packages for the Timbre-Trap comparison only
├── backend/
│   ├── mf0_service.py           the ported multif0 model: load, features, predict, peak picking
│   ├── app.py                   FastAPI web API (GET /health, POST /transcribe)
│   └── test_api.py              smoke test for the API
├── frontend/
│   ├── package.json             TypeScript + Vite frontend starter
│   ├── src/                     upload flow, API client, pitch conversion, canvas chart
│   └── sample_transcription.json sample response for offline UI development
├── eval/
│   ├── prep_data.py             builds the 14 test mixtures from Choral Singing Dataset stems
│   ├── mf0_estimate.py          runs multif0 over the test mixtures, saves activations
│   ├── tt_estimate.py           runs Timbre-Trap over the same mixtures
│   ├── evaluate.py              scores both with mir_eval, writes results.json
│   ├── port_test.py             synthetic chord test that proves the port loads and works
│   └── tt_test.py               synthetic check that Timbre-Trap runs unmodified
└── docs/
    ├── RESEARCH_REPORT.md       full findings: candidates, tests, datasets, risks, sources
    ├── IMPLEMENTATION_CHECKLIST.md  step-by-step 4-phase implementation checklist
    ├── DEVELOPER_GUIDE.md       consolidated master developer & architecture guide
    ├── DEVELOPER_GUIDE.docx     formatted Microsoft Word version of Developer Guide
    ├── IMPLEMENTATION_CHECKLIST.md  step-by-step 4-phase implementation checklist
    ├── IMPLEMENTATION_CHECKLIST.docx formatted Microsoft Word version of Checklist
    ├── RESEARCH_REPORT.md       full findings: candidates, tests, datasets, risks, sources
    └── EVALUATION_GUIDE.md      evaluation protocol and benchmark reproducibility
```

## Quick start (back end)

You need Python 3.12 and about 3 GB of free disk space for TensorFlow.

```bash
# 1. get the pretrained weights (they live in the original author's repo)
git clone --depth 1 https://github.com/helenacuesta/multif0-estimation-polyvocals
export MF0_REPO="$PWD/multif0-estimation-polyvocals"

# 2. install
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r mvp/requirements.txt

# 3. run the API
cd mvp/backend
uvicorn app:app --host 0.0.0.0 --port 8000

# 4. try it (in another terminal)
curl -F "file=@some_choir_clip.wav" "http://localhost:8000/transcribe?threshold=0.5"
```

The first start takes about 5 seconds to load the model. A 30 second clip takes about 22 seconds to process on 2 CPU cores. Full details, including every setting, are in [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md).

## Run the frontend and backend with Docker

From the repository root, build and start both services:

```bash
docker compose up --build
```

Open the frontend at `http://localhost:3000`. The frontend image installs its
Node dependencies, builds the Vite app, and serves the production assets with
Nginx. Browser API requests use the same-origin `/api` path; Nginx forwards
them to the `backend` service on the private Compose network. No separate
`npm run dev` process is needed.

The backend API remains available directly at `http://localhost:8000`, with
interactive docs at `http://localhost:8000/docs`. Compose waits for the
backend's `/health` check before starting the frontend. Stop both services
with `docker compose down`.

The Compose setup publishes frontend port `3000` and backend port `8000`. It
sets `VITE_API_BASE_URL=/api` as a frontend **build argument** and sets
`MF0_REPO=/app/multif0-estimation-polyvocals` and `CORS_ORIGINS=*` in the
backend container. No separate frontend runtime API URL is needed because the
browser uses the same-origin Nginx proxy.

The Docker build downloads backend dependencies and the model repository, so
an internet connection is required during the first build. Frontend host port
`3000` and backend host port `8000` must be available.

## What the MVP does and does not do

**Does.** Takes a choir recording (WAV, FLAC, OGG or MP3) and returns, for every 11.6 ms frame, the list of pitches in Hz that it hears.

**Does not.**
- Say which singer sings which pitch. The output is an unordered set per frame. Assigning pitches to singers needs extra work (see the next steps).
- Run in real time. It is offline analysis.
- Resolve pitch finer than its 20 cent grid without extra interpolation.
- Handle noisy recordings well. Recall falls from 0.85 on a clean recording to 0.42 at 0 dB noise.

## Status

| Item | State |
|---|---|
| Candidate search across the SLR | ✅ Done. 310 of 365 appendix rows scanned |
| multif0 port to Python 3.12 / Keras 3 | ✅ Done, all 33 layers load, works on real audio |
| Evaluation on 14 real choir mixtures | ✅ Done for multif0 and Timbre-Trap |
| Web API & SSE Job Streaming | ✅ Done (`/health`, `/transcribe`, `/jobs/{id}/events`, `/presets`, `/export/*`) |
| Docker image & Compose | ✅ Done (non-root backend and multi-stage frontend build) |
| Long file handling (block overlap) | ✅ Done (contiguous Hann window blending, L=5000, M=250) |
| Mathematical sub-bin pitch refinement | ✅ Done (parabolic interpolation with continuous cents) |
| Trajectory linking & SATB voicing | ✅ Done (bipartite greedy matching, vibrato smoothing, SATB) |
| Ensemble Analytics & Chords | ✅ Done (tuning drift, unison dispersion, vibrato, chord engine) |
| Multi-track MIDI & CSV Exporters | ✅ Done (Type 1 MIDI with pitch bends, CWE-1236 safe CSV) |
| Test suite & QA | ✅ Done (32 automated unit & integration tests passing) |
| Test on unseen dataset (Cantoría) | ⏳ In progress (evaluation runner in `eval/evaluate.py`) |
| Front end Studio UI | ⏳ In progress (see `docs/IMPLEMENTATION_CHECKLIST.md` Phase 2) |

## Who is doing what

Suggested split, for the group to confirm: one or two people on the back end, one on the front end, and the research author for the source handoff and open research items.

## Licenses and credit

This folder is group work built on other people's open source code. Check each before redistributing.

| Component | License | Notes |
|---|---|---|
| multif0-estimation-polyvocals | MIT | Weights were trained partly on commercial (pgmusic) recordings. Confirm with the author before redistributing the weights in a product |
| Timbre-Trap | MIT | Weights from the project's Hugging Face Space |
| UMSS (not used yet) | Apache-2.0 file, but README says "All rights reserved" | Ask the author before reusing |
| YourMT3 (not used) | GPL-3.0 | Anything derived from it would have to be GPL |

The model weights are **not** stored in this repository. The back end reads them from a clone of the original multif0 repository (`MF0_REPO`).
