"""Manual real IndicConformer integration test.

Run explicitly with RUN_REAL_ASR=1 after supplying a clear Hindi 16 kHz WAV.
"""

import os
from pathlib import Path

import pytest

from voice.asr import IndicConformerASR


@pytest.mark.skipif(os.getenv("RUN_REAL_ASR") != "1", reason="manual real-model test")
def test_real_indic_conformer_transcription():
    audio_path = Path(os.getenv("ASR_TEST_WAV", "live_utterance.wav"))
    assert audio_path.exists(), f"Missing ASR test WAV: {audio_path}"
    asr = IndicConformerASR("models/indic-conformer-600m-int8", language="Hindi", decoding="ctc")
    result = asr.transcribe(audio_path)
    assert set(result) == {"text", "language", "confidence", "model"}
    assert result["model"] == "indic-conformer-600m-int8"
    assert isinstance(result["text"], str)
    asr.unload()


def test_language_aliases():
    assert IndicConformerASR._language_code("English") == "en"
    assert IndicConformerASR._language_code("Hindi") == "hi"
    assert IndicConformerASR._language_code("Telugu") == "te"


def test_invalid_language_is_rejected_without_inference():
    asr = IndicConformerASR.__new__(IndicConformerASR)
    asr._engine = type("Engine", (), {"language_masks": {"hi": []}})()
    with pytest.raises(ValueError, match="not available"):
        asr.transcribe(([], 16000), language="English")
