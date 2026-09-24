"""
Recognition Service
===================
Evaluates a patient's spoken transcript against the expected concepts for a
story beat.  Returns correct / partial / wrong without exact string matching.

Rules
-----
* correct  — transcript contains at least one acceptable answer phrase
* partial  — transcript contains a word from an expected concept (≥3 chars)
* wrong    — no concept overlap found
"""
from __future__ import annotations

import re

from ..data.narrations import NARRATIONS


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def _concept_words(concept: str) -> list[str]:
    return [w for w in _normalize(concept).split() if len(w) >= 3]


class RecognitionService:
    def evaluate(
        self,
        beat_id: str,
        transcript: str,
        acceptable_answers: list[str] | None = None,
        expected_concepts: list[str] | None = None,
    ) -> dict:
        """
        Returns:
          {
            "outcome": "correct" | "partial" | "wrong",
            "transcript": str,
            "feedback": str,
            "hint": str | None,
          }
        """
        narration = NARRATIONS.get(beat_id, {})
        answers   = acceptable_answers or narration.get("acceptable_answers", [])
        concepts  = expected_concepts  or narration.get("expected_concepts", [])

        # Fall back: derive concepts from the question itself
        if not concepts:
            question = narration.get("question", "")
            # last noun-ish word in the question is usually the concept
            words = _normalize(question).split()
            concepts = [words[-1]] if words else []

        norm = _normalize(transcript)

        # 1. Exact acceptable answer match
        if answers and any(_normalize(a) in norm for a in answers):
            return {
                "outcome": "correct",
                "transcript": transcript,
                "feedback": narration.get("success_response", "Yes, that's right!"),
                "hint": None,
            }

        # 2. Concept word overlap
        if concepts and any(w in norm for c in concepts for w in _concept_words(c)):
            return {
                "outcome": "partial",
                "transcript": transcript,
                "feedback": narration.get("hint", "You're on the right track. Look again."),
                "hint": narration.get("hint"),
            }

        return {
            "outcome": "wrong",
            "transcript": transcript,
            "feedback": narration.get("retry_response", "Let's watch that moment again."),
            "hint": None,
        }
