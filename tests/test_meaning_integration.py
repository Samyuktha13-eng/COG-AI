"""Manual real Whisper-to-meaning integration test."""

import json
import os
from pathlib import Path

import pytest

from voice.english_asr import EnglishASR
from voice.meaning import understand
from voice.semantic_validation import validate_semantic_result


@pytest.mark.skipif(os.getenv("RUN_REAL_MEANING") != "1", reason="manual real-model test")
def test_real_whisper_to_meaning(capsys):
    audio_path = Path(os.getenv("MEANING_TEST_WAV", "test_voice_16k.wav"))
    assert audio_path.exists(), f"Missing meaning test WAV: {audio_path}"
    raw = EnglishASR().transcribe(audio_path)
    semantic = understand(raw["text"], raw["language"])
    validate_semantic_result(semantic)
    print("RAW ASR:", raw["text"])
    print("SEMANTIC INTENT:", semantic["intent"])
    print("ENTITIES:", json.dumps(semantic["entities"], ensure_ascii=False))
    print("CONFIDENCE:", semantic["confidence"])
    print("NEEDS CLARIFICATION:", semantic["needs_clarification"])
    assert semantic["intent"] == "create_reminder"
