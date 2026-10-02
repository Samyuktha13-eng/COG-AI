from __future__ import annotations

from datetime import datetime

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


class StoryComparison(CognivBaseModel):
    story_id: str = ""
    beat_id: str = ""
    timestamp: str | None = None
    question: str = ""
    original_story: str = ""
    patient_answer: str = ""
    match_score: int | None = None
    matched_fragments: int = 0
    scored_fragments: int = 0
    difference: str = ""


class StoryScore(CognivBaseModel):
    story_id: str = ""
    score: int | None = None
    score_label: str = ""
    spoken_responses: int = 0
    matched_fragments: int = 0
    scored_fragments: int = 0


class SessionReport(CognivBaseModel):
    session_id: str = ""
    patient_id: str = ""
    patient_name: str = ""
    stories_played: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    total_beats: int = 0
    spoken_responses: int = 0
    skipped_responses: int = 0
    events: list[dict[str, object]] = Field(default_factory=list)
    story_comparisons: list[StoryComparison] = Field(default_factory=list)
    story_scores: list[StoryScore] = Field(default_factory=list)
    supported_content: list[EvidenceItem] = Field(default_factory=list)
    unsupported_content: list[UnsupportedItem] = Field(default_factory=list)
    memory_score: int | None = None
    memory_score_label: str = ""
    report_path: str | None = None
