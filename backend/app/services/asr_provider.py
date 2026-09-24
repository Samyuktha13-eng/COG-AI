from pathlib import Path
from typing import Protocol
from uuid import uuid4

from ..models.recognition import SpeechTranscript
from ..models.speech_job import SpeechJob


class ASRProvider(Protocol):
    async def submit(self, audio_path: str, session_id: str, language: str | None = None) -> SpeechJob: ...

    async def get_result(self, job: SpeechJob) -> SpeechTranscript | None: ...


class DeterministicASRProvider:
    """Test adapter; production callers can replace it without changing gameplay."""

    def __init__(self, transcript: str = ""):
        self.transcript = transcript

    async def submit(self, audio_path: str, session_id: str, language: str | None = None) -> SpeechJob:
        return SpeechJob(job_id=str(uuid4()), session_id=session_id, asset_id=audio_path, status="completed")

    async def get_result(self, job: SpeechJob) -> SpeechTranscript:
        return SpeechTranscript(text=self.transcript, language="en", confidence=1.0, engine="deterministic")


class IndicConformerASRProvider:
    """Adapter for the existing local Indic Conformer runtime."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)

    async def submit(self, audio_path: str, session_id: str, language: str | None = None) -> SpeechJob:
        return SpeechJob(
            job_id=str(uuid4()),
            session_id=session_id,
            asset_id=audio_path,
            status="queued",
            language=language,
        )

    async def get_result(self, job: SpeechJob) -> SpeechTranscript:
        from voice.asr_router import ASRRouter

        if not job.language:
            raise ValueError("Indic Conformer requires an explicit language before transcription.")
        result = ASRRouter(self.project_root).transcribe(job.asset_id, job.language)
        return SpeechTranscript(
            text=result.get("text", ""),
            language=result.get("language", job.language),
            confidence=result.get("confidence"),
            engine=result.get("model", "indic-conformer"),
        )
