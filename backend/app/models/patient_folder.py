from __future__ import annotations

from enum import Enum

from pydantic import Field

from ._common import CognivBaseModel


class FolderAssetType(str, Enum):
    STORY_DOCUMENT = "story_document"
    IMAGE = "image"
    VOICE_STORY = "voice_story"
    VIDEO = "video"


class FolderAsset(CognivBaseModel):
    asset_id: str = ""
    patient_id: str = ""
    type: FolderAssetType = FolderAssetType.STORY_DOCUMENT
    name: str = ""
    path: str = ""
    relative_path: str = ""
    story_reference: str | None = None
    created_at: str | None = None
    url: str | None = None


class PatientFolder(CognivBaseModel):
    patient_id: str = ""
    documents: list[FolderAsset] = Field(default_factory=list)
    image_assets: list[FolderAsset] = Field(default_factory=list)
    voice_story: FolderAsset | None = None
    document_text: dict[str, str] = Field(default_factory=dict)
    story_status: str = "not_started"
    game_status: str = "not_started"
    build_id: str | None = None
    build_summary: dict[str, object] = Field(default_factory=dict)
