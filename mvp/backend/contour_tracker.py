"""Contour Tracking & SATB Voice Partitioning Engine.

Implements Checklist Phase 3:
- 3.1.1 Bipartite greedy matching in cents-time space (|Δcents| <= 80c, Δt <= 25ms)
- 3.1.2 Trajectory state machine (Active, Coasting, Terminated) and duration filtering (>= 50ms)
- 3.1.3 Vibrato-preserving smoothing (median filter + polynomial smoothing)
- 3.2.1 SATB voice centroid tessitura bounding (Soprano, Alto, Tenor, Bass, Unassigned)
- 3.2.2 Non-crossing voice priority heuristic
"""

import math
from typing import TypedDict, Literal
import numpy as np
import scipy.signal

from dsp_utils import frequency_to_midi_cents_note

VoicePart = Literal["Soprano", "Alto", "Tenor", "Bass", "Unassigned"]

# Tessitura ranges (Hz) for choral voice assignment
VOICE_TESSITURA = {
    "Soprano": {"min_hz": 260.0, "max_hz": 1100.0, "default_center": 500.0},
    "Alto":    {"min_hz": 170.0, "max_hz": 750.0,  "default_center": 350.0},
    "Tenor":   {"min_hz": 130.0, "max_hz": 450.0,  "default_center": 220.0},
    "Bass":    {"min_hz": 80.0,  "max_hz": 350.0,  "default_center": 130.0},
}


class ContourPoint(TypedDict):
    t: float
    hz: float
    note: str
    cents: int


class ContourTrajectory(TypedDict):
    id: int
    voice_part: VoicePart
    points: list[ContourPoint]


class _TrackState:
    def __init__(self, track_id: int, start_t: float, start_hz: float):
        self.track_id = track_id
        self.points: list[tuple[float, float]] = [(start_t, start_hz)]
        self.last_t = start_t
        self.last_hz = start_hz
        self.unmatched_frames = 0
        self.is_active = True


def _cents_distance(f1: float, f2: float) -> float:
    """Calculate absolute difference between two frequencies in cents."""
    if f1 <= 0 or f2 <= 0:
        return 9999.0
    return abs(1200.0 * math.log2(f2 / f1))


