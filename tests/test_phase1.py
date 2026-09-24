from pathlib import Path

import numpy as np
import soundfile as sf

from tools.memory import memory_search
from tools.reminders import ReminderStore
from voice.agent import generate_response
from voice.audio import prepare_for_asr, resample_audio
from voice.intent import IntentRouter
from voice.pipeline import CognivVoicePipeline


def test_audio_preparation_is_mono_16khz():
    samples, rate = prepare_for_asr(np.ones((160, 2), dtype=np.float32) * 2, 8000)
    assert rate == 16000
    assert samples.ndim == 1
    assert len(samples) == 320
    assert np.max(np.abs(samples)) <= 1


def test_resample_empty_audio():
    assert resample_audio(np.array([], dtype=np.float32), 8000).size == 0


def test_intent_shapes():
    router = IntentRouter()
    assert router.route("Remind me to drink water at 10:30.") == {"intent": "create_reminder", "task": "drink water", "time": "10:30"}
    assert router.route("Start a memory game") == {"intent": "start_game", "game": "memory"}
    assert router.route("Who is my daughter?") == {"intent": "query_memory", "query": "Who is my daughter?"}


def test_reminder_tool_only_reports_success_after_creation():
    store = ReminderStore()
    result = store.create_reminder("drink water", "10:30")
    assert result["status"] == "success"
    assert store.get_reminders()[0]["task"] == "drink water"
    assert store.cancel_reminder("missing")["status"] == "error"


def test_memory_placeholder():
    assert memory_search("Who is my daughter?")["status"] == "not_connected"


def test_response_generation():
    assert "couldn't" in generate_response({"intent": "create_reminder"}, {"status": "error"})
    assert generate_response({"intent": "query_memory"}, memory_search("x")) == "I don't have that memory available yet."


def test_pipeline_with_mocks(tmp_path: Path):
    class FakeASR:
        def transcribe(self, audio):
            return "Remind me to drink water at 10:30"

    class FakeTTS:
        def synthesize(self, text, output):
            Path(output).write_bytes(b"wav")
            return Path(output)

    result = CognivVoicePipeline(FakeASR(), FakeTTS()).run(tmp_path / "input.wav", tmp_path / "output.wav")
    assert result["intent"]["intent"] == "create_reminder"
    assert result["tool_result"]["status"] == "success"
    assert result["audio_output"] == str(tmp_path / "output.wav")
    assert (tmp_path / "output.wav").exists()


def test_build_local_pipeline_uses_existing_indicf5_reference_prompt(tmp_path: Path):
    project_root = tmp_path / "project"
    (project_root / "models" / "indicf5").mkdir(parents=True)
    reference = project_root / "models" / "indicf5" / "prompts" / "MAR_F_HAPPY_00001.wav"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"wav")
    (project_root / "models" / "indic-conformer-600m-int8").mkdir(parents=True)

    pipeline = __import__("voice.pipeline", fromlist=["build_local_pipeline"]).build_local_pipeline(project_root)

    assert pipeline.tts.reference_audio == reference
    assert pipeline.tts.reference_audio.exists()
