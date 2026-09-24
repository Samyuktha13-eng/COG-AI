import pytest

from voice.meaning import understand
from voice.semantic_validation import is_valid_semantic_result, validate_semantic_result


def test_valid_create_reminder_schema():
    result = understand("Remind me to drink water at 10:30.", "en")
    assert is_valid_semantic_result(result)
    assert result["entities"]["time"] == "10:30"


def test_missing_time_requires_clarification():
    result = understand("Remind me to drink water.", "en")
    assert result["needs_clarification"] is True
    assert result["clarification_question"] == "What time should I remind you?"


def test_invalid_time_is_rejected():
    result = understand("Remind me to drink water at 10:30.", "en")
    result["entities"]["time"] = "tomorrow"
    with pytest.raises(ValueError, match="HH:MM"):
        validate_semantic_result(result)


def test_unsupported_intent_is_rejected():
    result = understand("Hello", "en")
    result["intent"] = "delete_everything"
    assert not is_valid_semantic_result(result)
