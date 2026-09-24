"""Manual real Whisper integration test."""

import os
from pathlib import Path

import pytest

from voice.english_asr import EnglishASR


@pytest.mark.skipif(os.getenv("RUN_REAL_WHISPER") != "1", reason="manual real-model test")
def test_real_local_whisper_transcription():
    audio_path = Path(os.getenv("WHISPER_TEST_WAV", "test_voice_16k.wav"))
    assert audio_path.exists(), f"Missing Whisper test WAV: {audio_path}"
    result = EnglishASR().transcribe(audio_path)
    assert result["engine"] == "whisper"
    assert result["model"] == "base.en"
    assert result["language"] == "en"
    assert isinstance(result["text"], str)
    assert result["inference_seconds"] >= 0
