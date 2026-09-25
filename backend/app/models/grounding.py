from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class CaregiverIntent(CognivBaseModel):
    raw_prompt: str = ""
    topic: str = ""
    life_period: str = ""
    entities: list[str] = Field(default_factory=list)
    story_id: str | None = None


class ScenePlan(CognivBaseModel):
    story_id: str = ""
    beat_id: str | None = None
    grounding_source: str = ""
    reference_images: list[str] = Field(default_factory=list)
    memory_cues: list[str] = Field(default_factory=list)
    notes: str = ""


class GroundingResult(CognivBaseModel):
    match: bool = False
    story_id: str | None = None
    beat_id: str | None = None
    reason: str = ""
    scene_plan: ScenePlan | None = None
    reference_images: list[str] = Field(default_factory=list)
    confidence: float = 0.0
