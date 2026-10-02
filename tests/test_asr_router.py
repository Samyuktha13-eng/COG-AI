from pathlib import Path

import pytest

from voice.canary_asr import CanaryUnavailableError, IndicTranscribeASR
from voice.asr_router import ASRRouter, INDIAN_LANGUAGE_CODES


class FakeEnglish:
    def transcribe(self, audio_path):
        return {"text": "hello", "language": "en", "engine": "whisper", "model": "base.en", "inference_seconds": 0.1, "device": "cpu"}


class FakeIndic:
    def transcribe(self, audio_path, language=None):
        return {"text": "namaste", "language": language, "confidence": 0.9, "model": "indic-conformer-600m-int8"}


class FakeAzureSpeech:
    configured = True
    ASR_LOCALES = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}

    def transcribe(self, audio_path, language):
        return {"text": "నమస్కారం", "language": language, "engine": "azure-speech"}


@pytest.fixture(autouse=True)
def disable_azure_for_local_router_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)


def test_routes_english_to_whisper():
    result = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "English")
    assert result["engine"] == "whisper"
    assert result["language"] == "en"


def test_routes_indian_language_to_canary():
    result = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "Hindi")
    assert result["engine"] == "canary"
    assert result["language"] == "hi"
    assert result["text"] == "namaste"


def test_routes_supported_language_to_azure_speech():
    result = ASRRouter(
        english_asr=FakeEnglish(),
        indic_asr=FakeIndic(),
        azure_speech=FakeAzureSpeech(),
    ).transcribe("input.wav", "Telugu")

    assert result["engine"] == "azure-speech"
    assert result["language"] == "te"
    assert result["text"] == "నమస్కారం"


def test_routes_every_indian_language_to_canary():
    router = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic())

    for language in INDIAN_LANGUAGE_CODES:
        result = router.transcribe("input.wav", language)
        assert result["engine"] == "canary", language
        assert result["language"] == language, language


def test_rejects_unknown_language():
    with pytest.raises(ValueError, match="Unsupported ASR language"):
        ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic()).transcribe("input.wav", "French")


def test_router_function_accepts_injected_engines():
    router = ASRRouter(english_asr=FakeEnglish(), indic_asr=FakeIndic())
    assert router.transcribe(Path("input.wav"), "en")["model"] == "base.en"


def test_default_indic_engine_is_canary(tmp_path: Path):
    router = ASRRouter(project_root=tmp_path, english_asr=FakeEnglish())

    assert isinstance(router.indic_asr, IndicTranscribeASR)


def test_canary_resolves_huggingface_cache_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cache_root = tmp_path / "hf-cache"
    snapshot = cache_root / "models--bodhan-ai--indic-transcribe-core" / "snapshots" / "revision"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").touch()
    (snapshot / "model.safetensors").touch()
    refs_main = snapshot.parent.parent / "refs" / "main"
    refs_main.parent.mkdir()
    refs_main.write_text("revision", encoding="utf-8")
    monkeypatch.setenv("HF_CACHE_DIR", str(cache_root))

    assert IndicTranscribeASR(tmp_path / "missing-model").resolve_model_dir() == snapshot


def test_capabilities_marks_missing_canary_checkpoint_as_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    def missing_checkpoint(self):
        raise CanaryUnavailableError("Canary checkpoint missing for test")

    monkeypatch.setattr(IndicTranscribeASR, "resolve_model_dir", missing_checkpoint)
    result = ASRRouter.capabilities(tmp_path)

    assert result["engines"]["english"]["ready"] is False
    assert result["engines"]["indic"]["ready"] is False
    assert "checkpoint missing" in result["engines"]["indic"]["message"]
    assert {item["code"] for item in result["languages"]} >= {"en", "hi", "ta", "te", "kn"}
    assert all(not item["ready"] for item in result["languages"])
