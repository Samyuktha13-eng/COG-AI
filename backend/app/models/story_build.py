from __future__ import annotations

from enum import Enum

from ._common import CognivBaseModel


class BuildStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StoryBuild(CognivBaseModel):
    build_id: str = ""
    patient_id: str = ""
    status: BuildStatus = BuildStatus.PROCESSING
    documents_found: int = 0
    images_found: int = 0
    voice_found: int = 0
    chapters_found: int = 0
    image_groups_matched: int = 0
    narration_prepared: int = 0
    created_at: str | None = None
    updated_at: str | None = None
