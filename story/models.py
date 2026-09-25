from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SceneAsset:
    filename: str = ""
    url: str = ""
    kind: str = "image"


@dataclass
class Question:
    prompt: str = ""
    options: list[str] = field(default_factory=list)
    answer: str | None = None


@dataclass
class AnswerOutcome:
    correct: bool = False
    message: str = ""


@dataclass
class StoryScene:
    id: str = ""
    chapter_id: str = ""
    story_id: str = ""
    story_reference: str = ""
    sequence: int = 0
    location: str = ""
    objects: list[str] = field(default_factory=list)
    memory_cues: list[str] = field(default_factory=list)
    story_section: str = ""
    narrative_summary: str = ""
    image_asset: SceneAsset | None = None
    question: Question | None = None
    outcome: AnswerOutcome | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
