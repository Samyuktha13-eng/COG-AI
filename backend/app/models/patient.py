from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class PatientProfile(CognivBaseModel):
    patient_id: str = ""
    name: str = ""
    story_id: str | None = None
    preferred_language: str = "en"
    notes: dict[str, object] = Field(default_factory=dict)
