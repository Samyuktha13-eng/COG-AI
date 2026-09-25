from __future__ import annotations

from enum import Enum

from pydantic import Field

from ._common import CognivBaseModel


class VideoJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
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
    created_at: str | None = None
    updated_at: str | None = None
