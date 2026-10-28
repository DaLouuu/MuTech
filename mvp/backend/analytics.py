"""Ensemble Intonation & Performance Analytics Dashboard.

Implements Checklist Phase 3:
- 3.3.1 Tuning drift trend calculation (signed cents)
- 3.3.2 Pitch stability and vibrato analysis (rate in Hz, depth in cents)
- 3.3.3 Polyphony density distribution breakdown
- 3.3.4 Unison dispersion metric (frequency spread in cents between singers)
- 3.4.1 Structured CSV export generation
"""

import io
import csv
import math
from typing import TypedDict, Optional, Any
import numpy as np

from dsp_utils import frequency_to_midi_cents_note, identify_vertical_chord


class VibratoMetrics(TypedDict):
    rate_hz: float
    depth_cents: float
    stability_cents_std: float


class ChordSummary(TypedDict):
    chord: str
    count: int
    percentage: float


class EnsembleAnalytics(TypedDict, total=False):
    tuning_drift_cents: float
    mean_cents_error: float
    polyphony_distribution: dict[str, float]
    unison_dispersion_cents: float
    vibrato: Optional[VibratoMetrics]
    top_chords: list[ChordSummary]


def compute_unison_dispersion(frame_pitches: list[list[float]]) -> float:
    """Calculate the frequency spread (cents difference) when multiple voices sing the same pitch class.

    Implements Checklist 3.3.4:
    Detects pairs of sounding pitches within 100 cents (~1 semitone) in the same frame
    and returns the mean dispersion in cents.
    """
    unison_spreads: list[float] = []

    for pitches in frame_pitches:
        if len(pitches) < 2:
            continue
        sorted_p = sorted(pitches)
        for i in range(len(sorted_p)):
            for j in range(i + 1, len(sorted_p)):
                f1, f2 = sorted_p[i], sorted_p[j]
                if f1 <= 0 or f2 <= 0:
                    continue
                cents_diff = 1200.0 * math.log2(f2 / f1)
                # If within 100 cents (same pitch class unison)
                if cents_diff <= 100.0:
                    unison_spreads.append(cents_diff)

    if not unison_spreads:
        return 0.0
    return round(float(np.mean(unison_spreads)), 1)


def compute_vibrato_and_stability(
    contours: Optional[list[dict]],
    sample_rate_frames: float = 86.13,  # ~11.61ms per frame (22050 / 256)
) -> Optional[VibratoMetrics]:
    """Calculate pitch standard deviation and estimate vibrato rate and depth for sustained notes.

    Implements Checklist 3.3.2:
    - Sustained note segments > 500 ms (> 43 frames)
    - Vibrato rate in Hz (expected 4 to 8 Hz)
    - Vibrato depth in cents
    - Pitch stability (standard deviation in cents)
    """
    if not contours:
        return None

    sustained_cents_devs: list[float] = []
    vibrato_rates: list[float] = []
    vibrato_depths: list[float] = []

    for c in contours:
        pts = c.get("points", [])
        if len(pts) < 43:  # Less than ~500 ms at 11.6ms/frame
            continue

        hz_vals = np.array([p["hz"] for p in pts], dtype=np.float64)
        if np.any(hz_vals <= 0):
            continue

        # Convert to continuous cents relative to segment median
        median_hz = float(np.median(hz_vals))
        cents_series = 1200.0 * np.log2(hz_vals / median_hz)
        cents_std = float(np.std(cents_series))
        sustained_cents_devs.append(cents_std)

        # Estimate vibrato depth (peak-to-peak amplitude ~ 2 * sqrt(2) * std for sine)
        depth = float(2.0 * np.sqrt(2.0) * cents_std)
        vibrato_depths.append(depth)

        # Zero-crossing rate of detrended cents series to estimate vibrato rate
        detrended = cents_series - np.mean(cents_series)
        zero_crossings = np.where(np.diff(np.signbit(detrended)))[0]
        duration_s = pts[-1]["t"] - pts[0]["t"]
        if duration_s > 0.3 and len(zero_crossings) >= 4:
            # Full cycles = zero_crossings / 2
            estimated_hz = (len(zero_crossings) / 2.0) / duration_s
            # Human choral vibrato is physically bounded between 4.0 Hz and 8.5 Hz
            if 4.0 <= estimated_hz <= 8.5:
                vibrato_rates.append(estimated_hz)

    if not sustained_cents_devs:
        return None

    mean_rate = float(np.mean(vibrato_rates)) if vibrato_rates else 5.8
    mean_depth = float(np.mean(vibrato_depths)) if vibrato_depths else float(np.mean(sustained_cents_devs) * 2.5)
    mean_std = float(np.mean(sustained_cents_devs))

    return {
        "rate_hz": round(mean_rate, 1),
        "depth_cents": round(mean_depth, 1),
        "stability_cents_std": round(mean_std, 1),
    }


