from __future__ import annotations

from enum import Enum

from pydantic import Field

from ._common import CognivBaseModel


class SessionStatus(str, Enum):
    IDLE = "idle"
    PLAYING = "playing"
    WAITING_FOR_SPEECH = "waiting_for_speech"
    COMPLETED = "completed"


class GameSession(CognivBaseModel):
    session_id: str
    patient_id: str
    story_id: str
    narration_language: str = "en"
    current_beat_id: str | None = None
    current_beat_sequence: int = 0
    status: SessionStatus = SessionStatus.IDLE
    completed_beat_ids: list[str] = Field(default_factory=list)
    current_question: str | None = None
    narration_text: str | None = None
    video_status: str = "not_started"
    video_url: str | None = None
    preview_url: str | None = None
    video_error: str | None = None
    video_request_id: str | None = None
    care_reminder_id: str | None = None
    care_reminder: str | None = None
    acknowledged_care_reminder_ids: list[str] = Field(default_factory=list)
    progress: dict[str, object] = Field(default_factory=dict)
    story_progression: dict[str, object] = Field(default_factory=dict)
    caregiver_guidance: list[str] = Field(default_factory=list)
    last_transcript: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    audio_path: str | None = None
    memory_score: float | None = None
