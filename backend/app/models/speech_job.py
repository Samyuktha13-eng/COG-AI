from __future__ import annotations

from enum import Enum

from pydantic import Field

from ._common import CognivBaseModel


class SpeechJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SpeechJob(CognivBaseModel):
    job_id: str = ""
    patient_id: str = ""
    story_id: str | None = None
    session_id: str | None = None
    status: SpeechJobStatus = SpeechJobStatus.QUEUED
    input_path: str | None = None
    transcript: str | None = None
    error: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
