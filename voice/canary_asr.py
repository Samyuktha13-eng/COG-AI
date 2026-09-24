"""Adapter for the downloaded Indic-Transcribe Canary model."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


class CanaryUnavailableError(RuntimeError):
    """Raised when the local Canary runtime cannot be loaded."""


class IndicTranscribeASR:
    """Load Indic-Transcribe lazily and reuse the local model instance."""

    def __init__(self, model_dir: str | Path, device: str | None = None) -> None:
        self.model_dir = Path(model_dir)
        self.device = device
        self._engine: Any = None

    def load(self) -> "IndicTranscribeASR":
        if self._engine is not None:
            return self
        if not self.model_dir.exists():
            raise CanaryUnavailableError(f"Indic-Transcribe model not found: {self.model_dir}")
        try:
            model_path = str(self.model_dir.resolve())
            if model_path not in sys.path:
                sys.path.insert(0, model_path)
            runtime = importlib.import_module("indic_transcribe")
            self._engine = runtime.IndicTranscribe.from_pretrained(model_path, device=self.device)
        except Exception as exc:
            raise CanaryUnavailableError(f"Indic-Transcribe failed to load: {exc}") from exc
        return self

    def transcribe(self, audio_path: str | Path, language: str | None = None) -> dict[str, Any]:
        self.load()
        try:
            text = self._engine.transcribe(str(audio_path), lang=language)
        except Exception as exc:
            raise CanaryUnavailableError(f"Indic-Transcribe inference failed: {exc}") from exc
        return {
            "text": str(text).strip(),
            "language": language,
            "confidence": None,
            "model": "indic-transcribe-core",
            "engine": "canary",
            "device": self.device or "cpu",
        }

    def unload(self) -> None:
        self._engine = None