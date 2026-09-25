from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel
from .beat import StoryBeat


class Story(CognivBaseModel):
    id: str
    title: str
    prompt: str = ""
    description: str = ""
    beats: list[StoryBeat] = Field(default_factory=list)
    chapters: list[str] = Field(default_factory=list)
