"""Structured intent routing with a replaceable provider boundary."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Intent:
    intent: str
    task: str | None = None
    time: str | None = None
    query: str | None = None
    game: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class IntentProvider(Protocol):
    def classify(self, text: str) -> Intent: ...


class DeterministicIntentProvider:
    """Small offline fallback for tests and environments without an LLM."""

    _reminder = re.compile(r"(?:remind me to|reminder to)\s+(.+?)(?:\s+at\s+(.+))?$", re.I)
    _game = re.compile(
        r"(?:start|play)\s+(?:a\s+)?(?:memory\s+)?game|"
        r"(शुरू करो|खेल शुरू|ప్రారంభించు|ఆట ప్రారంభించు|தொடங்கு|விளையாட்டை தொடங்கு|"
        r"ಪ್ರಾರಂಭಿಸಿ|ಆಟ ಪ್ರಾರಂಭಿಸಿ|ആരംഭിക്കുക|കളി ആരംഭിക്കുക|सुरू करा|खेळ सुरू करा|"
        r"শুরু করুন|খেলা শুরু করুন)", re.I,
    )
    _replay = re.compile(
        r"\b(repeat|replay|say that again)\b|"
        r"(दोबारा|फिर से|మళ్లీ|మళ్ళీ|மீண்டும்|ಮತ್ತೆ|വീണ്ടും|पुन्हा|আবার)", re.I,
    )
    _next = re.compile(
        r"\b(next scene|next memory|continue|move on|skip)\b|"
        r"(अगला दृश्य|आगे बढ़ो|अगली कहानी|తదుపరి దృశ్యం|కొనసాగించు|"
        r"அடுத்த காட்சி|தொடரவும்|ಮುಂದಿನ ದೃಶ್ಯ|ಮುಂದುವರಿಸಿ|അടുത്ത രംഗം|തുടരുക|"
        r"पुढील दृश्य|पुढे जा|পরের দৃশ্য|চালিয়ে যান)", re.I,
    )
    _finish = re.compile(
        r"\b(finish|end|stop|done|that is all)\b|"
        r"(समाप्त|खत्म|रोक दो|ముగించు|ఆపు|முடி|நிறுத்து|ಮುಗಿಸಿ|ನಿಲ್ಲಿಸಿ|"
        r"അവസാനിപ്പിക്കുക|നിർത്തുക|समाप्त करा|थांबा|শেষ করুন|থামুন)", re.I,
    )

    def classify(self, text: str) -> Intent:
        message = " ".join(text.split()).strip()
        if not message:
            return Intent("unknown", message="")
        reminder = self._reminder.search(message)
        if reminder:
            task = reminder.group(1).strip().rstrip(".,!?;:")
            reminder_time = reminder.group(2)
            if reminder_time:
                reminder_time = reminder_time.strip().rstrip(".,!?;:")
            return Intent("create_reminder", task=task, time=reminder_time)
        if self._game.search(message):
            return Intent("start_game", game="memory")
        if self._replay.search(message):
            return Intent("replay_scene")
        if self._next.search(message):
            return Intent("next_scene")
        if self._finish.search(message):
            return Intent("finish_session")
        if re.search(r"\b(who|what|when|where|remember|daughter|son|family)\b|"
                 r"(कौन|क्या|कब|कहाँ|याद|परिवार|ఎవరు|ఏమిటి|ఎప్పుడు|ఎక్కడ|గుర్తు|"
                 r"யார்|என்ன|எப்போது|எங்கே|நினைவு|ಯಾರು|ಏನು|ಯಾವಾಗ|ಎಲ್ಲಿ|ನೆನಪು|"
                 r"ആര്|എന്ത്|എപ്പോൾ|എവിടെ|ഓർമ്മ|कोण|काय|कधी|कुठे|आठवण|"
                 r"কে|কি|কখন|কোথায়|মনে)", message, re.I):
            return Intent("query_memory", query=message)
        if re.search(r"\b(hello|hi|good morning|good evening|how are you|thank you)\b", message, re.I):
            return Intent("general_conversation", message=message)
        return Intent("unknown", message=message)


class IntentRouter:
    def __init__(self, provider: IntentProvider | None = None) -> None:
        self.provider = provider or DeterministicIntentProvider()

    def route(self, text: str) -> dict[str, Any]:
        try:
            result = self.provider.classify(text)
        except Exception as exc:
            return {"intent": "unknown", "error": f"Intent classification failed: {exc}"}
        if result.intent not in {"create_reminder", "query_memory", "start_game", "replay_scene", "next_scene", "finish_session", "general_conversation", "unknown"}:
            return {"intent": "unknown", "error": "Intent provider returned an unsupported intent."}
        return result.to_dict()
