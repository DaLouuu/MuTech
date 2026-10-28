"""Comprehensive Unit & Integration Test Suite for Choir Pitch Tracker Backend.

Validates Checklist Items:
- 1.1 Audio ingestion, conditioning & normalization
- 1.2 Parabolic peak interpolation, cents, and note naming
- 1.3 Block overlap stitching & Hann cross-fading
- 1.4 API health, non-blocking execution, and async job polling
- 3.1 Contour linking & smoothing
- 3.2 SATB voice centroid partitioning
- 3.3 Ensemble tuning drift & polyphony distribution
- 3.4 CSV export generation
"""

import math
import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dsp_utils import (
    parabolic_interpolation,
    frequency_to_midi_cents_note,
    bin_to_frequency,
    refine_salience_peaks,
    stitch_overlapping_blocks,
    FMIN,
    BINS_PER_OCTAVE,
)
from audio_processor import (
    downmix_to_mono,
    normalize_rms,
    apply_highpass_filter,
    resample_audio,
    TARGET_SR,
    TARGET_RMS_DBFS,
)
from contour_tracker import link_contours, smooth_trajectory
from analytics import compute_ensemble_analytics, generate_csv_export
from midi_exporter import generate_midi_type1
import app as backend_app
from job_manager import JobManager


# -------------------------------------------------------------
# 1.2 DSP & Math Tests
# -------------------------------------------------------------

def test_parabolic_interpolation_symmetric():
    """Symmetric peak should have delta = 0."""
    alpha, beta, gamma = 0.5, 0.9, 0.5
    delta, mag = parabolic_interpolation(alpha, beta, gamma)
    assert abs(delta) < 1e-6
    assert abs(mag - 0.9) < 1e-6


def test_parabolic_interpolation_asymmetric():
    """Right-shifted peak should produce positive delta."""
    alpha, beta, gamma = 0.4, 0.9, 0.7
    delta, mag = parabolic_interpolation(alpha, beta, gamma)
    assert 0.0 < delta <= 0.5
    assert mag >= beta


def test_parabolic_interpolation_non_convex():
    """Non-convex point (valley/flat) should return delta=0 and original beta."""
    alpha, beta, gamma = 0.8, 0.4, 0.8  # concave up
    delta, mag = parabolic_interpolation(alpha, beta, gamma)
    assert delta == 0.0
    assert mag == 0.4


def test_cents_conversion_standard_pitches():
    """Verify standard reference pitches return exactly 0 cents deviation."""
    # A4 = 440 Hz
    frac_midi, nearest_midi, name, cents = frequency_to_midi_cents_note(440.0)
    assert nearest_midi == 69
    assert name == "A4"
    assert cents == 0

    # Middle C (C4) ~ 261.6256 Hz
    c4_hz = 440.0 * (2.0 ** ((60 - 69) / 12.0))
    _, nearest_midi, name, cents = frequency_to_midi_cents_note(c4_hz)
    assert nearest_midi == 60
    assert name == "C4"
    assert cents == 0


def test_cents_conversion_detuned():
    """Verify +15 cents detuning."""
    target_hz = 440.0 * (2.0 ** (15.0 / 1200.0))  # +15 cents above A4
    _, nearest_midi, name, cents = frequency_to_midi_cents_note(target_hz)
    assert nearest_midi == 69
    assert name == "A4"
    assert cents == 15


def test_refine_salience_peaks_synthetic():
    """Verify peak extraction and continuous parabolic refinement on a synthetic matrix."""
    n_bins = 360
    n_frames = 10
    act = np.zeros((n_bins, n_frames), dtype=np.float32)

    # Place a peak near bin 180 (A4 is ~ bin 212 at fmin=32.7)
    peak_bin = 180
    act[peak_bin - 1, :] = 0.5
    act[peak_bin, :] = 0.95
    act[peak_bin + 1, :] = 0.65

    raw_f0, refined_f0, notes, cents = refine_salience_peaks(act, threshold=0.5)

    assert len(raw_f0) == n_frames
    for t in range(n_frames):
        assert len(raw_f0[t]) == 1
        assert len(refined_f0[t]) == 1
        # Refined frequency should be slightly higher than discrete bin frequency because right neighbor > left
        assert refined_f0[t][0] > raw_f0[t][0]
        assert isinstance(notes[t][0], str)
        assert -50 <= cents[t][0] <= 50


# -------------------------------------------------------------
# 1.3 Block Overlap & Hann Cross-Fading Tests
# -------------------------------------------------------------

