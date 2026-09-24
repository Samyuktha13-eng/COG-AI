"""Lazy adapter for the existing IndicF5 Transformers implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import sys


class TTSUnavailableError(RuntimeError):
    """Raised when IndicF5 cannot be loaded or used."""


class IndicF5TTS:
    def __init__(self, model_dir: str | Path, reference_audio: str | Path, reference_text: str, device: str | None = None) -> None:
        self.model_dir = Path(model_dir)
        self.reference_audio = Path(reference_audio)
        self.reference_text = reference_text
        self.device = device
        self._model: Any = None

    def load(self) -> "IndicF5TTS":
        if not self.model_dir.exists():
            raise TTSUnavailableError(f"IndicF5 model directory not found: {self.model_dir}")
        if not self.reference_audio.exists():
            raise TTSUnavailableError(f"IndicF5 reference audio not found: {self.reference_audio}")
        try:
            model_path = str(self.model_dir.resolve())
            if model_path not in sys.path:
                sys.path.insert(0, model_path)
            from transformers import AutoModel
            kwargs: dict[str, Any] = {"trust_remote_code": True, "local_files_only": True}
            if self.device:
                kwargs["device_map"] = self.device
            self._model = AutoModel.from_pretrained(str(self.model_dir), **kwargs)
            if hasattr(self._model, "eval"):
                self._model.eval()
        except Exception as exc:
            raise TTSUnavailableError(f"IndicF5 failed to load: {exc}") from exc
        return self

    def synthesize(self, text: str, output_path: str | Path) -> Path:
        if not text or not text.strip():
            raise ValueError("TTS text cannot be empty.")
        if self._model is None:
            self.load()
        try:
            import numpy as np
            import soundfile as sf
            audio = self._model(
                text.strip(),
                ref_audio_path=str(self.reference_audio),
                ref_text=self.reference_text,
            )
            if getattr(audio, "dtype", None) == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output), np.asarray(audio, dtype=np.float32), samplerate=24000)
            return output
        except Exception as exc:
            raise TTSUnavailableError(f"IndicF5 synthesis failed: {exc}") from exc

    def unload(self) -> None:
        self._model = None
