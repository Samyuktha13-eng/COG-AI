"""Response generation from intents and tool outcomes."""

from __future__ import annotations

from typing import Any


def generate_response(intent: dict[str, Any], tool_result: dict[str, Any] | None = None) -> str:
    kind = intent.get("intent")
    if kind == "create_reminder":
        if tool_result and tool_result.get("status") == "success":
            reminder = tool_result["reminder"]
            when = f" at {reminder['time']}" if reminder.get("time") else ""
            return f"Okay. I will remind you to {reminder['task']}{when}."
        return "I couldn't create that reminder yet."
    if kind == "query_memory":
        return "I don't have that memory available yet."
    if kind == "start_game":
        return "The memory game is not connected yet."
    if kind == "general_conversation":
        message = intent.get("message", "")
        if "good morning" in message.lower():
            return "Good morning. How are you feeling today?"
        if "thank" in message.lower():
            return "You are welcome."
        return "Hello. How can I help you today?"
    if intent.get("error"):
        return "I had trouble understanding that. Please try again."
    return "I am not sure I understood. Please try again."
