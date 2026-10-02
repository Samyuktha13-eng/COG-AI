"""Explicit language router for English Whisper and Indic-Transcribe Canary."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any

from .canary_asr import CanaryUnavailableError, IndicTranscribeASR
from .azure_speech import AzureSpeechClient
from .english_asr import EnglishASR, WhisperUnavailableError, validate_whisper_model

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
LANGUAGE_LABELS = {"en": "English", **{code: name.title() for name, code in INDIAN_LANGUAGE_NAMES.items()}}


class ASRRouter:
    def __init__(
        self,
        project_root: str | Path | None = None,
        english_asr: Any = None,
        indic_asr: Any = None,
        azure_speech: AzureSpeechClient | None = None,
    ) -> None:
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        self.english_asr = english_asr or EnglishASR(root)
        self.indic_asr = indic_asr or IndicTranscribeASR(root / "models" / "indic-transcribe-core")
        self.azure_speech = azure_speech or AzureSpeechClient.from_environment()

    @staticmethod
    def language_code(language: str) -> str:
        if language is None:
            return "en"
        normalized = str(language).strip().lower().replace("_", "-")
        if not normalized:
            return "en"
        if normalized in {"english", "en", "en-in", "en-us"}:
            return "en"
        if normalized in INDIAN_LANGUAGE_CODES:
            return normalized
        if "-" in normalized:
            base = normalized.split("-", 1)[0]
            if base in INDIAN_LANGUAGE_CODES:
                return base
            if base == "en":
                return "en"
        if normalized in INDIAN_LANGUAGE_NAMES:
            return INDIAN_LANGUAGE_NAMES[normalized]
        return INDIAN_LANGUAGE_NAMES.get(normalized, normalized)

    @staticmethod
    def capabilities(project_root: str | Path | None = None) -> dict[str, Any]:
        root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
        azure_speech = AzureSpeechClient.from_environment()
        try:
            english_model = validate_whisper_model(root)
            english_ready = True
            english_message = f"Local Whisper model ready: {english_model.name}."
        except WhisperUnavailableError as error:
            english_ready = False
            english_message = str(error)

        indic_model_dir = root / "models" / "indic-transcribe-core"
        indic_runtime = IndicTranscribeASR(indic_model_dir)
        try:
            resolved_model_dir = indic_runtime.resolve_model_dir()
            missing_dependencies = [
                package
                for package in ("torch", "torchaudio", "transformers", "sentencepiece", "soundfile")
                if importlib.util.find_spec(package) is None
            ]
            indic_ready = not missing_dependencies
            indic_message = (
                f"Indic-Transcribe Canary model ready: {resolved_model_dir}."
                if indic_ready
                else "Indic-Transcribe Canary is missing dependencies: " + ", ".join(missing_dependencies)
            )
        except CanaryUnavailableError as error:
            indic_ready = False
            indic_message = str(error)

        azure_asr_languages = set(AzureSpeechClient.ASR_LOCALES)
        languages = [
            {
                "code": "en",
                "name": LANGUAGE_LABELS["en"],
                "ready": english_ready or (azure_speech.configured and "en" in azure_asr_languages),
                "engine": "azure-speech" if azure_speech.configured and "en" in azure_asr_languages else "whisper",
            }
        ]
        languages.extend(
            {
                "code": code,
                "name": LANGUAGE_LABELS[code],
                "ready": indic_ready or (azure_speech.configured and code in azure_asr_languages),
                "engine": "azure-speech" if azure_speech.configured and code in azure_asr_languages else "canary",
            }
            for code in sorted(INDIAN_LANGUAGE_CODES)
        )
        return {
            "languages": languages,
            "engines": {
                "english": {
                    "ready": english_ready or (azure_speech.configured and "en" in azure_asr_languages),
                    "message": "Azure Speech configured." if azure_speech.configured else english_message,
                },
                "indic": {
                    "ready": indic_ready or (azure_speech.configured and bool(azure_asr_languages - {"en"})),
                    "message": "Azure Speech configured for supported Indic languages." if azure_speech.configured else indic_message,
                },
                "azure": {
                    "ready": azure_speech.configured,
                    "message": "Azure Speech is configured." if azure_speech.configured else "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to enable the free Azure Speech tier.",
                },
            },
        }

    def transcribe(self, audio_path: str | Path, language: str) -> dict[str, Any]:
        code = self.language_code(language)
        if code not in {"en", *INDIAN_LANGUAGE_CODES}:
            raise ValueError(f"Unsupported ASR language: {language}")
        if self.azure_speech.configured and code in self.azure_speech.ASR_LOCALES:
            started = time.perf_counter()
            result = self.azure_speech.transcribe(audio_path, code)
            normalized = dict(result)
            normalized.setdefault("engine", "azure-speech")
            normalized.setdefault("model", "speech-to-text")
            normalized["language"] = code
            normalized.setdefault("inference_seconds", time.perf_counter() - started)
            return normalized
        if code == "en":
            return self.english_asr.transcribe(audio_path)
        started = time.perf_counter()
        result = self.indic_asr.transcribe(audio_path, language=code)
        normalized = dict(result)
        normalized.setdefault("engine", "canary")
        normalized.setdefault("model", "indic-transcribe-core")
        normalized.setdefault("device", "cpu")
        normalized["language"] = code
        normalized.setdefault("inference_seconds", time.perf_counter() - started)
        return normalized


def transcribe(audio_path: str | Path, language: str, **kwargs: Any) -> dict[str, Any]:
    """Route one transcription using explicit language selection."""
    return ASRRouter(**kwargs).transcribe(audio_path, language)
