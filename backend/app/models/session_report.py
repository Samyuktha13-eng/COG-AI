from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class EvidenceItem(CognivBaseModel):
    transcript_fragment: str = ""
    matched_story_reference: str = ""
    confidence: float = 0.0
    evidence_type: str = "match"


class UnsupportedItem(CognivBaseModel):
    transcript_fragment: str = ""
    reason: str = ""
    category: str = "unsupported"


class SessionReport(CognivBaseModel):
    session_id: str = ""
    patient_id: str = ""
    patient_name: str = ""
    stories_played: list[str] = Field(default_factory=list)
    started_at: str | None = None
    ended_at: str | None = None
    total_beats: int = 0
    spoken_responses: int = 0
    skipped_responses: int = 0
    events: list[dict[str, object]] = Field(default_factory=list)
    supported_content: list[EvidenceItem] = Field(default_factory=list)
    unsupported_content: list[UnsupportedItem] = Field(default_factory=list)
    memory_score: int = 0
    memory_score_label: str = ""
    report_path: str | None = None
