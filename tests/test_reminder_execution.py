from tools.reminders import ReminderStore
from tools.router import ToolRouter


KEYS = ("task", "time", "date", "reminder_type", "recurrence", "person", "memory_id", "game")


def semantic(intent, **values):
    return {
        "intent": intent, "language": "en",
        "entities": {key: values.get(key) for key in KEYS},
        "confidence": 0.92, "needs_clarification": False, "clarification_question": None,
    }


def test_create_hydration_reminder():
    result = ToolRouter(ReminderStore()).execute(semantic("create_reminder", task="drink water", time="10:30", reminder_type="hydration"))
    assert result["tool_result"]["success"] is True
    assert result["tool_result"]["reminder_id"].startswith("rem_")
    assert result["tool_result"]["reminder_type"] == "hydration"


def test_multilingual_canonical_payloads_create_same_operation():
    router = ToolRouter(ReminderStore())
    for language in ("en", "hi", "te", "ta"):
        value = semantic("create_reminder", task="drink water", time="10:30", reminder_type="hydration")
        value["language"] = language
        assert router.execute(value)["tool_result"]["success"] is True


def test_medication_daily_and_appointment_payloads():
    store = ReminderStore()
    router = ToolRouter(store)
    for values in (
        {"task": "take medicine", "time": "20:00", "reminder_type": "medication"},
        {"task": "walk", "time": "08:00", "recurrence": "daily", "reminder_type": "activity"},
        {"task": "doctor appointment", "time": "14:00", "date": "tomorrow", "reminder_type": "appointment"},
    ):
        assert router.execute(semantic("create_reminder", **values))["tool_result"]["success"] is True


def test_query_cancel_complete():
    store = ReminderStore()
    router = ToolRouter(store)
    created = router.execute(semantic("create_reminder", task="drink water", time="10:30"))["tool_result"]
    reminder_id = created["reminder_id"]
    query = router.execute(semantic("query_reminder", memory_id=reminder_id))
    assert query["tool_result"]["reminders"][0]["id"] == reminder_id
    completed = router.execute(semantic("complete_reminder", memory_id=reminder_id))
    assert completed["tool_result"]["success"] is True
    cancelled = router.execute(semantic("cancel_reminder", memory_id=reminder_id))
    assert cancelled["tool_result"]["reminder"]["status"] == "cancelled"


def test_clarification_does_not_execute_tool():
    class FailingTool:
        def create_reminder(self, *args):
            raise AssertionError("tool executed")
    value = semantic("create_reminder", task="drink water")
    value["needs_clarification"] = True
    value["clarification_question"] = "What time should I remind you?"
    assert ToolRouter(FailingTool()).execute(value)["route"] == "clarification"


def test_failed_creation_is_propagated():
    class FailedTool:
        def create_reminder(self, *args):
            return {"success": False, "error": "reminder_creation_failed"}
    result = ToolRouter(FailedTool()).execute(semantic("create_reminder", task="drink water", time="10:30"))
    assert result["tool_result"] == {"success": False, "error": "reminder_creation_failed"}


def test_invalid_semantic_input_does_not_execute_tool():
    store = ReminderStore()
    value = semantic("create_reminder", task="drink water", time="invalid")
    result = ToolRouter(store).execute(value)
    assert result["route"] == "unknown"
    assert store.get_reminders() == []
