from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: str
    confidence: float | None = None


class SpeechService:
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        raise NotImplementedError
