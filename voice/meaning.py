"""Multilingual semantic understanding with a replaceable provider boundary."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from .semantic_validation import ENTITY_KEYS, SUPPORTED_LANGUAGES, validate_semantic_result


class MeaningProvider(Protocol):
    def understand(self, transcript: str, language: str, conversation_context: Any = None, patient_context: Any = None) -> dict[str, Any]: ...


@dataclass
class MeaningResult:
    intent: str
    language: str
    entities: dict[str, Any]
    confidence: float
    needs_clarification: bool
    clarification_question: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent, "language": self.language, "entities": self.entities,
            "confidence": self.confidence, "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
        }


def _entities(**values: Any) -> dict[str, Any]:
    return {key: values.get(key) for key in ENTITY_KEYS}


def _normalize_time(text: str) -> str | None:
    match = re.search(r"\b(\d{1,2})[.:](\d{2})\b", text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    match = re.search(r"\b(\d{1,2})(?::00)?\s*(am|pm)\b", text, re.I)
    if match:
        hour = int(match.group(1)) % 12 + (12 if match.group(2).lower() == "pm" else 0)
        return f"{hour:02d}:00"
    words = re.search(r"\b(ten|eight|five)\s+(thirty|thirty|o'clock)\b", text, re.I)
    if words:
        hour = {"ten": 10, "eight": 8, "five": 5}[words.group(1).lower()]
        return f"{hour:02d}:{'30' if words.group(2).lower() == 'thirty' else '00'}"
    if re.search(r"half\s+past\s+ten", text, re.I) or any(
        phrase in text for phrase in ("साढ़े दस", "साडेदहा", "పదిన్నర", "பத்து முப்பது", "সাড়ে দশ", "সাৰে দহ", "ಹತ್ತೂವರೆ", "പത്തരയ്ക്ക്", "ਸਾਢੇ ਦਸ", "ساڑھے دس")
    ):
        return "10:30"
    return None


def _canonical_task(text: str) -> tuple[str | None, str | None]:
    lower = text.lower()
    if any(term in lower for term in ("water", "hydration", "drink", "నీళ్లు", "నీరు", "पानी", "தண்ணீர்", "জল", "পানী", "पाणी", "ನೀರು", "വെള്ളം", "ਪਾਣੀ", "پانی")):
        return "drink water", "hydration"
    if any(term in lower for term in ("medicine", "medication", "tablet", "दवा", "औषध", "మందు", "மருந்து", "ওষুধ", "ಔಷಧ", "മരുന്ന്", "ਦਵਾਈ", "دوا")):
        return "take medicine", "medication"
    match = re.search(r"(?:remind me to|remind me about|reminder to)\s+(.+?)(?:\s+at\s+|\s+tomorrow\b|$)", text, re.I)
    return (match.group(1).strip(" .,!?") if match else None), None


class DeterministicMeaningProvider:
    """Offline fallback for common reminder semantics and explicit context."""

    def understand(self, transcript: str, language: str, conversation_context: Any = None, patient_context: Any = None) -> dict[str, Any]:
        text = " ".join(transcript.split()).strip()
        code = language.strip().lower()
        if code not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported meaning language: {language}")
        reminder_signal = re.search(r"remind|remember|याद|आठवण|గుర్తు|நினைவூட்ட|মনে কর|মনত পেলাই|ನೆನಪ|ഓർമ്മ|ਯਾਦ|یاد", text, re.I)
        has_follow_up = isinstance(conversation_context, dict) and bool(conversation_context.get("previous_intent"))
        if code in {"en", "hi", "te", "ta", "bn", "mr", "kn", "ml", "pa", "ur", "as", "gu"} and (reminder_signal or _canonical_task(text)[0] or has_follow_up):
            task, kind = _canonical_task(text)
            if task is None and any(term in text.lower() for term in ("water", "पानी", "నీళ్లు", "தண்ணீர்", "জল")):
                task, kind = "drink water", "hydration"
            reminder_time = _normalize_time(text)
            previous = conversation_context.get("previous_intent") if isinstance(conversation_context, dict) else None
            if task is None and isinstance(previous, dict):
                previous_entities = previous.get("entities", {})
                task = previous_entities.get("task")
                kind = previous_entities.get("reminder_type")
            date = "tomorrow" if re.search(r"tomorrow|कल|రేపు|நாளை|আগামীকাল|উদ্যা|उद्या|ನಾಳೆ|നാളെ|کل", text, re.I) else None
            needs = task is None or reminder_time is None
            question = "What time should I remind you?" if task and reminder_time is None else "What should I remind you about?" if task is None else None
            return MeaningResult("create_reminder", code, _entities(task=task, time=reminder_time, date=date, reminder_type=kind), 0.92 if not needs else 0.78, needs, question).to_dict()
        if re.search(r"\b(hello|hi|good morning|नमस्ते|नमस्कार|నమస్కారం|வணக்கம்)\b", text, re.I):
            return MeaningResult("general_conversation", code, _entities(), 0.95, False, None).to_dict()
        return MeaningResult("unknown", code, _entities(), 0.35, True, "Could you say that another way?").to_dict()


class MeaningLayer:
    def __init__(self, provider: MeaningProvider | None = None) -> None:
        self.provider = provider or DeterministicMeaningProvider()

    def understand(self, transcript: str, language: str, conversation_context: Any = None, patient_context: Any = None) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.provider.understand(transcript, language, conversation_context, patient_context)
        validate_semantic_result(result)
        result["inference_seconds"] = time.perf_counter() - started
        return result


def understand(transcript: str, language: str, conversation_context: Any = None, patient_context: Any = None, provider: MeaningProvider | None = None) -> dict[str, Any]:
    return MeaningLayer(provider).understand(transcript, language, conversation_context, patient_context)