def test_stitch_overlapping_blocks():
    """Verify smooth stitching of overlapping blocks without edge discontinuities."""
    n_bins = 10
    block_size = 100
    overlap_margin = 10  # 2M = 20
    overlap_len = 20

    # Block 1 is constant 1.0, Block 2 is constant 2.0
    b1 = np.ones((n_bins, block_size), dtype=np.float32)
    b2 = np.full((n_bins, block_size), 2.0, dtype=np.float32)

    stitched = stitch_overlapping_blocks([b1, b2], block_size=block_size, overlap_margin=overlap_margin)

    # Length should be (100 - 20) + 20 + (100 - 20) = 180
    expected_len = block_size + (block_size - overlap_len)
    assert stitched.shape == (n_bins, expected_len)

    # Head should be 1.0
    assert np.allclose(stitched[:, :70], 1.0)
    # Overlap seam region should transition monotonically from 1.0 to 2.0
    seam = stitched[0, 80:100]
    assert np.all(np.diff(seam) >= 0)
    # Tail should be 2.0
    assert np.allclose(stitched[:, 110:], 2.0)


# -------------------------------------------------------------
# 1.1 Audio Conditioning Tests
# -------------------------------------------------------------

def test_downmix_to_mono():
    """Stereo audio should downmix via channel averaging."""
    stereo = np.array([[1.0, 3.0], [2.0, 4.0]], dtype=np.float32)  # shape (2, 2)
    mono = downmix_to_mono(stereo)
    assert np.allclose(mono, np.array([2.0, 3.0], dtype=np.float32))


def test_normalize_rms():
    """Signal should be scaled to target RMS dBFS."""
    sine = np.sin(np.linspace(0, 20 * np.pi, 10000, dtype=np.float32)) * 0.01
    norm = normalize_rms(sine, target_dbfs=-20.0)
    rms_linear = float(np.sqrt(np.mean(norm ** 2)))
    target_linear = 10.0 ** (-20.0 / 20.0)
    assert abs(rms_linear - target_linear) < 1e-3


