from pathlib import Path

import pytest

from voice.english_asr import EnglishASR, WhisperUnavailableError, validate_whisper_model


def test_validate_whisper_model_missing(tmp_path: Path):
    with pytest.raises(WhisperUnavailableError, match="missing from the deployment package"):
        validate_whisper_model(tmp_path)


def test_english_asr_loads_once_and_returns_structured_result(tmp_path: Path, monkeypatch):
    model_path = tmp_path / "models" / "whisper-base-en" / "base.en.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"checkpoint")
    calls = []

    class FakeModel:
        def transcribe(self, samples, **kwargs):
            return {"text": "hello from whisper"}

    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return False

    class FakeWhisper:
        @staticmethod
        def load_model(path, **kwargs):
            calls.append((path, kwargs))
            return FakeModel()

    monkeypatch.setitem(__import__("sys").modules, "torch", FakeTorch)
    monkeypatch.setitem(__import__("sys").modules, "whisper", FakeWhisper)
    monkeypatch.setattr("voice.english_asr.load_audio", lambda path: (__import__("numpy").zeros(1600), 16000))
    asr = EnglishASR(tmp_path)
    result = asr.transcribe(tmp_path / "input.wav")
    asr.load()
    assert len(calls) == 1
    assert calls[0][0] == str(model_path)
    assert result["text"] == "hello from whisper"
    assert result["language"] == "en"
    assert result["engine"] == "whisper"
    assert result["model"] == "base.en"
    assert result["device"] == "cpu"


def test_english_asr_missing_weights_never_downloads(tmp_path: Path):
    with pytest.raises(WhisperUnavailableError, match="missing from the deployment package"):
        EnglishASR(tmp_path).load()
