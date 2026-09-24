"""Validation for canonical Cogniv semantic intents."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

class SemanticIntent(str, Enum):
    CREATE_REMINDER = "create_reminder"
    CANCEL_REMINDER = "cancel_reminder"
    QUERY_REMINDER = "query_reminder"
    COMPLETE_REMINDER = "complete_reminder"
    QUERY_MEMORY = "query_memory"
    SAVE_MEMORY = "save_memory"
    START_GAME = "start_game"
    ANSWER_GAME = "answer_game"
    GENERAL_CONVERSATION = "general_conversation"
    UNKNOWN = "unknown"


SUPPORTED_INTENTS = {
    "create_reminder", "cancel_reminder", "query_reminder", "complete_reminder",
    "query_memory", "save_memory", "start_game", "answer_game", "general_conversation", "unknown",
}
SUPPORTED_LANGUAGES = {
    "en", "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok", "mai", "ml", "mni",
    "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta", "te", "ur",
}
ENTITY_KEYS = ("task", "time", "date", "reminder_type", "recurrence", "person", "memory_id", "game")
_TIME = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


def validate_semantic_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Semantic result must be an object.")
    intent = result.get("intent")
    language = result.get("language")
    if isinstance(intent, SemanticIntent):
        intent = intent.value
    if intent not in SUPPORTED_INTENTS:
        raise ValueError(f"Unsupported semantic intent: {intent}")
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported semantic language: {language}")
    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("Semantic confidence must be between 0 and 1.")
    entities = result.get("entities")
    if not isinstance(entities, dict) or set(entities) != set(ENTITY_KEYS):
        raise ValueError("Semantic entities must contain exactly the canonical entity keys.")
    if entities["time"] is not None and not _TIME.fullmatch(str(entities["time"])):
        raise ValueError("Reminder time must use HH:MM format.")
    needs = result.get("needs_clarification")
    question = result.get("clarification_question")
    if not isinstance(needs, bool):
        raise ValueError("needs_clarification must be boolean.")
    if needs and (not isinstance(question, str) or not question.strip()):
        raise ValueError("Clarification requires a question.")
    if not needs and question is not None:
        raise ValueError("clarification_question must be null when clarification is not needed.")
    if intent == "create_reminder" and not entities["task"]:
        raise ValueError("create_reminder requires a task.")
    if intent == "create_reminder" and entities["time"] is None and not needs:
        raise ValueError("create_reminder without time requires clarification.")
    return result


def is_valid_semantic_result(result: dict[str, Any]) -> bool:
    try:
        validate_semantic_result(result)
    except ValueError:
        return False
    return True
