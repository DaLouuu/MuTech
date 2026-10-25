"""Ported multif0 (Cuesta et al. 2020, model3) as a robust, non-blocking inference service.

Implements Checklist Phase 1 & Phase 3:
- 1.1 Ingestion & conditioning integration (audio_processor.py)
- 1.2 Parabolic sub-bin peak interpolation & cents calculation (dsp_utils.py)
- 1.3 Contiguous block overlap & Hann cross-fading for long files
- 3.1 Frame-to-frame trajectory linking (contour_tracker.py)
- 3.2 SATB voice part partitioning
- 3.3 Ensemble intonation drift & polyphony analytics (analytics.py)
"""

import os
import time
from typing import Optional, Union, Callable
import numpy as np

from dsp_utils import (
    refine_salience_peaks,
    stitch_overlapping_blocks,
    bin_to_frequency,
    FMIN,
    BINS_PER_OCTAVE,
    N_BINS,
)
from audio_processor import load_and_condition_audio, TARGET_SR
from contour_tracker import link_contours
from analytics import compute_ensemble_analytics

REPO = os.environ.get("MF0_REPO", "./multif0-estimation-polyvocals")
HOP = 256
SR = TARGET_SR
BLOCK_SIZE = 5000       # ~58.05 s
OVERLAP_MARGIN = 250    # ~2.90 s (overlap length = 500 frames)
HOP_STRIDE = BLOCK_SIZE - 2 * OVERLAP_MARGIN  # 4500 frames

_model = None
_pump = None
_model_load_error: Optional[str] = None


def _build_model():
    """Rebuild multif0 Late/Deep (model3) architecture in Keras 3."""
    import keras
    import tensorflow as tf
    from keras import layers

    bn = [0]
    def BN():
        bn[0] += 1
        return layers.BatchNormalization(name=f"batch_normalization_{bn[0]}")

    def base(x, let):
        x = BN()(x)
        for nm, f, k in [
            ("conv1", 16, (5, 5)),
            ("conv2", 32, (5, 5)),
            ("conv3", 32, (5, 5)),
            ("conv4", 32, (5, 5)),
            ("harm1", 32, (70, 3)),
            ("harm2", 32, (70, 3)),
        ]:
            x = layers.Conv2D(f, k, padding="same", activation="relu", name=nm + let)(x)
            x = BN()(x)
        return x

    i1 = keras.Input((None, None, 5))
    i2 = keras.Input((None, None, 5))
    c = layers.Concatenate()([base(i1, "a"), base(i2, "b")])
    x = layers.Conv2D(64, (3, 3), padding="same", activation="relu", name="conv7")(c)
    x = BN()(x)
    x = layers.Conv2D(64, (3, 3), padding="same", activation="relu", name="conv8")(x)
    x = BN()(x)
    x = layers.Conv2D(8, (360, 1), padding="same", activation="sigmoid", name="distribution")(x)
    x = BN()(x)
    x = layers.Conv2D(1, (1, 1), padding="same", activation="sigmoid", name="squishy")(x)
    return keras.Model([i1, i2], layers.Lambda(lambda z: tf.squeeze(z, axis=3))(x))


def is_model_loaded() -> bool:
    """Check whether neural network model is loaded in memory."""
    return _model is not None


def get_model_status() -> dict:
    return {
        "loaded": _model is not None,
        "error": _model_load_error,
        "repo_path": REPO,
    }


def load():
    """Load Keras 3 multif0 model weights and initialize pumpp transform."""
    global _model, _pump, _model_load_error
    if _model is not None:
        return

    try:
        import h5py
        import pumpp
        from keras import layers

        weights_path = os.path.join(REPO, "models", "exp3multif0.pkl")
        if not os.path.exists(weights_path):
            _model_load_error = f"Weights not found at {weights_path}"
            return

        m = _build_model()
        with h5py.File(weights_path, "r") as f:
            weights = f["model_weights"]
            for L in m.layers:
                if L.name in weights:
                    g = weights[L.name][L.name]
                    if isinstance(L, layers.Conv2D):
                        L.set_weights([g["kernel:0"][()], g["bias:0"][()]])
                    elif isinstance(L, layers.BatchNormalization):
                        L.set_weights([
                            g["gamma:0"][()],
                            g["beta:0"][()],
                            g["moving_mean:0"][()],
                            g["moving_variance:0"][()],
                        ])
        _model = m
        _pump = pumpp.Pump(
            pumpp.feature.HCQTPhaseDiff(
                name="dphase",
                sr=SR,
                hop_length=HOP,
                fmin=FMIN,
                n_octaves=6,
                over_sample=5,
                harmonics=[1, 2, 3, 4, 5],
                log=True,
            )
        )
        _model_load_error = None
    except Exception as e:
        _model_load_error = str(e)


