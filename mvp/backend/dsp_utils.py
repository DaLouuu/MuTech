"""DSP utilities for high-precision pitch refinement and musical note mapping.

Implements Checklist Phase 1.2:
- 1.2.1 Parabolic sub-bin peak interpolation
- 1.2.2 Boundary handling and convexity validation
- 1.2.3 Fractional MIDI, cents intonation deviation, and note naming
"""

import math
import numpy as np

# multif0 parameters
FMIN = 32.7       # C1 in Hz
BINS_PER_OCTAVE = 60  # 20 cents per bin
N_BINS = 360      # 6 octaves: C1 (~32.7 Hz) to B6 (~1975.5 Hz)
A4_HZ = 440.0

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def parabolic_interpolation(alpha: float, beta: float, gamma: float) -> tuple[float, float]:
    """Calculate parabolic sub-bin offset and refined peak amplitude.

    Args:
        alpha: Activation at bin k-1
        beta:  Activation at peak bin k
        gamma: Activation at bin k+1

    Returns:
        (delta, refined_mag):
            delta: sub-bin offset in [-0.5, 0.5]
            refined_mag: estimated continuous peak amplitude
    """
    denominator = 2.0 * (alpha - 2.0 * beta + gamma)
    
    # Require strict peak convexity (denominator < 0)
    if abs(denominator) < 1e-9 or denominator >= 0:
        return 0.0, float(beta)
    
    delta = (alpha - gamma) / denominator
    delta = max(-0.5, min(0.5, float(delta)))
    refined_mag = float(beta - 0.25 * (alpha - gamma) * delta)
    return delta, max(0.0, refined_mag)


def bin_to_frequency(bin_index: float, fmin: float = FMIN, bpo: int = BINS_PER_OCTAVE) -> float:
    """Convert continuous or discrete bin index to frequency in Hz."""
    return float(fmin * (2.0 ** (bin_index / float(bpo))))


def frequency_to_bin(freq_hz: float, fmin: float = FMIN, bpo: int = BINS_PER_OCTAVE) -> float:
    """Convert frequency in Hz to continuous bin index."""
    if freq_hz <= 0:
        return 0.0
    return float(bpo * math.log2(freq_hz / fmin))