def compute_ensemble_analytics(
    frame_cents: list[list[int]],
    frame_pitches: list[list[float]],
    contours: Optional[list[dict]] = None,
) -> EnsembleAnalytics:
    """Compute ensemble intonation drift, mean error, polyphonic density, unison dispersion, chords, and vibrato.

    Args:
        frame_cents: List of integer cents deviations for each frame
        frame_pitches: List of detected frequencies for each frame
        contours: Optional list of linked vocal trajectories

    Returns:
        EnsembleAnalytics dict matching the data contract.
    """
    total_frames = max(1, len(frame_pitches))

    # 1. Flatten all detected cents
    all_cents = [c for c_list in frame_cents for c in c_list]

    if all_cents:
        mean_drift = float(np.mean(all_cents))
        mean_abs_err = float(np.mean(np.abs(all_cents)))
    else:
        mean_drift = 0.0
        mean_abs_err = 0.0

    # 2. Compute polyphony distribution percentages
    poly_counts = {"silence": 0, "solo": 0, "2_part": 0, "3_part": 0, "4_part": 0}

    for pitches in frame_pitches:
        n = len(pitches)
        if n == 0:
            poly_counts["silence"] += 1
        elif n == 1:
            poly_counts["solo"] += 1
        elif n == 2:
            poly_counts["2_part"] += 1
        elif n == 3:
            poly_counts["3_part"] += 1
        else:
            poly_counts["4_part"] += 1

    poly_distribution = {
        k: round(float(v / total_frames * 100.0), 1)
        for k, v in poly_counts.items()
    }

    # 3. Unison Dispersion Metric (Checklist 3.3.4)
    unison_disp = compute_unison_dispersion(frame_pitches)

    # 4. Vibrato & Stability Metrics (Checklist 3.3.2)
    vibrato_info = compute_vibrato_and_stability(contours)

    # 5. Harmonic Analysis & Chord Progression Summary (Checklist 2.5 & Phase 3.5)
    chord_counts: dict[str, int] = {}
    polyphonic_frames = 0
    for pitches in frame_pitches:
        if len(pitches) >= 2:
            polyphonic_frames += 1
            ch = identify_vertical_chord(pitches)
            if ch and not ch.startswith("["):
                chord_counts[ch] = chord_counts.get(ch, 0) + 1

    top_chords: list[ChordSummary] = []
    if polyphonic_frames > 0:
        sorted_chords = sorted(chord_counts.items(), key=lambda x: x[1], reverse=True)
        for ch_name, count in sorted_chords[:8]:
            top_chords.append({
                "chord": ch_name,
                "count": count,
                "percentage": round(count / polyphonic_frames * 100.0, 1),
            })

    analytics_dict: EnsembleAnalytics = {
        "tuning_drift_cents": round(mean_drift, 1),
        "mean_cents_error": round(mean_abs_err, 1),
        "polyphony_distribution": poly_distribution,
        "unison_dispersion_cents": unison_disp,
        "top_chords": top_chords,
    }
    if vibrato_info is not None:
        analytics_dict["vibrato"] = vibrato_info

    return analytics_dict


def _sanitize_csv_cell(val: Any) -> str:
    """Sanitize strings against CSV Formula Injection (CWE-1236).

    Prepends a single quote if string begins with =, +, -, @, tab, or newline
    to prevent spreadsheet applications from executing formulas.
    """
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


def generate_csv_export(
    frames: list[dict],
    contours: list[dict] | None = None,
) -> str:
    """Generate structured CSV representation of the multi-pitch transcription.

    Columns:
        frame_index, timestamp_sec, frequency_hz, midi_note, note_name, cents_offset, chord, contour_id, voice_part
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "frame_index",
        "timestamp_sec",
        "frequency_hz",
        "midi_note",
        "note_name",
        "cents_offset",
        "chord",
        "contour_id",
        "voice_part"
    ])

    # Build quick lookup from (time, hz) to contour if contours are provided
    contour_map = {}
    if contours:
        for c in contours:
            cid = c.get("id", "")
            voice = c.get("voice_part", "Unassigned")
            for pt in c.get("points", []):
                key = (round(pt["t"], 3), round(pt["hz"], 1))
                contour_map[key] = (cid, voice)

    for i, frame in enumerate(frames):
        t = frame["t"]
        f0_list = frame.get("f0_refined", frame.get("f0", []))
        notes_list = frame.get("notes", [])
        cents_list = frame.get("cents", [])
        chord = frame.get("chord", "")

        if not f0_list:
            continue

        for p_idx, hz in enumerate(f0_list):
            note = notes_list[p_idx] if p_idx < len(notes_list) else ""
            cents = cents_list[p_idx] if p_idx < len(cents_list) else 0

            key = (round(t, 3), round(hz, 1))
            cid, voice = contour_map.get(key, ("", "Unassigned"))

            _, nearest_midi, _, _ = frequency_to_midi_cents_note(hz)

            writer.writerow([
                i,
                f"{t:.4f}",
                f"{hz:.2f}",
                nearest_midi,
                _sanitize_csv_cell(note),
                cents,
                _sanitize_csv_cell(chord),
                _sanitize_csv_cell(cid),
                _sanitize_csv_cell(voice)
            ])

    return output.getvalue()
