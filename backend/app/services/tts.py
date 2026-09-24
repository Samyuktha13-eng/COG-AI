from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_path: str
    language: str
    duration: float | None = None


class TTSService:
    async def synthesize(
        self,
        text: str,
        language: str,
        speaker_id: str | None = None,
    ) -> TTSResult:
        raise NotImplementedError
