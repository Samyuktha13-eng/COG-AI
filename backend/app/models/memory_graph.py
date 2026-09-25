from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class MemoryNode(CognivBaseModel):
    beat_id: str = ""
    story_id: str = ""
    patient_id: str = ""
    grounding_source: str = ""
    reference_images: list[str] = Field(default_factory=list)
    created_at: str | None = None


class MemoryGraph(CognivBaseModel):
    patient_id: str = ""
    story_id: str = ""
    nodes: list[MemoryNode] = Field(default_factory=list)
    summary: str = ""
