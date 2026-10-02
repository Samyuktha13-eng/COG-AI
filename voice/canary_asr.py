"""Adapter for the downloaded Indic-Transcribe Canary model."""

from __future__ import annotations

import importlib
import os
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

    @staticmethod
    def _contains_checkpoint(model_dir: Path) -> bool:
        return (model_dir / "config.json").is_file() and (model_dir / "model.safetensors").is_file()

    def resolve_model_dir(self) -> Path:
        configured = os.environ.get("INDIC_TRANSCRIBE_MODEL_DIR")
        candidates = [Path(configured)] if configured else []
        candidates.append(self.model_dir)

        cache_roots = [
            Path(value)
            for value in (os.environ.get("HF_HUB_CACHE"), os.environ.get("HF_CACHE_DIR"))
            if value
        ]
        hf_home = os.environ.get("HF_HOME")
        cache_roots.append(Path(hf_home) / "hub" if hf_home else Path.home() / ".cache" / "huggingface" / "hub")
        if os.name == "nt" and Path("D:/cogniv-huggingface").is_dir():
            cache_roots.append(Path("D:/cogniv-huggingface"))

        for cache_root in dict.fromkeys(cache_roots):
            repo_cache = cache_root / "models--bodhan-ai--indic-transcribe-core"
            refs_main = repo_cache / "refs" / "main"
            if refs_main.is_file():
                candidates.append(repo_cache / "snapshots" / refs_main.read_text(encoding="utf-8").strip())
            candidates.extend(sorted((repo_cache / "snapshots").glob("*"), reverse=True))

        for candidate in candidates:
            if self._contains_checkpoint(candidate):
                return candidate
        raise CanaryUnavailableError(
            "Indic-Transcribe checkpoint weights were not found. Expected config.json and model.safetensors "
            f"under {self.model_dir} or a configured Hugging Face cache."
        )

    def load(self) -> "IndicTranscribeASR":
        if self._engine is not None:
            return self
        try:
            resolved_model_dir = self.resolve_model_dir()
            model_path = str(resolved_model_dir.resolve())
            if model_path not in sys.path:
                sys.path.insert(0, model_path)
            runtime = importlib.import_module("indic_transcribe")
            self._engine = runtime.IndicTranscribe.from_pretrained(model_path, device=self.device)
            self.device = getattr(self._engine, "device", self.device)
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