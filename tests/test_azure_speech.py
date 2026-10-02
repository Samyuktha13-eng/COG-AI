import json
from pathlib import Path

import pytest

from voice.azure_speech import AzureSpeechClient, AzureSpeechError


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


def test_azure_asr_posts_pcm_and_maps_telugu_locale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    audio_path = tmp_path / "speech.wav"
    audio_path.write_bytes(b"wav-pcm")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(json.dumps({"RecognitionStatus": "Success", "DisplayText": "నమస్కారం"}).encode())

    monkeypatch.setattr("voice.azure_speech.urlopen", fake_urlopen)
    result = AzureSpeechClient("test-key", "centralindia").transcribe(audio_path, "te")

    request = captured["request"]
    assert "language=te-IN" in request.full_url
    assert request.data == b"wav-pcm"
    assert request.get_header("Content-type") == "audio/wav; codecs=audio/pcm; samplerate=16000"
    assert request.get_header("Ocp-apim-subscription-key") == "test-key"
    assert result["text"] == "నమస్కారం"
    assert result["engine"] == "azure-speech"


def test_azure_tts_returns_wav_and_escapes_text(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return FakeResponse(b"RIFF-audio")

    monkeypatch.setattr("voice.azure_speech.urlopen", fake_urlopen)
    audio = AzureSpeechClient("test-key", "centralindia").synthesize("A & B", "hi")
    request = captured["request"]

    assert audio.startswith(b"RIFF")
    assert b"hi-IN-SwaraNeural" in request.data
    assert b"A &amp; B" in request.data
    assert request.get_header("X-microsoft-outputformat") == "riff-24khz-16bit-mono-pcm"


def test_azure_client_requires_key_and_region():
    with pytest.raises(AzureSpeechError, match="AZURE_SPEECH_KEY"):
        AzureSpeechClient().synthesize("hello", "en")


def test_azure_client_rejects_invalid_region():
    with pytest.raises(ValueError, match="region"):
        AzureSpeechClient("test-key", "https://example.com")


def test_azure_upload_conversion_produces_mono_16khz_pcm(tmp_path: Path):
    import numpy as np
    import soundfile as sf

    from backend.app.api.voice import _convert_audio_to_azure_wav

    input_path = tmp_path / "recording.wav"
    samples = np.zeros((44100, 2), dtype=np.float32)
    sf.write(input_path, samples, 44100, subtype="PCM_16")
    output_path = _convert_audio_to_azure_wav(input_path)
    try:
        info = sf.info(output_path)
        assert info.samplerate == 16000
        assert info.channels == 1
        assert info.subtype == "PCM_16"
    finally:
        output_path.unlink(missing_ok=True)