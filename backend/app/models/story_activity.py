from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class StoryDerivedActivity(CognivBaseModel):
    activity_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    beat_id: str | None = None
    title: str = ""
    description: str = ""
    category: str = "memory"
    metadata: dict[str, object] = Field(default_factory=dict)
