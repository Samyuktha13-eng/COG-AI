from pathlib import Path

import pytest

from voice.asr_router import ASRRouter


class FakeEnglish:
    def transcribe(self, audio_path):
        return {"text": "hello", "language": "en", "engine": "whisper", "model": "base.en", "inference_seconds": 0.1, "device": "cpu"}


class FakeIndic:
    def transcribe(self, audio_path, language=None):
        return {"text": "namaste", "language": language, "confidence": 0.9, "model": "indic-conformer-600m-int8"}


def test_routes_english_to_whisper():
    result = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "English")
    assert result["engine"] == "whisper"
    assert result["language"] == "en"


def test_routes_indian_language_to_existing_indicconformer():
    result = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "Hindi")
    assert result["engine"] == "indicconformer"
    assert result["language"] == "hi"
    assert result["text"] == "namaste"


def test_rejects_unknown_language():
    with pytest.raises(ValueError, match="Unsupported ASR language"):
        ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "French")


def test_router_function_accepts_injected_engines():
    router = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic())
    assert router.transcribe(Path("input.wav"), "en")["model"] == "base.en"
