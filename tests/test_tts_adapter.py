import asyncio
from pathlib import Path

import pytest

from voice.canary_asr import IndicTranscribeASR
from voice.pipeline import CognivVoicePipeline, build_local_pipeline
from voice.asr_router import INDIAN_LANGUAGE_CODES
from voice.tts import IndicParlerTTS, TTSUnavailableError
from backend.app.api.voice import voice_capabilities
from backend.app.api.voice import synthesize_voice
from backend.app.api.voice import _new_temporary_audio
from voice.azure_speech import AzureSpeechClient


def test_local_pipeline_uses_canary_and_indic_parler(tmp_path: Path):
    pipeline = build_local_pipeline(tmp_path)

    assert isinstance(pipeline.asr, IndicTranscribeASR)
    assert isinstance(pipeline.tts, IndicParlerTTS)
    assert pipeline.tts.model_dir == tmp_path / "models" / "indic-parler-tts"


def test_parler_rejects_unsupported_language_without_loading(tmp_path: Path):
    tts = IndicParlerTTS(tmp_path / "missing-model")

    with pytest.raises(ValueError, match="Unsupported Indic Parler language"):
        tts.synthesize("Hello", tmp_path / "output.wav", language="fr")

    assert tts._model is None


def test_parler_supports_all_asr_languages_and_marks_unofficial_languages():
    assert IndicParlerTTS.SUPPORTED_LANGUAGES == {"en", *INDIAN_LANGUAGE_CODES}
    assert IndicParlerTTS.EXPERIMENTAL_LANGUAGES == {"ks", "pa"}
    assert "Hindi" in IndicParlerTTS._description_for_language("hi")
    assert "Kashmiri" in IndicParlerTTS._description_for_language("ks")


def test_parler_normalizes_language_names_before_model_validation(tmp_path: Path):
    tts = IndicParlerTTS(tmp_path / "missing-model")

    with pytest.raises(TTSUnavailableError, match="Indic Parler checkpoint not found"):
        tts.synthesize("Hello", tmp_path / "output.wav", language="Marathi")


def test_voice_capabilities_reports_all_tts_languages(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    capabilities = voice_capabilities()
    tts_languages = capabilities["engines"]["tts"]["languages"]

    assert {language["code"] for language in tts_languages} == {"en", *INDIAN_LANGUAGE_CODES}
    assert {language["code"] for language in tts_languages if language["support"] == "experimental"} == {"ks", "pa"}


def test_sanskrit_tts_routes_to_local_generation(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    calls = []

    def fake_synthesize(text, output_path, language, project_root):
        calls.append((text, language))
        Path(output_path).write_bytes(b"RIFF-test-audio")

    monkeypatch.setattr("backend.app.api.voice._synthesize_with_local_parler", fake_synthesize)

    response = asyncio.run(synthesize_voice(text="नमस्ते", language="sa"))

    assert calls == [("नमस्ते", "sa")]
    assert Path(response.path).read_bytes() == b"RIFF-test-audio"
    Path(response.path).unlink()


def test_voice_capabilities_does_not_exclude_sanskrit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    capabilities = voice_capabilities()
    tts_languages = {language["code"]: language for language in capabilities["engines"]["tts"]["languages"]}

    assert tts_languages["sa"]["support"] != "unsupported"


def test_azure_tts_route_returns_wav_for_telugu(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "centralindia")
    calls = []

    def fake_synthesize(self, text, language):
        calls.append((text, language))
        return b"RIFF-test-audio"

    monkeypatch.setattr(AzureSpeechClient, "synthesize", fake_synthesize)
    response = asyncio.run(synthesize_voice(text="నమస్కారం", language="te"))

    assert response.media_type == "audio/wav"
    assert response.body == b"RIFF-test-audio"
    assert calls == [("నమస్కారం", "te")]


def test_voice_capabilities_reports_azure_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "centralindia")

    capabilities = voice_capabilities()
    tts_languages = {language["code"]: language for language in capabilities["engines"]["tts"]["languages"]}

    assert capabilities["engines"]["tts"]["provider"] == "azure-speech"
    assert tts_languages["hi"]["support"] == "azure-speech"
    assert tts_languages["te"]["support"] == "azure-speech"


def test_pipeline_passes_asr_language_to_tts_and_unloads_asr(tmp_path: Path):
    class FakeASR:
        unloaded = False

        def transcribe(self, audio_path):
            return {"text": "hello", "language": "hi"}

        def unload(self):
            self.unloaded = True

    class FakeTTS:
        language = None

        def synthesize(self, text, output_path, language=None):
            self.language = language
            return Path(output_path)

    asr = FakeASR()
    tts = FakeTTS()
    pipeline = CognivVoicePipeline(asr, tts)

    pipeline.run(tmp_path / "input.wav", tmp_path / "output.wav")

    assert tts.language == "hi"
    assert asr.unloaded


def test_voice_temporary_audio_uses_configured_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COGNIV_TEMP_DIR", str(tmp_path))

    with _new_temporary_audio(".wav") as temporary_audio:
        assert Path(temporary_audio.name).parent == tmp_path