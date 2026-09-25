from __future__ import annotations


class ReminderStore:
    def __init__(self):
        self._items: list[dict[str, object]] = []

    def create_reminder(self, task: str, due_time: str | None = None) -> dict[str, object]:
        item = {"task": task, "time": due_time or "09:00", "status": "created"}
        self._items.append(item)
        return item

    def list_reminders(self) -> list[dict[str, object]]:
        return list(self._items)
