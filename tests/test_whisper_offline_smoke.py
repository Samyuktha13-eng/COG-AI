"""Manual deployment smoke test for local-only Whisper initialization."""

import os

import pytest

from voice.english_asr import EnglishASR


@pytest.mark.skipif(os.getenv("RUN_REAL_WHISPER") != "1", reason="loads the real local checkpoint")
def test_whisper_initializes_without_download(monkeypatch):
    import whisper

    def forbidden_download(*args, **kwargs):
        raise AssertionError("Whisper attempted a network download.")

    monkeypatch.setattr(whisper, "_download", forbidden_download)
    asr = EnglishASR()
    asr.load()
    assert asr.model_path.is_file()
    asr.unload()
