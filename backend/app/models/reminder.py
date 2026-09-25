from __future__ import annotations

from pydantic import Field

from ._common import CognivBaseModel


class BeatReminder(CognivBaseModel):
    reminder_id: str = ""
    patient_id: str = ""
    story_id: str = ""
    beat_id: str | None = None
    task: str = ""
    reminder_type: str = "routine"
    time: str | None = None
    created_at: str | None = None
    acked: bool = False


class ReminderQuestion(CognivBaseModel):
    question_id: str = ""
    reminder_id: str = ""
    patient_id: str = ""
    text: str = ""
    choices: list[str] = Field(default_factory=list)
