from datetime import datetime

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.care_plan import CarePlan, CarePlanReminder
from backend.app.services.reminder_scheduler import CarePlanReminderScheduler

client = TestClient(app)


def test_due_reminder_matches_current_time():
    care_plan = CarePlan(
        patient_id="lakshmi_001",
        reminders=[
            CarePlanReminder(
                reminder_id="r1",
                patient_id="lakshmi_001",
                task="Take medicine",
                reminder_type="medication",
                time="09:15",
            ),
            CarePlanReminder(
                reminder_id="r2",
                patient_id="lakshmi_001",
                task="Drink water",
                reminder_type="hydration",
                time="10:00",
            ),
        ],
    )

    due = CarePlanReminderScheduler(care_plan).due_at(datetime(2026, 9, 20, 9, 15))

    assert [item.reminder_id for item in due] == ["r1"]
    assert due[0].task == "Take medicine"


def test_disabled_reminder_is_not_due():
    care_plan = CarePlan(
        patient_id="lakshmi_001",
        reminders=[
            CarePlanReminder(
                reminder_id="r3",
                patient_id="lakshmi_001",
                task="Watch memory story",
                reminder_type="routine",
                time="08:00",
                enabled=False,
            )
        ],
    )

    due = CarePlanReminderScheduler(care_plan).due_at(datetime(2026, 9, 20, 8, 0))

    assert due == []


def test_scheduler_supports_trigger_window_for_time_based_reminders():
    care_plan = CarePlan(
        patient_id="lakshmi_001",
        reminders=[
            CarePlanReminder(
                reminder_id="r4",
                patient_id="lakshmi_001",
                task="Morning memory cue",
                reminder_type="routine",
                time="08:00",
            ),
            CarePlanReminder(
                reminder_id="r5",
                patient_id="lakshmi_001",
                task="Evening memory cue",
                reminder_type="routine",
                time="18:00",
            ),
        ],
    )

    scheduler = CarePlanReminderScheduler(care_plan)
    triggered = scheduler.trigger_due(datetime(2026, 9, 20, 8, 4), window_minutes=5)

    assert [item.reminder_id for item in triggered] == ["r4"]
    assert scheduler.next_due(datetime(2026, 9, 20, 8, 4)).reminder_id == "r4"


def test_due_endpoint_uses_window_for_realistic_care_prompts():
    response = client.get(
        "/api/patients/lakshmi_001/care-plan/reminders/due",
        params={"now": "2026-09-20T09:00:00+00:00", "window_minutes": 60},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert any(item["reminder_id"] == "rem_morning_water" for item in payload["due_reminders"])
