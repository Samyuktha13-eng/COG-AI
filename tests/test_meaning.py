from voice.meaning import MeaningLayer, understand


def assert_hydration(text, language="en"):
    result = understand(text, language)
    assert result["intent"] == "create_reminder"
    assert result["entities"]["task"] == "drink water"
    assert result["entities"]["time"] == "10:30"
    assert result["entities"]["reminder_type"] == "hydration"
    assert result["needs_clarification"] is False
    assert result["confidence"] >= 0.8


def test_english_reminder_variants():
    assert_hydration("Remind me to drink water at 10:30.")
    assert_hydration("Please remind me about drinking water at ten thirty.")
    assert_hydration("At half past ten remind me to have some water.")
    assert_hydration("Now must the police team remind me to bring water at 10.30.")


def test_medication_and_relative_date():
    medicine = understand("Remind me to take my medicine at 8 pm.", "en")
    assert medicine["entities"]["task"] == "take medicine"
    assert medicine["entities"]["time"] == "20:00"
    assert medicine["entities"]["reminder_type"] == "medication"
    tomorrow = understand("Remind me to call my daughter tomorrow.", "en")
    assert tomorrow["entities"]["task"] == "call my daughter"
    assert tomorrow["entities"]["date"] == "tomorrow"
    assert tomorrow["needs_clarification"] is True


def test_follow_up_context_preserves_task():
    first = understand("Remind me to drink water.", "en")
    second = understand("At ten thirty", "en", conversation_context={"previous_intent": first})
    assert second["entities"]["time"] == "10:30"


def test_meaning_provider_is_replaceable():
    class Provider:
        def understand(self, transcript, language, conversation_context=None, patient_context=None):
            return {
                "intent": "general_conversation", "language": language,
                "entities": {key: None for key in ("task", "time", "date", "reminder_type", "recurrence", "person", "memory_id", "game")},
                "confidence": 0.9, "needs_clarification": False, "clarification_question": None,
            }
    assert MeaningLayer(Provider()).understand("hello", "en")["intent"] == "general_conversation"
