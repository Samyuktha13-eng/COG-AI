from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class SpeechTranscript(CognivBaseModel):
    transcript_id: str = ""
    patient_id: str = ""
    session_id: str | None = None
    story_id: str | None = None
    beat_id: str | None = None
    text: str = ""
    confidence: float = 0.0
    language: str = "en"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str | None = None