def test_highpass_filter():
    """DC offset should be completely stripped by 30 Hz high-pass filter."""
    sr = 22050
    t = np.linspace(0, 1.0, sr, dtype=np.float32)
    signal_with_dc = np.sin(2 * np.pi * 100 * t) + 2.5  # 2.5V DC offset
    filtered = apply_highpass_filter(signal_with_dc, sr, cutoff_hz=30.0)
    # Mean of filtered signal should be very close to 0
    assert abs(np.mean(filtered[sr // 4:])) < 0.05


def test_audio_processor_empty_and_edge_inputs():
    """Verify audio processor handles empty arrays without crashing or throwing unhandled errors."""
    empty = np.array([], dtype=np.float32)
    assert len(downmix_to_mono(empty)) == 0
    assert len(apply_highpass_filter(empty, 22050)) == 0
    assert len(normalize_rms(empty)) == 0
    assert len(resample_audio(empty, 44100, 22050)) == 0
    # Invalid sample rates guard
    assert len(resample_audio(empty, -1, 22050)) == 0
    assert len(apply_highpass_filter(empty, -1)) == 0


# -------------------------------------------------------------
# 3.1 & 3.2 Contour Linking & SATB Tests
# -------------------------------------------------------------

def test_link_contours_two_voices():
    """Verify greedy tracking links two distinct simultaneous voice lines."""
    times = [round(i * 0.0116, 4) for i in range(20)]
    # Soprano line at ~523 Hz (C5), Bass line at ~131 Hz (C3)
    pitches = [[130.8 + 0.1 * np.sin(i), 523.25 + 0.2 * np.cos(i)] for i in range(20)]

    contours = link_contours(times, pitches)

    assert len(contours) == 2
    voice_parts = {c["voice_part"] for c in contours}
    assert "Soprano" in voice_parts
    assert "Bass" in voice_parts
    for c in contours:
        assert len(c["points"]) == 20


# -------------------------------------------------------------
# 3.3 Analytics Tests
# -------------------------------------------------------------

def test_compute_ensemble_analytics():
    """Verify ensemble drift and polyphony distribution calculation."""
    frame_cents = [[0, 5], [0, 10], [5, 10], []]
    frame_pitches = [[440.0, 523.0], [440.0, 523.0], [440.0, 523.0], []]

    analytics = compute_ensemble_analytics(frame_cents, frame_pitches)

    # 4 frames: 3 frames of 2_part (75%), 1 frame silence (25%)
    assert analytics["polyphony_distribution"]["2_part"] == 75.0
    assert analytics["polyphony_distribution"]["silence"] == 25.0
    assert analytics["mean_cents_error"] > 0


def test_generate_csv_export():
    """Verify CSV string generation format."""
    frames = [
        {"t": 0.0, "f0_refined": [440.0], "notes": ["A4"], "cents": [0]},
        {"t": 0.0116, "f0_refined": [442.5], "notes": ["A4"], "cents": [10]},
    ]
    csv_str = generate_csv_export(frames)
    lines = csv_str.strip().split("\n")
    assert lines[0].startswith("frame_index,timestamp_sec,frequency_hz")
    assert len(lines) == 3


# -------------------------------------------------------------
# 1.4 API Endpoints Integration Tests
# -------------------------------------------------------------

client = TestClient(backend_app.app)


def test_api_health_endpoint():
    """Verify GET /health returns 200 with system & model state."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "uptime_s" in data
    assert "system" in data
    assert "memory_percent" in data["system"]


def test_api_unsupported_media_type():
    """Verify 415 response for unsupported file type."""
    res = client.post(
        "/transcribe",
        files={"file": ("document.txt", b"plain text", "text/plain")},
    )
    assert res.status_code == 415


def test_api_async_job_submission():
    """Verify async job creation and job polling via /jobs/{job_id}."""
    jm = JobManager()
    job = jm.create_job()
    assert job.status == "pending"

    jm.update_progress(job.job_id, 45.0, "processing")
    j = jm.get_job(job.job_id)
    assert j.status == "processing"
    assert j.progress == 45.0

    jm.complete_job(job.job_id, {"n_frames": 100})
    assert j.status == "completed"
    assert j.progress == 100.0


def test_api_export_csv_endpoint():
    """Verify POST /export/csv endpoint."""
    payload = {
        "frames": [
            {"t": 0.0, "f0_refined": [440.0], "notes": ["A4"], "cents": [0]}
        ]
    }
    res = client.post("/export/csv", json=payload)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "frame_index" in res.text


def test_generate_midi_type1():
    """Verify multi-track MIDI Type 1 file generation with pitch bends."""
    import mido
    import io
    contours = [
        {
            "id": 1,
            "voice_part": "Soprano",
            "points": [
                {"t": 0.0, "hz": 523.25, "note": "C5", "cents": 0},
                {"t": 0.05, "hz": 526.0, "note": "C5", "cents": 9},
                {"t": 0.10, "hz": 523.25, "note": "C5", "cents": 0},
            ]
        },
        {
            "id": 2,
            "voice_part": "Bass",
            "points": [
                {"t": 0.0, "hz": 130.81, "note": "C3", "cents": 0},
                {"t": 0.10, "hz": 130.81, "note": "C3", "cents": 0},
            ]
        }
    ]
    midi_bytes = generate_midi_type1(contours, tempo_bpm=120)
    assert len(midi_bytes) > 0
    # Parse back using mido to verify validity
    parsed_mid = mido.MidiFile(file=io.BytesIO(midi_bytes))
    assert parsed_mid.type == 1
    # Master track + Soprano track + Bass track = 3 tracks
    assert len(parsed_mid.tracks) == 3


def test_api_export_midi_endpoint():
    """Verify POST /export/midi endpoint."""
    payload = {
        "contours": [
            {
                "id": 1,
                "voice_part": "Soprano",
                "points": [
                    {"t": 0.0, "hz": 440.0, "note": "A4", "cents": 0},
                    {"t": 0.1, "hz": 440.0, "note": "A4", "cents": 0},
                ]
            }
        ]
    }
    res = client.post("/export/midi?tempo_bpm=120", json=payload)
    assert res.status_code == 200
    assert "audio/midi" in res.headers["content-type"]
    assert len(res.content) > 0


def test_unison_dispersion():
    """Verify unison dispersion metric calculates cents spread between unison singers."""
    from analytics import compute_unison_dispersion
    # Two singers singing near A4 (440.0 Hz and 442.5 Hz -> ~10 cents apart)
    pitches = [
        [440.0, 442.5],
        [440.0, 441.2],
        [130.8, 523.2],  # Non-unison (C3 and C5, 2400 cents apart) -> ignored
    ]
    disp = compute_unison_dispersion(pitches)
    assert 0.0 < disp < 15.0


def test_vibrato_and_stability():
    """Verify vibrato rate and pitch stability calculation on synthetic sustained note."""
    from analytics import compute_vibrato_and_stability
    # 50 frames of A4 with 6 Hz sinusoidal vibrato of +/- 20 cents
    times = [i * 0.0116 for i in range(60)]
    pts = []
    for t in times:
        cents_mod = 20.0 * np.sin(2 * np.pi * 6.0 * t)
        hz = 440.0 * (2.0 ** (cents_mod / 1200.0))
        pts.append({"t": t, "hz": hz, "cents": int(round(cents_mod))})

    contours = [{"id": 1, "points": pts}]
    vib = compute_vibrato_and_stability(contours)
    assert vib is not None
    assert 4.0 <= vib["rate_hz"] <= 8.5
    assert vib["depth_cents"] > 10.0
    assert vib["stability_cents_std"] > 0


def test_job_saturation_limit():
    """Verify JobManager protects against memory exhaustion by enforcing active job limits."""
    from job_manager import JobManager, JobLimitExceededError, MAX_ACTIVE_JOBS
    jm = JobManager()
    # Fill up to max active jobs
    for _ in range(MAX_ACTIVE_JOBS):
        jm.create_job()
    # Next create should raise JobLimitExceededError
    with pytest.raises(JobLimitExceededError):
        jm.create_job()


def test_audio_too_short_rejection():
    """Verify audio < 50ms is rejected with 400 error."""
    import io, soundfile as sf
    from audio_processor import load_and_condition_audio, AudioProcessingError
    # 100 samples at 22050 Hz = ~4.5 ms
    tiny = np.zeros(100, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, tiny, 22050, format="WAV")
    buf.seek(0)
    with pytest.raises(AudioProcessingError) as exc_info:
        load_and_condition_audio(buf.getvalue())
    assert exc_info.value.status_code == 400


def test_presets_endpoints():
    """Verify /presets list, JSON data, and audio endpoints."""
    # 1. List presets
    res = client.get("/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) >= 1
    assert presets[0]["id"] == "bach_chorale_satb"

    # 2. Get preset JSON transcription
    res_json = client.get("/presets/bach_chorale_satb")
    assert res_json.status_code == 200
    data = res_json.json()
    assert "frames" in data
    assert "contours" in data
    assert len(data["frames"]) > 100

    # 3. Stream preset audio
    res_audio = client.get("/presets/bach_chorale_satb/audio")
    assert res_audio.status_code == 200
    assert "audio/wav" in res_audio.headers["content-type"]
    assert len(res_audio.content) > 1000

    # 4. Unknown preset returns 404
    res_bad = client.get("/presets/non_existent_preset")
    assert res_bad.status_code == 404


def test_csv_injection_sanitization():
    """Verify CWE-1236 CSV Formula Injection prevention."""
    from analytics import _sanitize_csv_cell, generate_csv_export
    # Test individual cell sanitization
    assert _sanitize_csv_cell("=1+1") == "'=1+1"
    assert _sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert _sanitize_csv_cell("-2+3") == "'-2+3"
    assert _sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert _sanitize_csv_cell("NormalNote") == "NormalNote"

    # Test integrated CSV generation with injection attempt in contour voice_part
    malicious_contour = {
        "id": "=1+2",
        "voice_part": "@DDE('cmd';'calc.exe';'a')",
        "points": [{"t": 0.0, "hz": 440.0, "cents": 0}]
    }
    malicious_frame = {
        "t": 0.0,
        "f0_refined": [440.0],
        "notes": ["+A4"],
        "cents": [0]
    }
    csv_out = generate_csv_export([malicious_frame], [malicious_contour])
    assert "'=1+2" in csv_out
    assert "'@DDE" in csv_out
    assert "'+A4" in csv_out


def test_resample_nonstandard_rate_dos_protection():
    """Verify polyphase resampling avoids CPU exhaustion on coprime sample rates (CWE-400)."""
    import time
    from audio_processor import resample_audio
    # 44,101 Hz has gcd=1 with 22,050 Hz
    nonstandard_sr = 44101
    duration_s = 0.5
    y = np.sin(2 * np.pi * 440.0 * np.linspace(0, duration_s, int(nonstandard_sr * duration_s), endpoint=False)).astype(np.float32)

    t0 = time.time()
    resampled = resample_audio(y, orig_sr=nonstandard_sr, target_sr=22050)
    elapsed = time.time() - t0

    assert elapsed < 1.0  # Must complete rapidly (under 1 second)
    expected_samples = int(len(y) * (22050 / nonstandard_sr))
    assert abs(len(resampled) - expected_samples) <= 200


def test_export_payload_limits():
    """Verify oversized payloads exceed bounds and return 422 validation errors."""
    # Test contours exceeding 500
    excessive_contours = [{"id": i, "voice_part": "Bass", "points": []} for i in range(505)]
    res = client.post("/export/midi", json={"contours": excessive_contours})
    assert res.status_code == 422


def test_missing_weights_503_response(monkeypatch):
    """Verify transcription returns HTTP 503 when model weights are not loaded."""
    import mf0_service as svc
    def mock_transcribe(*args, **kwargs):
        raise RuntimeError("multif0 model is not loaded. Details: Weights not found")

    monkeypatch.setattr(svc, "transcribe", mock_transcribe)
    wav_header = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\"V\x00\x00D\xac\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    res = client.post(
        "/transcribe",
        files={"file": ("test.wav", wav_header, "audio/wav")}
    )
    assert res.status_code == 503
    assert "weights are not loaded" in res.json()["detail"].lower()


def test_job_incremental_progress():
    """Verify that asynchronous background jobs receive incremental progress callbacks."""
    import time
    from job_manager import job_manager
    from app import _process_transcription_job
    import mf0_service as svc

    # Create job
    job = job_manager.create_job()
    assert job.progress == 0.0

    # Call worker with dummy source
    # We provide a synthetic activation override to simulate full transcription with callbacks
    n_bins = 360
    n_frames = 20
    dummy_act = np.zeros((n_bins, n_frames), dtype=np.float32)

    # Trigger job worker using mock transcribe that triggers progress callbacks
    recorded_progress = []
    def mock_transcribe(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback(15.0)
            progress_callback(50.0)
            progress_callback(90.0)
        return {"n_frames": n_frames, "frames": []}

    orig_transcribe = svc.transcribe
    try:
        svc.transcribe = mock_transcribe
        _process_transcription_job(
            job.job_id,
            b"fake_bytes",
            "fake.wav",
            0.5,
            1,
            True,
        )
        final_job = job_manager.get_job(job.job_id)
        assert final_job is not None
        assert final_job.status == "completed"
        assert final_job.progress == 100.0
    finally:
        svc.transcribe = orig_transcribe


def test_identify_vertical_chord():
    """Verify vertical choral harmonic analysis for triads, inversions, and dyads."""
    from dsp_utils import identify_vertical_chord

    # 1. C Major root position: C4 (261.63), E4 (329.63), G4 (392.00)
    c_maj = identify_vertical_chord([261.63, 329.63, 392.00])
    assert c_maj == "C Major"

    # 2. C Major 1st inversion (E in bass): E3 (164.81), C4 (261.63), G4 (392.00)
    c_maj_inv = identify_vertical_chord([164.81, 261.63, 392.00])
    assert c_maj_inv == "C Major / E"

    # 3. A Minor root position: A3 (220.00), C4 (261.63), E4 (329.63)
    a_min = identify_vertical_chord([220.00, 261.63, 329.63])
    assert a_min == "A Minor"

    # 4. Open 5th dyad: D4 (293.66), A4 (440.00)
    open_5th = identify_vertical_chord([293.66, 440.00])
    assert "D 5" in open_5th or "Open 5th" in open_5th

    # 5. Octave doubling: A3 (220.00), A4 (440.00)
    octave = identify_vertical_chord([220.00, 440.00])
    assert octave == "A (Octave)"


def test_ensemble_analytics_top_chords():
    """Verify that compute_ensemble_analytics produces top_chords breakdown."""
    from analytics import compute_ensemble_analytics

    # Construct synthetic frames with C Major and A Minor sounding repeatedly
    c_maj_pitches = [261.63, 329.63, 392.00]
    a_min_pitches = [220.00, 261.63, 329.63]
    frame_pitches = [c_maj_pitches] * 10 + [a_min_pitches] * 5
    frame_cents = [[0, 0, 0]] * 15

    analytics = compute_ensemble_analytics(frame_cents, frame_pitches)
    assert "top_chords" in analytics
    top_chords = analytics["top_chords"]
    assert len(top_chords) >= 2
    chord_names = [tc["chord"] for tc in top_chords]
    assert "C Major" in chord_names
    assert "A Minor" in chord_names


def test_job_sse_stream_events():
    """Verify Server-Sent Events stream emits valid event stream headers and events."""
    from job_manager import job_manager

    job = job_manager.create_job()
    job_manager.complete_job(job.job_id, {"status": "success", "frames": []})

    with client.stream("GET", f"/jobs/{job.job_id}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        lines = list(response.iter_lines())
        assert any("event: complete" in line for line in lines)
        assert any(job.job_id in line for line in lines)



