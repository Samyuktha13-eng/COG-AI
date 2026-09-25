from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class CarePlanReminder(CognivBaseModel):
    reminder_id: str = ""
    patient_id: str = ""
    task: str = ""
    reminder_type: str = "routine"
    time: str = "09:00"
    created_at: str | None = None


class CarePlan(CognivBaseModel):
    patient_id: str = ""
    reminders: list[CarePlanReminder] = Field(default_factory=list)
    notes: str = ""
    created_at: str | None = None
