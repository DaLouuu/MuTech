# MuTech Choir Pitch Tracker: Developer Guide

Technical reference for the MuTech Choir Pitch Tracker MVP, covering the audio DSP pipeline, HTTP endpoints, browser canvas interface, and acoustic terms.

---

## 1. System Architecture & DSP Pipeline

```
   Raw Audio (.wav, .flac, .ogg, .mp3, .m4a)
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Audio Ingestion & Conditioning (audio_processor.py) │
│    • Stereo-to-mono downmix                             │
│    • 4th-order Butterworth high-pass filter (30 Hz)     │
│    • RMS loudness normalization (-20 dBFS)              │
│    • Polyphase bandlimited resampling to 22,050 Hz      │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Feature Extraction & Neural Inference (mf0_service)  │
│    • Harmonic CQT (HCQT: 1x, 2x, 3x, 4x, 5x harmonics)  │
│    • Phase differential computation                     │
│    • multif0 Late/Deep CNN (Cuesta et al., 2020)        │
│    • Salience Activation Map (360 bins × N frames)      │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Sub-Bin Refinement & Intonation (dsp_utils.py)       │
│    • Local peak picking with convexity validation       │
│    • Parabolic sub-bin interpolation (±0.5 bin offset)  │
│    • Fractional MIDI & signed cents deviation mapping   │
│    • Vertical polyphonic chord & harmonic analysis      │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Contour Tracking & SATB Voice Assignment             │
│    • Greedy bipartite cents-distance matching (≤ 80c)   │
│    • Coasting state machine & 50ms duration filtering   │
│    • Vibrato-preserving Savitzky-Golay smoothing        │
│    • Centroid tessitura classification (S, A, T, B)     │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│ 5. API Delivery & Web Presentation                      │
│    • Asynchronous job worker & REST endpoints (app.py)  │
│    • Interactive HTML5 Canvas Piano Roll Studio         │
│    • Multi-track Type 1 Standard MIDI & CSV export      │
└─────────────────────────────────────────────────────────┘
```

### Acoustic Specifications
* **Audio Input:** 22,050 Hz sample rate, mono 32-bit floating point.
* **Temporal Resolution:** 256 samples per hop $\to 11.61\text{ ms}$ per frame ($86.13\text{ fps}$).
* **Frequency Grid:** 360 logarithmic bins across 6 octaves ($C_1 \approx 32.7\text{ Hz}$ to $B_6 \approx 1975.5\text{ Hz}$), yielding $60\text{ bins/octave}$ ($20\text{ cents/bin}$).
* **Peak Interpolation:** Continuous parabolic offset refinement:
  $$\delta = \frac{\alpha - \gamma}{2(\alpha - 2\beta + \gamma)}, \quad f = f_{\min} \cdot 2^{(\text{bin} + \delta)/60}$$

---

## 2. Backend Service Reference (`mvp/backend/`)

### Module Inventory
| File | Role | Key Functions / Classes |
|---|---|---|
| [`app.py`](../backend/app.py) | FastAPI HTTP server & lifespan | `/transcribe`, `/jobs/{id}`, `/export/csv`, `/export/midi`, `/health` |
| [`mf0_service.py`](../backend/mf0_service.py) | Keras 3 multif0 model wrapper | `load()`, `activations()`, `peaks()`, `transcribe()` |
| [`audio_processor.py`](../backend/audio_processor.py) | Audio decoding & conditioning | `decode_audio()`, `preprocess_audio()`, `validate_file_metadata()` |
| [`dsp_utils.py`](../backend/dsp_utils.py) | Sub-bin pitch refinement & chords | `parabolic_interpolation()`, `frequency_to_midi_cents_note()`, `identify_vertical_chord()` |
| [`contour_tracker.py`](../backend/contour_tracker.py) | Trajectory tracking & SATB | `link_contours()`, `smooth_trajectory()`, `assign_voice_parts()` |
| [`job_manager.py`](../backend/job_manager.py) | Asynchronous memory job queue | `submit()`, `get_status()`, `cleanup_expired()` |
| [`midi_exporter.py`](../backend/midi_exporter.py) | Type 1 Standard MIDI generation | `generate_midi_type1()`, pitch wheel curve automation |
| [`analytics.py`](../backend/analytics.py) | Tabular report generation | `generate_csv_export()` |

### Key API Endpoints

#### `POST /transcribe`
Synchronous or streaming multipart audio upload.
* **Parameters:**
  * `file`: Audio file (`.wav`, `.flac`, `.ogg`, `.mp3`, `.m4a`, max 50 MB).
  * `threshold` (query float, default `0.5`, range `0.1`–`0.95`): Minimum neural salience threshold.
  * `hop` (query int, default `1`, range `1`–`20`): Temporal downsampling step.
