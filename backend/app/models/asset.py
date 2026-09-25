from __future__ import annotations

from enum import Enum

from ._common import CognivBaseModel


class AssetType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    VIDEO = "video"


class PatientAsset(CognivBaseModel):
    asset_id: str = ""
    patient_id: str = ""
    type: AssetType = AssetType.IMAGE
    original_filename: str = ""
    path: str = ""
    story_reference: str | None = None
    created_at: str | None = None

    @classmethod
    def now(cls, **kwargs):
        from ._common import utc_now

        payload = dict(kwargs)
        payload.setdefault("created_at", utc_now().isoformat())
        return cls(**payload)
