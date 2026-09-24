from datetime import datetime

from timeline.daily_schedule import DailySchedule
from timeline.reminder_scheduler import ReminderScheduler
from timeline.timeline_engine import TimelineEngine
from tools.reminders import ReminderStore


def test_due_priority_visual_and_resume():
    reminders = ReminderStore()
    medication = reminders.create_reminder("take medicine", time="08:00", reminder_type="medication")["reminder_id"]
    reminders.create_reminder("drink water", time="08:00", reminder_type="hydration")
    engine = TimelineEngine(ReminderScheduler(reminders))
    engine.begin_reminiscence({"current_memory_id": "memory-1", "conversation_depth": 2})
    cue = engine.check(datetime(2026, 9, 13, 8, 1))
    assert cue.reminder_id == medication
    assert cue.visual_asset == "reminders/medicine.jpg"
    assert engine.state.active_reminiscence is False
    assert engine.complete_reminder() == {"current_memory_id": "memory-1", "conversation_depth": 2}
    assert reminders.get_reminders()[0]["status"] == "completed"


def test_daily_schedule_and_future_reminder():
    reminders = ReminderStore()
    reminders.create_reminder("lunch", time="12:00", reminder_type="lunch")
    scheduler = ReminderScheduler(reminders)
    assert DailySchedule.time_of_day(datetime(2026, 9, 13, 11, 0)) == "morning"
    assert scheduler.due(datetime(2026, 9, 13, 11, 59)) is None
