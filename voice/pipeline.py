"""End-to-end Phase 1 voice orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent import generate_response
from .asr import IndicConformerASR
from .audio import load_audio, record_audio
from .intent import IntentRouter
from .tts import IndicF5TTS
from tools.memory import memory_search
from tools.reminders import ReminderStore


def _resolve_reference_audio(model_dir: Path, fallback_reference: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if fallback_reference is not None:
        candidates.append(Path(fallback_reference))
    candidates.extend([
        model_dir / "prompts" / "MAR_F_HAPPY_00001.wav",
        model_dir / "prompts" / "PAN_F_HAPPY_00001.wav",
        model_dir / "MAR_F_HAPPY_00001.wav",
        model_dir / "PAN_F_HAPPY_00001.wav",
    ])
    if model_dir.exists():
        candidates.extend(sorted(model_dir.rglob("*.wav")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if fallback_reference is not None:
        return Path(fallback_reference)
    raise FileNotFoundError(f"No IndicF5 reference audio found under {model_dir}")


class CognivVoicePipeline:
    def __init__(self, asr: Any, tts: Any, router: IntentRouter | None = None, reminders: ReminderStore | None = None) -> None:
        self.asr = asr
        self.tts = tts
        self.router = router or IntentRouter()
        self.reminders = reminders or ReminderStore()

    def run(self, input_audio: str | Path, output_audio: str | Path, language: str | None = None) -> dict[str, Any]:
        asr_result = self.asr.transcribe(input_audio, language=language) if language else self.asr.transcribe(input_audio)
        transcript = asr_result["text"] if isinstance(asr_result, dict) else asr_result
        intent = self.router.route(transcript)
        tool_result = self._run_tool(intent)
        response = generate_response(intent, tool_result)
        audio_output = self.tts.synthesize(response, output_audio)
        return {"audio_input": str(input_audio), "transcript": transcript, "asr": asr_result, "intent": intent, "tool_result": tool_result, "response_text": response, "audio_output": str(audio_output)}

    def run_microphone(self, input_audio: str | Path, output_audio: str | Path, duration: float = 5.0, device: Any = None, language: str | None = None) -> dict[str, Any]:
        recorded = record_audio(input_audio, duration=duration, device=device)
        return self.run(recorded, output_audio, language=language)

    def _run_tool(self, intent: dict[str, Any]) -> dict[str, Any] | None:
        kind = intent.get("intent")
        if kind == "create_reminder":
            return self.reminders.create_reminder(intent.get("task", ""), intent.get("time"))
        if kind == "query_memory":
            return memory_search(intent.get("query", ""))
        if kind == "start_game":
            return {"status": "not_connected", "message": "Cognitive games are not connected yet."}
        return None


def build_local_pipeline(project_root: str | Path) -> CognivVoicePipeline:
    root = Path(project_root)
    model_dir = root / "models" / "indicf5"
    reference_audio = _resolve_reference_audio(model_dir, root / "prompts" / "reference.wav")
    asr = IndicConformerASR(root / "models" / "indic-conformer-600m-int8")
    tts = IndicF5TTS(model_dir, reference_audio, "")
    return CognivVoicePipeline(asr, tts)
