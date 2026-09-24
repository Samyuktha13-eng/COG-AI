from tools.router import ToolRouter, route_semantic_intent


ENTITY_KEYS = ("task", "time", "date", "reminder_type", "recurrence", "person", "memory_id", "game")


def semantic(intent, **entities):
    return {
        "intent": intent,
        "language": "te",
        "entities": {key: entities.get(key) for key in ENTITY_KEYS},
        "confidence": 0.92,
        "needs_clarification": False,
        "clarification_question": None,
    }


def test_create_reminder_route_preserves_payload():
    result = route_semantic_intent(semantic("create_reminder", task="drink water", time="10:30", reminder_type="hydration"))
    assert result["route"] == "reminder"
    assert result["action"] == "create"
    assert result["payload"]["task"] == "drink water"
    assert result["payload"]["time"] == "10:30"


def test_memory_routes():
    assert route_semantic_intent(semantic("query_memory"))["route"] == "memory"
    assert route_semantic_intent(semantic("query_memory"))["action"] == "query"
    assert route_semantic_intent(semantic("save_memory"))["action"] == "save"


def test_game_routes():
    assert route_semantic_intent(semantic("start_game", game="memory")) == {"route": "game", "action": "start", "payload": {"game": "memory"}}
    assert route_semantic_intent(semantic("answer_game", game="memory"))["action"] == "answer"


def test_clarification_routes_without_execution():
    value = semantic("create_reminder", task="drink water")
    value["needs_clarification"] = True
    value["clarification_question"] = "What time should I remind you?"
    result = ToolRouter().route(value)
    assert result == {"route": "clarification", "action": "ask", "payload": {"question": "What time should I remind you?"}}


def test_unknown_and_invalid_are_safe():
    unknown = route_semantic_intent(semantic("unknown"))
    assert unknown["route"] == "unknown"
    invalid = semantic("create_reminder", task="drink water", time="not-a-time")
    result = route_semantic_intent(invalid)
    assert result["route"] == "unknown"
    assert result["action"] == "reject"
    assert "error" in result
