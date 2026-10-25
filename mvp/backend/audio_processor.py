"""Audio Ingestion & Preprocessing Pipeline.

Implements Checklist Phase 1.1:
- 1.1.1 Multi-format audio decoder (.wav, .flac, .ogg, .mp3, .m4a)
- 1.1.2 Audio conditioning:
    * Stereo-to-mono channel averaging
    * RMS loudness normalization to -20 dBFS
    * 4th-order Butterworth high-pass filter (cutoff 30 Hz)
    * Bandlimited resampling to 22,050 Hz via polyphase filtering
"""

import io
import math
import os
from typing import Union
import numpy as np
import scipy.signal
import soundfile as sf

TARGET_SR = 22050
TARGET_RMS_DBFS = -20.0  # ~0.1 linear RMS amplitude
HIGHPASS_CUTOFF_HZ = 30.0
HIGHPASS_ORDER = 4
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_DURATION_SECONDS = 600.0  # 10 minutes
ALLOWED_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".m4a"}


class AudioProcessingError(Exception):
    """Base exception for audio processing errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnsupportedAudioFormatError(AudioProcessingError):
    def __init__(self, message: str = "Unsupported audio format. Supported: .wav, .flac, .ogg, .mp3, .m4a"):
        super().__init__(message, status_code=415)


class FileTooLargeError(AudioProcessingError):
    def __init__(self, message: str = "Audio file exceeds maximum size limit (50 MB)."):
        super().__init__(message, status_code=413)


class AudioDurationExceededError(AudioProcessingError):
    def __init__(self, message: str = "Audio file duration exceeds maximum limit (10 minutes)."):
        super().__init__(message, status_code=400)


def validate_file_metadata(filename: str, file_size: int):
    """Validate file extension and file size limit with path sanitization."""
    safe_filename = os.path.basename(filename)
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedAudioFormatError(
            f"File format '{ext}' is unsupported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed limit (50 MB)."
        )


def decode_audio(
    source: Union[str, bytes, io.BytesIO]
) -> tuple[np.ndarray, int]:
    """Decode audio into a numpy float array and native sample rate.

    Supports WAV, FLAC, OGG, and MP3 using soundfile.
    """
    try:
        if isinstance(source, bytes):
            file_obj = io.BytesIO(source)
            y, sr = sf.read(file_obj, dtype="float32")
        elif isinstance(source, io.BytesIO):
            y, sr = sf.read(source, dtype="float32")
        else:
            y, sr = sf.read(source, dtype="float32")
        return y, sr
    except Exception as e:
        # Fallback using librosa if available
        try:
            import librosa
            if isinstance(source, bytes):
                file_obj = io.BytesIO(source)
                y, sr = librosa.load(file_obj, sr=None, mono=False)
                # librosa gives (channels, samples) for stereo
                if y.ndim > 1:
                    y = y.T
            else:
                y, sr = librosa.load(source, sr=None, mono=False)
                if y.ndim > 1:
                    y = y.T
            return y.astype(np.float32), sr
        except Exception:
            raise UnsupportedAudioFormatError(f"Failed to decode audio stream: {str(e)}")


def downmix_to_mono(y: np.ndarray) -> np.ndarray:
    """Downmix multi-channel audio to mono via energy-preserving channel averaging."""
    if y.ndim == 1:
        return y.astype(np.float32)
    elif y.ndim == 2:
        # If shape is (samples, channels)
        if y.shape[1] <= y.shape[0]:
            return np.mean(y, axis=1, dtype=np.float32)
        else:  # shape is (channels, samples)
            return np.mean(y, axis=0, dtype=np.float32)
    else:
        return np.mean(y, axis=tuple(range(y.ndim - 1)), dtype=np.float32)


def apply_highpass_filter(
    y: np.ndarray,
    sr: int,
    cutoff_hz: float = HIGHPASS_CUTOFF_HZ,
    order: int = HIGHPASS_ORDER,
) -> np.ndarray:
    """Apply Butterworth 4th-order high-pass filter to remove stage rumble and DC offset."""
    nyquist = 0.5 * sr
    norm_cutoff = cutoff_hz / nyquist
    if norm_cutoff >= 1.0 or norm_cutoff <= 0.0:
        return y
    sos = scipy.signal.butter(order, norm_cutoff, btype="highpass", output="sos")
    return scipy.signal.sosfilt(sos, y).astype(np.float32)


def normalize_rms(y: np.ndarray, target_dbfs: float = TARGET_RMS_DBFS) -> np.ndarray:
    """Normalize audio loudness to target dBFS RMS (e.g. -20 dBFS)."""
    current_rms = float(np.sqrt(np.mean(y ** 2)))
    if current_rms < 1e-7:
        return y
    target_rms = 10.0 ** (target_dbfs / 20.0)
    gain = target_rms / current_rms
    y_norm = y * gain
    # Soft peak limiting to prevent digital clipping while preserving dynamics
    max_peak = float(np.max(np.abs(y_norm)))
    if max_peak > 0.99:
        y_norm = y_norm * (0.99 / max_peak)
    return y_norm.astype(np.float32)


def resample_audio(y: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    """Resample audio signal to target sample rate using polyphase filtering.

    Guards against CPU exhaustion on non-standard sample rates by limiting
    polyphase filter rational approximation (CWE-400).
    """
    if orig_sr == target_sr:
        return y
    gcd = math.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd

    # If gcd is small (e.g. prime sample rates), limit filter length to avoid CPU freeze
    if up > 500 or down > 500:
        import fractions
        frac = fractions.Fraction(target_sr, orig_sr).limit_denominator(200)
        up, down = frac.numerator, frac.denominator

    resampled = scipy.signal.resample_poly(y, up, down)
    return resampled.astype(np.float32)


def load_and_condition_audio(
    source: Union[str, bytes, io.BytesIO],
    filename: str = "audio.wav",
    target_sr: int = TARGET_SR,
    target_rms_dbfs: float = TARGET_RMS_DBFS,
    cutoff_hz: float = HIGHPASS_CUTOFF_HZ,
    max_duration_seconds: float = MAX_DURATION_SECONDS,
) -> tuple[np.ndarray, float]:
    """Execute complete ingestion and conditioning pipeline.

    Returns:
        (conditioned_audio_array, duration_seconds)
    """
    if isinstance(source, bytes):
        validate_file_metadata(filename, len(source))
    elif isinstance(source, str) and os.path.isfile(source):
        validate_file_metadata(filename, os.path.getsize(source))

    # 1. Decode audio
    y, orig_sr = decode_audio(source)
    # Sanitize any corrupted NaN or Inf samples from malformed audio streams
    y = np.nan_to_num(y, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
    
    # 2. Downmix to mono
    y_mono = downmix_to_mono(y)
    
    # Check duration bounds
    if len(y_mono) == 0:
        raise AudioProcessingError("Audio signal is empty (0 samples).", status_code=400)
    duration_s = float(len(y_mono) / orig_sr)
    if duration_s < 0.05:
        raise AudioProcessingError(f"Audio duration ({duration_s:.3f} s) is too short. Minimum 0.05 s required.", status_code=400)
    if duration_s > max_duration_seconds:
        raise AudioDurationExceededError(
            f"Audio duration ({duration_s:.1f} s) exceeds maximum allowed ({max_duration_seconds} s)."
        )

    # 3. Butterworth 4th-order High-pass filter (at native SR before resampling)
    y_hp = apply_highpass_filter(y_mono, orig_sr, cutoff_hz=cutoff_hz)
    
    # 4. Bandlimited Resampling to 22,050 Hz
    y_resampled = resample_audio(y_hp, orig_sr, target_sr)
    
    # 5. RMS Loudness Normalization to -20 dBFS
    y_norm = normalize_rms(y_resampled, target_rms_dbfs)
    
    final_duration = float(len(y_norm) / target_sr)
    return y_norm, round(final_duration, 4)
