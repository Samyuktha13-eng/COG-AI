from __future__ import annotations

from datetime import datetime, timedelta

from ..models.care_plan import CarePlan, CarePlanReminder


class CarePlanReminderScheduler:
    """Return care-plan reminders whose configured time matches the current clock."""

    def __init__(self, care_plan: CarePlan):
        self.care_plan = care_plan

    def due_at(self, now: datetime) -> list[CarePlanReminder]:
        current_time = now.strftime("%H:%M")
        due: list[CarePlanReminder] = []
        for reminder in self.care_plan.reminders:
            if not reminder.enabled:
                continue
            if not reminder.time:
                continue
            if reminder.time.strip() == current_time:
                due.append(reminder)
        return due

    def trigger_due(self, now: datetime, window_minutes: int = 0) -> list[CarePlanReminder]:
        """Return reminders due within a tolerance window around the configured time."""
        if window_minutes <= 0:
            window_minutes = 15

        due: list[CarePlanReminder] = []
        for reminder in self.care_plan.reminders:
            if not reminder.enabled or not reminder.time:
                continue
            try:
                reminder_time = datetime.strptime(reminder.time.strip(), "%H:%M")
            except ValueError:
                continue
            reminder_dt = now.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
            delta_seconds = abs((now - reminder_dt).total_seconds())
            if delta_seconds <= window_minutes * 60:
                due.append(reminder)
        return due

    def next_due(self, now: datetime) -> CarePlanReminder | None:
        upcoming: list[tuple[datetime, CarePlanReminder]] = []
        for reminder in self.care_plan.reminders:
            if not reminder.enabled or not reminder.time:
                continue
            try:
                reminder_time = datetime.strptime(reminder.time.strip(), "%H:%M")
            except ValueError:
                continue
            candidate = now.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
            if candidate < now and now - candidate > timedelta(minutes=15):
                candidate += timedelta(days=1)
            upcoming.append((candidate, reminder))
        if not upcoming:
            return None
        upcoming.sort(key=lambda item: item[0])
        return upcoming[0][1]

    def upcoming_within(self, now: datetime, lead_minutes: int = 15) -> list[CarePlanReminder]:
        """Return enabled reminders whose next occurrence is within the lead window."""
        upcoming: list[tuple[datetime, CarePlanReminder]] = []
        for reminder in self.care_plan.reminders:
            if not reminder.enabled or not reminder.time:
                continue
            try:
                reminder_time = datetime.strptime(reminder.time.strip(), "%H:%M")
            except ValueError:
                continue
            candidate = now.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
            if candidate < now:
                candidate += timedelta(days=1)
            if timedelta(0) <= candidate - now <= timedelta(minutes=lead_minutes):
                upcoming.append((candidate, reminder))
        upcoming.sort(key=lambda item: item[0])
        return [item[1] for item in upcoming]
