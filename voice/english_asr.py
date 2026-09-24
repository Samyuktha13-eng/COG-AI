"""Local-only English Whisper ASR."""

from __future__ import annotations

import time
import os
from pathlib import Path
from typing import Any

import numpy as np

from .audio import load_audio, prepare_for_asr

DEFAULT_MODEL_RELATIVE_PATH = Path("models") / "whisper-base-en" / "base.en.pt"
WHISPER_MODEL_PATH = "models/whisper-base-en/base.en.pt"


class WhisperUnavailableError(RuntimeError):
    """Raised when the local Whisper deployment cannot be used."""


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_whisper_model(project_root_path: str | Path | None = None) -> Path:
    root = Path(project_root_path) if project_root_path else project_root()
    model_path = root / DEFAULT_MODEL_RELATIVE_PATH
    if not model_path.is_file() or not model_path.stat().st_size:
        raise WhisperUnavailableError("Whisper base.en weights are missing from the deployment package.")
    if not os.access(model_path, os.R_OK):
        raise WhisperUnavailableError(f"Whisper base.en weights are not readable: {model_path}")
    return model_path


class EnglishASR:
    """Lazy, local-only Whisper base.en inference."""

    def __init__(self, project_root_path: str | Path | None = None, device: str | None = None) -> None:
        self.project_root = Path(project_root_path) if project_root_path else project_root()
        self.device = device
        self._model: Any = None

    @property
    def model_path(self) -> Path:
        return self.project_root / DEFAULT_MODEL_RELATIVE_PATH

    def load(self) -> "EnglishASR":
        if self._model is not None:
            return self
        model_path = validate_whisper_model(self.project_root)
        try:
            import torch
            import whisper

            selected_device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.device = selected_device
            self._model = whisper.load_model(str(model_path), device=selected_device, download_root=str(model_path.parent))
        except Exception as exc:
            raise WhisperUnavailableError(f"Local Whisper base.en failed to load: {exc}") from exc
        return self

    def transcribe(self, audio_path: str | Path) -> dict[str, Any]:
        self.load()
        samples, sample_rate = load_audio(audio_path)
        samples, sample_rate = prepare_for_asr(samples, sample_rate)
        started = time.perf_counter()
        try:
            result = self._model.transcribe(
                np.asarray(samples, dtype=np.float32),
                language="en",
                fp16=self.device == "cuda",
                temperature=0,
            )
        except Exception as exc:
            raise WhisperUnavailableError(f"Whisper inference failed: {exc}") from exc
        return {
            "text": str(result.get("text", "")).strip(),
            "language": "en",
            "engine": "whisper",
            "model": "base.en",
            "inference_seconds": time.perf_counter() - started,
            "device": self.device,
        }

    def unload(self) -> None:
        self._model = None
