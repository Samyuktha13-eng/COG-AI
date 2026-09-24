"""Microphone and WAV preparation utilities for speech recognition."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np

TARGET_SAMPLE_RATE = 16_000


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a PCM WAV file as mono float32 samples."""
    try:
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError("Audio loading requires soundfile.") from exc
    samples, sample_rate = sf.read(str(path), dtype="float32", always_2d=False)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    return np.asarray(samples, dtype=np.float32), int(sample_rate)


def resample_audio(samples: np.ndarray, source_rate: int, target_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """Resample audio with linear interpolation only when rates differ."""
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("Sample rates must be positive.")
    if source_rate == target_rate or samples.size == 0:
        return samples
    target_length = max(1, round(samples.size * target_rate / source_rate))
    source_positions = np.linspace(0, samples.size - 1, num=target_length)
    return np.interp(source_positions, np.arange(samples.size), samples).astype(np.float32)


def prepare_for_asr(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, int]:
    """Convert audio to mono, float32, and the ASR sample rate."""
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if samples.ndim != 1:
        raise ValueError("Audio must be a one-dimensional mono signal or a two-dimensional channel array.")
    peak = float(np.max(np.abs(samples), initial=0.0))
    if peak > 1.0:
        samples = samples / peak
    return resample_audio(samples, sample_rate), TARGET_SAMPLE_RATE


def record_audio(
    output_path: str | Path,
    duration: float = 5.0,
    device: Any = None,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> Path:
    """Record a mono WAV and always release the microphone stream."""
    if duration <= 0:
        raise ValueError("Recording duration must be positive.")
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError("Microphone recording requires sounddevice and soundfile.") from exc
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    stream = None
    try:
        stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", device=device)
        stream.start()
        frames, _ = stream.read(round(duration * sample_rate))
        sf.write(str(output), np.asarray(frames).reshape(-1), sample_rate, subtype="PCM_16")
    except Exception as exc:
        raise RuntimeError(f"Microphone recording failed: {exc}") from exc
    finally:
        if stream is not None:
            stream.stop()
            stream.close()
    return output
