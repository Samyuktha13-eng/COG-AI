from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class SessionEvent(CognivBaseModel):
    session_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    beat_id: str | None = None
    event_type: str = ""
    question: str | None = None
    transcript: str | None = None
    audio_path: str | None = None
    sequence: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    spoken: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)
