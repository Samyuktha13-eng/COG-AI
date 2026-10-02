from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from ._common import CognivBaseModel


class VideoJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoJob(CognivBaseModel):
    job_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    scene_id: str | None = None
    status: VideoJobStatus = VideoJobStatus.QUEUED
    output_url: str | None = None
    output_path: str | None = None
    provider_job_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _coerce_datetime(cls, value):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