* **Response (excerpt):**
  ```json
  {
    "sample_rate": 22050,
    "hop_s": 0.01161,
    "threshold": 0.5,
    "n_frames": 2583,
    "process_s": 4.12,
    "frames": [
      {
        "t": 1.2539,
        "f0": [220.15, 330.22],
        "notes": ["A3", "E4"],
        "cents": [1, 2],
        "chord": "A (Open 5th)"
      }
    ],
    "contours": [
      {
        "id": 1,
        "voice_part": "Tenor",
        "points": [{"t": 1.2539, "hz": 220.15, "note": "A3", "cents": 1}]
      }
    ]
  }
  ```

#### `POST /export/midi`
Generates a multi-track Type 1 Standard MIDI file with dedicated SATB tracks (Ch. 0: Soprano, 1: Alto, 2: Tenor, 3: Bass) and high-resolution pitch bend curves.

#### `POST /export/csv`
Returns a structured CSV containing frame-level frequencies, notes, intonation deviation, identified chords, and voice trajectories.

#### `GET /health`
System diagnostics probe returning memory usage, CPU load, and model readiness status.

---

## 3. Frontend Web Studio Guide (`mvp/frontend/`)

### User Interface Capabilities
1. **Interactive File Ingestion:** Drag-and-drop audio uploader supporting all modern browser formats.
2. **Audio-Synchronized Canvas Playback:** Web AudioContext timeline playback synchronized with a 60 FPS canvas piano roll.
3. **Continuous Intonation Inspection:** Real-time hover tooltips indicating exact pitch frequency (Hz), nearest equal-tempered note name, and signed cents deviation (e.g., `G3 +14c`).
4. **SATB Voice Filtering:** Independent toggle controls to solo or mute Soprano, Alto, Tenor, and Bass trajectories.
5. **Interactive Sensitivity Tuning:** Live slider dynamically adjusting peak detection threshold from $0.20$ to $0.80$.

### Pitch-to-Note Math (`src/music.ts`)
Equal temperament with $A_4 = 440\text{ Hz}$:
```ts
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

export function hzToMidiAndCents(hz: number, a4 = 440) {
  if (hz <= 0) return { midi: 0, note: "", cents: 0 };
  const fractionalMidi = 69 + 12 * Math.log2(hz / a4);
  const nearestMidi = Math.round(fractionalMidi);
  const cents = Math.round(100 * (fractionalMidi - nearestMidi));
  const noteName = NOTE_NAMES[((nearestMidi % 12) + 12) % 12];
  const octave = Math.floor(nearestMidi / 12) - 1;
  return {
    midi: fractionalMidi,
    note: `${noteName}${octave}`,
    cents, // positive = sharp, negative = flat
  };
}
```

---

## 4. Audio & Musical Domain Glossary

| Term | Technical Definition | Practical Role in MuTech |
|---|---|---|
| **F0 (Fundamental Frequency)** | The lowest periodic frequency component in an acoustic signal, perceived as musical pitch. | Estimated per frame in Hz. |
| **Multi-F0 Estimation** | The simultaneous extraction of multiple concurrent fundamental frequencies in polyphonic audio. | The core task performed by the multif0 CNN. |
| **Cent** | A logarithmic unit of musical interval. $1\text{ semitone} = 100\text{ cents}$, $1\text{ octave} = 1200\text{ cents}$. | Quantifies singer intonation accuracy (sharp/flat). |
| **HCQT (Harmonic Constant-Q Transform)** | A geometrically spaced multi-resolution time-frequency transform stacked across harmonic multiples ($1\times, 2\times, \dots, 5\times$). | Neural input representation providing shift-invariant overtone patterns. |
| **Phase Differential** | The temporal rate of change in the phase spectrum across adjacent frames. | Enables the model to sharpen transient peak locations beyond the STFT resolution. |
| **Tessitura** | The most acceptable, comfortable vocal range for a given voice type. | Used by `contour_tracker.py` to assign SATB roles based on pitch centroid. |
| **Octave Error** | A common MIR defect where an algorithm predicts $2\times$ or $0.5\times$ of the true fundamental frequency. | Mitigated via harmonic overtone stacking in HCQT. |
| **Vocal Blend** | Acoustic coupling occurring when multiple choral singers lock into identical harmonic partials and formant alignments. | The primary reason choral transcription requires specialized models over solo trackers. |

---

## 5. Quick Start & Execution

### Backend Execution
```bash
# 1. Activate backend environment
cd mvp/backend
source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows

# 2. Run the server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: [`http://localhost:8000/docs`](http://localhost:8000/docs)

### Frontend Studio Execution
```bash
cd mvp/frontend
npm install
npm run dev
```
Web Studio will be live at: [`http://localhost:5173`](http://localhost:5173) (or run `python -m http.server 3000 --directory mvp/frontend` for direct static serving).