def frequency_to_midi_cents_note(freq_hz: float, a4: float = A4_HZ) -> tuple[float, int, str, int]:
    """Convert frequency in Hz to musical pitch parameters.

    Returns:
        (fractional_midi, nearest_midi, note_name, signed_cents_deviation)
    """
    if freq_hz <= 0:
        return 0.0, 0, "", 0
    
    fractional_midi = 69.0 + 12.0 * math.log2(freq_hz / a4)
    nearest_midi = int(round(fractional_midi))
    cents_deviation = int(round(100.0 * (fractional_midi - nearest_midi)))
    
    note_idx = (nearest_midi % 12 + 12) % 12
    octave = (nearest_midi // 12) - 1
    note_name = f"{NOTE_NAMES[note_idx]}{octave}"
    
    return fractional_midi, nearest_midi, note_name, cents_deviation


CHORD_TEMPLATES = [
    # Triads
    ("Major", frozenset([0, 4, 7])),
    ("Minor", frozenset([0, 3, 7])),
    ("Dim", frozenset([0, 3, 6])),
    ("Aug", frozenset([0, 4, 8])),
    ("sus4", frozenset([0, 5, 7])),
    ("sus2", frozenset([0, 2, 7])),
    # 7ths
    ("7", frozenset([0, 4, 7, 10])),
    ("maj7", frozenset([0, 4, 7, 11])),
    ("m7", frozenset([0, 3, 7, 10])),
    ("ø7", frozenset([0, 3, 6, 10])),
    ("°7", frozenset([0, 3, 6, 9])),
    # Dyads / Intervals
    ("5 (Open 5th)", frozenset([0, 7])),
    ("3rd", frozenset([0, 4])),
    ("m3rd", frozenset([0, 3])),
]


def identify_vertical_chord(frequencies: list[float]) -> str:
    """Identify the vertical harmonic chord and inversion from a set of sounding frequencies.

    Implements Checklist 2.5 & Phase 3.5:
    - Pitch-class set reduction
    - Root identification and chord quality matching
    - Bass note inversion identification (e.g. 'C Major / E' for 1st inversion)
    """
    valid_freqs = [f for f in frequencies if f > 0]
    if not valid_freqs:
        return ""

    # Map each frequency to MIDI note and pitch class
    midi_pcs = []
    for f in valid_freqs:
        m = int(round(69.0 + 12.0 * math.log2(f / A4_HZ)))
        pc = (m % 12 + 12) % 12
        midi_pcs.append((f, pc))

    # Lowest sounding frequency determines bass note
    midi_pcs.sort(key=lambda x: x[0])
    bass_pc = midi_pcs[0][1]
    bass_name = NOTE_NAMES[bass_pc]

    unique_pcs = frozenset([pc for _, pc in midi_pcs])
    if len(unique_pcs) == 1:
        pc = list(unique_pcs)[0]
        return f"{NOTE_NAMES[pc]} (Octave)" if len(valid_freqs) > 1 else f"{NOTE_NAMES[pc]} (Solo)"

    # Test each pitch class as candidate root
    best_chord = ""
    best_priority = -1

    for root_pc in range(12):
        rel_pcs = frozenset([(pc - root_pc) % 12 for pc in unique_pcs])
        root_name = NOTE_NAMES[root_pc]

        for priority, (quality, template) in enumerate(reversed(CHORD_TEMPLATES)):
            # Check exact match or full containment
            if rel_pcs == template:
                inv = f" / {bass_name}" if bass_pc != root_pc else ""
                chord_name = f"{root_name} {quality}{inv}".strip()
                if priority > best_priority:
                    best_priority = priority
                    best_chord = chord_name
            elif len(rel_pcs) >= 3 and template.issubset(rel_pcs) and len(template) >= 3:
                # Sub-template match with doubled or passing tone
                inv = f" / {bass_name}" if bass_pc != root_pc else ""
                chord_name = f"{root_name} {quality}{inv}".strip()
                if priority > best_priority:
                    best_priority = priority
                    best_chord = chord_name

    if best_chord:
        return best_chord

    # Fallback: display sounding pitch classes
    pc_names = sorted(list(set(NOTE_NAMES[pc] for _, pc in midi_pcs)))
    return f"[{', '.join(pc_names)}]"


def refine_salience_peaks(
    activation_matrix: np.ndarray,
    threshold: float = 0.5,
    fmin: float = FMIN,
    bpo: int = BINS_PER_OCTAVE,
) -> tuple[list[list[float]], list[list[float]], list[list[str]], list[list[int]]]:
    """Refine peak activations with parabolic interpolation and pitch mapping.

    Args:
        activation_matrix: (n_bins, n_frames) 2D array of salience activations in [0, 1]
        threshold: Minimum salience threshold for peak detection
        fmin: Minimum frequency of bin 0 (default: 32.7 Hz)
        bpo: Bins per octave (default: 60)

    Returns:
        Tuple of per-frame lists:
        - raw_f0: Discrete grid frequencies in Hz
        - refined_f0: Parabolically refined continuous frequencies in Hz
        - notes: Musical note strings (e.g. "A4")
        - cents: Signed intonation deviations [-50, +50]
    """
    n_bins, n_frames = activation_matrix.shape
    
    raw_f0_all: list[list[float]] = [[] for _ in range(n_frames)]
    refined_f0_all: list[list[float]] = [[] for _ in range(n_frames)]
    notes_all: list[list[str]] = [[] for _ in range(n_frames)]
    cents_all: list[list[int]] = [[] for _ in range(n_frames)]
    
    discrete_freqs = [bin_to_frequency(k, fmin, bpo) for k in range(n_bins)]
    
    for t in range(n_frames):
        col = activation_matrix[:, t]
        
        # Local maxima detection along frequency axis
        for k in range(n_bins):
            val = col[k]
            if val < threshold:
                continue
            
            # Check strictly greater than left neighbor
            left = col[k - 1] if k > 0 else 0.0
            if val <= left:
                continue
            
            # Check strictly greater than right neighbor
            right = col[k + 1] if k < n_bins - 1 else 0.0
            if val <= right:
                continue
            
            # Local peak confirmed at bin k
            raw_hz = discrete_freqs[k]
            
            # Sub-bin parabolic refinement
            alpha = left
            beta = val
            gamma = right
            
            delta, _ = parabolic_interpolation(alpha, beta, gamma)
            refined_bin = k + delta
            # Ensure within bin bounds
            refined_bin = max(0.0, min(float(n_bins - 1), refined_bin))
            refined_hz = bin_to_frequency(refined_bin, fmin, bpo)
            
            _, _, note_name, cents_dev = frequency_to_midi_cents_note(refined_hz)
            
            raw_f0_all[t].append(round(float(raw_hz), 2))
            refined_f0_all[t].append(round(float(refined_hz), 2))
            notes_all[t].append(note_name)
            cents_all[t].append(cents_dev)
            
    return raw_f0_all, refined_f0_all, notes_all, cents_all


def stitch_overlapping_blocks(
    blocks: list[np.ndarray],
    block_size: int = 5000,
    overlap_margin: int = 250,
) -> np.ndarray:
    """Stitch sequential overlapping activation blocks using Hann cross-fading.

    Implements Checklist 1.3:
    - Block size L (5000 frames)
    - Overlap margin M (250 frames)
    - Overlap region length: 2*M (500 frames)
    - Hann window cross-fading across the overlap seam

    Args:
        blocks: List of 2D numpy arrays with shape (n_bins, block_frames)
        block_size: Nominal length of each processing block (5000 frames)
        overlap_margin: One-sided margin M (250 frames), overlap length = 2*M

    Returns:
        Unified stitched activation matrix of shape (n_bins, total_frames)
    """
    if not blocks:
        return np.empty((N_BINS, 0), dtype=np.float32)
    if len(blocks) == 1:
        return blocks[0]

    overlap_len = 2 * overlap_margin
    n_bins = blocks[0].shape[0]

    # Precalculate Hann fade ramps: win_in (0 -> 1) and win_out (1 -> 0)
    # Hann window: 0.5 * (1 - cos(pi * i / overlap_len))
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(overlap_len) / float(overlap_len)))
    win_in = ramp.astype(np.float32)       # 0 -> 1
    win_out = (1.0 - ramp).astype(np.float32) # 1 -> 0

    stitched_parts: list[np.ndarray] = []

    # First block: keep up to L - 2M directly
    current = blocks[0]
    
    for next_b in blocks[1:]:
        # If current block has overlap with next block
        if current.shape[1] > overlap_len:
            head = current[:, :-overlap_len]
            tail = current[:, -overlap_len:]
            stitched_parts.append(head)
            
            # Next block starts with overlap_len
            next_head = next_b[:, :overlap_len]
            # Cross-fade
            blended = tail * win_out + next_head * win_in
            stitched_parts.append(blended)
            
            # Remaining part of next block becomes current
            current = next_b[:, overlap_len:]
        else:
            # Fallback if block is unusually small
            stitched_parts.append(current)
            current = next_b

    stitched_parts.append(current)
    return np.hstack(stitched_parts)