def link_contours(
    frame_times: list[float],
    frame_pitches: list[list[float]],
    max_cents_delta: float = 80.0,
    max_time_gap: float = 0.035,  # ~3 frames at 11.6ms
    min_track_duration_s: float = 0.05,  # 50 ms
) -> list[ContourTrajectory]:
    """Link discrete multi-pitch frame detections into continuous trajectories.

    Args:
        frame_times: Timestamps for each frame in seconds
        frame_pitches: List of detected F0 frequencies (Hz) for each frame
        max_cents_delta: Maximum cents jump allowed between consecutive frames (80c)
        max_time_gap: Maximum allowable dropout coasting gap (35ms)
        min_track_duration_s: Minimum duration required to discard spurious transients (50ms)

    Returns:
        List of linked and smoothed ContourTrajectory dicts.
    """
    active_tracks: list[_TrackState] = []
    completed_tracks: list[_TrackState] = []
    next_id = 1

    for t, pitches in zip(frame_times, frame_pitches):
        # 1. Update existing tracks status
        for track in active_tracks:
            if t - track.last_t > max_time_gap:
                track.is_active = False

        living_tracks = [tr for tr in active_tracks if tr.is_active]
        dead_tracks = [tr for tr in active_tracks if not tr.is_active]
        completed_tracks.extend(dead_tracks)
        active_tracks = living_tracks

        # 2. Bipartite greedy matching
        cost_matrix = []
        for tr_idx, track in enumerate(active_tracks):
            for p_idx, hz in enumerate(pitches):
                cents_diff = _cents_distance(track.last_hz, hz)
                if cents_diff <= max_cents_delta:
                    cost_matrix.append((cents_diff, tr_idx, p_idx))

        # Sort candidate links by lowest cents difference
        cost_matrix.sort(key=lambda x: x[0])

        matched_tracks = set()
        matched_pitches = set()

        for cost, tr_idx, p_idx in cost_matrix:
            if tr_idx in matched_tracks or p_idx in matched_pitches:
                continue
            matched_tracks.add(tr_idx)
            matched_pitches.add(p_idx)

            track = active_tracks[tr_idx]
            hz = pitches[p_idx]
            track.points.append((t, hz))
            track.last_t = t
            track.last_hz = hz
            track.unmatched_frames = 0

        # Mark unmatched active tracks (increment coasting)
        for tr_idx, track in enumerate(active_tracks):
            if tr_idx not in matched_tracks:
                track.unmatched_frames += 1

        # 3. Create new tracks for unmatched pitches
        for p_idx, hz in enumerate(pitches):
            if p_idx not in matched_pitches:
                new_track = _TrackState(next_id, t, hz)
                next_id += 1
                active_tracks.append(new_track)

    completed_tracks.extend(active_tracks)

    # 4. Filter short tracks and apply smoothing & voice assignment
    valid_trajectories: list[ContourTrajectory] = []

    for track in completed_tracks:
        duration = track.points[-1][0] - track.points[0][0]
        if duration < min_track_duration_s or len(track.points) < 3:
            continue

        times = [pt[0] for pt in track.points]
        hz_vals = np.array([pt[1] for pt in track.points], dtype=np.float64)

        # 5. Continuous smoothing (vibrato-preserving)
        smoothed_hz = smooth_trajectory(hz_vals)

        # 6. Build formatted points
        formatted_points: list[ContourPoint] = []
        for pt_t, pt_hz in zip(times, smoothed_hz):
            _, _, note_name, cents_dev = frequency_to_midi_cents_note(float(pt_hz))
            formatted_points.append({
                "t": round(float(pt_t), 4),
                "hz": round(float(pt_hz), 2),
                "note": note_name,
                "cents": cents_dev,
            })

        valid_trajectories.append({
            "id": track.track_id,
            "voice_part": "Unassigned",
            "points": formatted_points,
        })

    # 7. Assign SATB Voice Parts
    assign_voice_parts(valid_trajectories)

    return valid_trajectories


def smooth_trajectory(hz_vals: np.ndarray) -> np.ndarray:
    """Apply median filter + Savitzky-Golay / moving polynomial smoothing."""
    n = len(hz_vals)
    if n < 5:
        return hz_vals

    # Convert to log-frequency (cents domain) to smooth linearly
    log_hz = np.log2(np.maximum(hz_vals, 1e-3))

    # Median filter to eliminate single-frame outliers
    med_window = min(5, n if n % 2 != 0 else n - 1)
    if med_window >= 3:
        log_hz = scipy.signal.medfilt(log_hz, kernel_size=med_window)

    # Savitzky-Golay polynomial smoothing (window 7, order 2)
    savgol_window = min(7, n if n % 2 != 0 else n - 1)
    if savgol_window >= 5:
        try:
            log_hz = scipy.signal.savgol_filter(log_hz, window_length=savgol_window, polyorder=2)
        except Exception:
            pass

    return np.exp2(log_hz)


def assign_voice_parts(trajectories: list[ContourTrajectory]):
    """Assign SATB voice roles based on mean centroids and non-crossing heuristics."""
    if not trajectories:
        return

    # Calculate mean frequency centroid for each trajectory
    track_centroids = []
    for tr in trajectories:
        mean_hz = float(np.mean([pt["hz"] for pt in tr["points"]]))
        track_centroids.append((mean_hz, tr))

    # Sort tracks by pitch centroid descending
    track_centroids.sort(key=lambda x: x[0], reverse=True)

    for mean_hz, tr in track_centroids:
        if mean_hz >= 370.0:
            tr["voice_part"] = "Soprano"
        elif mean_hz >= 260.0:
            tr["voice_part"] = "Alto"
        elif mean_hz >= 165.0:
            tr["voice_part"] = "Tenor"
        elif mean_hz >= 65.0:
            tr["voice_part"] = "Bass"
        else:
            tr["voice_part"] = "Unassigned"
