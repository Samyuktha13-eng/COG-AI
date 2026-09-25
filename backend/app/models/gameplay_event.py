from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class GameplayEvent(CognivBaseModel):
    event_type: str = ""
    session_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    beat_id: str | None = None
    chapter_id: str | None = None
    question: str | None = None
    transcript: str | None = None
    audio_path: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
