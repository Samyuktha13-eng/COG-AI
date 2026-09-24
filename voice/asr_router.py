"""Explicit language router for English Whisper and IndicConformer."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .canary_asr import IndicTranscribeASR
from .english_asr import EnglishASR

INDIAN_LANGUAGE_CODES = {
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "kok", "ks", "mai", "ml",
    "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur",
}
INDIAN_LANGUAGE_NAMES = {
    "assamese": "as", "bengali": "bn", "bodo": "brx", "dogri": "doi", "gujarati": "gu",
    "hindi": "hi", "kannada": "kn", "kashmiri": "ks", "konkani": "kok", "maithili": "mai",
    "malayalam": "ml", "manipuri": "mni", "marathi": "mr", "nepali": "ne", "odia": "or",
    "punjabi": "pa", "sanskrit": "sa", "santali": "sat", "sindhi": "sd", "tamil": "ta",
    "telugu": "te", "urdu": "ur",
}


class ASRRouter:
    def __init__(self, project_root: str | Path | None = None, english_asr: Any = None, indic_asr: Any = None) -> None:
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.english_asr = english_asr or EnglishASR(root)
        self.indic_asr = indic_asr or IndicTranscribeASR(root / "models" / "indic-conformer-600m-int8")

    @staticmethod
    def language_code(language: str) -> str:
        normalized = language.strip().lower()
        if normalized in {"english", "en"}:
            return "en"
        return INDIAN_LANGUAGE_NAMES.get(normalized, normalized)

    def transcribe(self, audio_path: str | Path, language: str) -> dict[str, Any]:
        code = self.language_code(language)
        if code == "en":
            return self.english_asr.transcribe(audio_path)
        if code not in INDIAN_LANGUAGE_CODES:
            raise ValueError(f"Unsupported ASR language: {language}")
        started = time.perf_counter()
        result = self.indic_asr.transcribe(audio_path, language=code)
        normalized = dict(result)
        normalized.setdefault("engine", "indicconformer")
        normalized.setdefault("model", "indic-conformer-600m-int8")
        normalized.setdefault("device", "cpu")
        normalized["language"] = code
        normalized.setdefault("inference_seconds", time.perf_counter() - started)
        return normalized


def transcribe(audio_path: str | Path, language: str, **kwargs: Any) -> dict[str, Any]:
    """Route one transcription using explicit language selection."""
    return ASRRouter(**kwargs).transcribe(audio_path, language)
