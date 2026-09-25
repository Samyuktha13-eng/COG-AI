from __future__ import annotations

from enum import Enum

from pydantic import Field

from ._common import CognivBaseModel


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationJob(CognivBaseModel):
    job_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    beat_id: str | None = None
    prompt: str = ""
    status: GenerationStatus = GenerationStatus.QUEUED
    output_url: str | None = None
    output_path: str | None = None
    error: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
