from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class StoryBeat(CognivBaseModel):
    id: str
    story_id: str
    sequence: int = 0
    image_path: str = ""
    action: str = ""
    motion: str = ""
    camera: str = "static"
    motion_sequence: list[str] = Field(default_factory=list)
    motion_constraints: list[str] = Field(default_factory=list)
    narration: str = ""
    narration_by_language: dict[str, str] = Field(default_factory=dict)
    prompt: str | None = None
    theme: str | None = None