def activations(
    path_or_y: Union[str, np.ndarray],
    progress_callback: Optional[Callable[[float], None]] = None,
) -> np.ndarray:
    """Run model inference over audio features with contiguous block overlap stitching.

    Implements Checklist 1.3:
    - Overlapping chunks with block size 5000 and overlap margin 250
    - Hann window blending across adjacent chunks
    """
    load()
    if _model is None or _pump is None:
        raise RuntimeError(
            f"multif0 model is not loaded. Details: {_model_load_error or 'Weights file missing'}"
        )

    # Feature extraction via pumpp
    if isinstance(path_or_y, str):
        d = _pump(audio_f=path_or_y)
    else:
        d = _pump(y=path_or_y, sr=SR)

    if progress_callback:
        progress_callback(20.0)

    mag = d["dphase/mag"][0].transpose(1, 2, 0)[None]      # (1, 360, n_frames, 5)
    dph = d["dphase/dphase"][0].transpose(1, 2, 0)[None]   # (1, 360, n_frames, 5)
    total_frames = mag.shape[2]

    # If audio is shorter than a single block, run in one pass
    if total_frames <= BLOCK_SIZE:
        out = _model.predict(
            [
                np.transpose(mag, (0, 1, 3, 2)),
                np.transpose(dph, (0, 1, 3, 2)),
            ],
            verbose=0,
        )[0]  # (360, total_frames)
        if progress_callback:
            progress_callback(75.0)
        return out

    # Contiguous overlapping sliding window
    blocks: list[np.ndarray] = []
    starts = list(range(0, total_frames, HOP_STRIDE))
    total_blocks = len(starts)

    for b_idx, start in enumerate(starts):
        end = min(total_frames, start + BLOCK_SIZE)
        mag_chunk = mag[:, :, start:end, :]
        dph_chunk = dph[:, :, start:end, :]

        chunk_out = _model.predict(
            [
                np.transpose(mag_chunk, (0, 1, 3, 2)),
                np.transpose(dph_chunk, (0, 1, 3, 2)),
            ],
            verbose=0,
        )[0]
        blocks.append(chunk_out)

        if progress_callback:
            pct = 20.0 + ((b_idx + 1) / total_blocks) * 55.0
            progress_callback(min(75.0, pct))

        if end >= total_frames:
            break

    # Blend and stitch using Hann cross-fade
    stitched = stitch_overlapping_blocks(blocks, block_size=BLOCK_SIZE, overlap_margin=OVERLAP_MARGIN)
    if progress_callback:
        progress_callback(78.0)
    return stitched


def transcribe(
    audio_source: Union[str, bytes],
    filename: str = "audio.wav",
    threshold: float = 0.5,
    hop: int = 1,
    link_voice_contours: bool = True,
    activation_override: Optional[np.ndarray] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> dict:
    """Execute complete end-to-end transcription pipeline.

    Conforms strictly to TranscribeResponse schema.
    """
    t0 = time.time()
    if progress_callback:
        progress_callback(5.0)

    # 1. Audio Ingestion & Conditioning Pipeline (Checklist 1.1)
    if activation_override is None:
        y_conditioned, duration_s = load_and_condition_audio(audio_source, filename=filename)
        if progress_callback:
            progress_callback(15.0)
        act = activations(y_conditioned, progress_callback=progress_callback)
    else:
        act = activation_override
        duration_s = round(float(act.shape[1] * (HOP / SR)), 4)
        if progress_callback:
            progress_callback(75.0)

    # 2. Peak Refinement & Cents Deviation (Checklist 1.2)
    raw_f0, refined_f0, notes, cents = refine_salience_peaks(
        act, threshold=threshold, fmin=FMIN, bpo=BINS_PER_OCTAVE
    )
    if progress_callback:
        progress_callback(85.0)

    n_frames = act.shape[1]
    hop_s = HOP / SR
    times = [round(float(i * hop_s), 4) for i in range(n_frames)]

    # 3. Contour Linking & SATB Voicing (Checklist 3.1 & 3.2)
    contours = []
    if link_voice_contours:
        contours = link_contours(times, refined_f0)
    if progress_callback:
        progress_callback(92.0)

    # 4. Ensemble Performance Analytics (Checklist 3.3)
    analytics = compute_ensemble_analytics(cents, refined_f0, contours=contours)
    if progress_callback:
        progress_callback(97.0)

    # 5. Build Sub-sampled Frames Response
    from dsp_utils import identify_vertical_chord
    frames_data = []
    for i in range(0, n_frames, hop):
        pitches = refined_f0[i]
        chord = identify_vertical_chord(pitches) if len(pitches) >= 2 else (notes[i][0] if len(notes[i]) == 1 else "")
        frames_data.append({
            "t": times[i],
            "f0": raw_f0[i],
            "f0_refined": refined_f0[i],
            "notes": notes[i],
            "cents": cents[i],
            "chord": chord,
        })

    process_s = round(time.time() - t0, 2)
    if progress_callback:
        progress_callback(100.0)

    return {
        "sample_rate": SR,
        "hop_s": round(hop_s, 5),
        "n_frames": n_frames,
        "duration_s": duration_s,
        "threshold": threshold,
        "process_s": process_s,
        "frames": frames_data,
        "contours": contours,
        "analytics": analytics,
    }
