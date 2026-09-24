"""
Difference Engine
=================
Compares patient speech transcripts against canonical story evidence.

Rules
-----
* Never says the patient is "wrong".
* Absence from stored material → "not found in available patient evidence".
* Raw transcript is never modified; only normalised copies are used for matching.
* Matching is deterministic keyword/phrase overlap — no LLM.
"""
from __future__ import annotations

import re

from ..data.stories import get_all_stories
from ..models.session_event import SessionEvent
from ..models.session_report import EvidenceItem, UnsupportedItem
from story.scene_loader import load_scenes

# ---------------------------------------------------------------------------
# Build a fact index from the canonical story registry
# beat_id → list of evidence phrases drawn from story, narration, and image metadata
# ---------------------------------------------------------------------------
def _build_fact_index() -> dict[str, list[str]]:
    from ..data.narrations import NARRATIONS
    index: dict[str, list[str]] = {}
    for story in get_all_stories():
        for beat in story.beats:
            facts: list[str] = []
            facts.append(beat.action.lower())
            facts.append(beat.motion.lower())
            for step in beat.motion_sequence:
                facts.append(step.lower())
            narration = NARRATIONS.get(beat.id, {})
            if narration.get("opening"):
                facts.append(narration["opening"].lower())
            index[beat.id] = facts

    scene_by_image = {
        scene.image_asset.filename: scene
        for scene in load_scenes()
        if scene.image_asset
    }
    for story in get_all_stories():
        for beat in story.beats:
            scene = scene_by_image.get(beat.image_path)
            if scene is None:
                continue
            index.setdefault(beat.id, []).extend(
                [
                    scene.story_section.lower(),
                    scene.narrative_summary.lower(),
                    scene.image_asset.description.lower(),
                    *[cue.lower() for cue in scene.memory_cues],
                    *[obj.lower() for obj in scene.objects],
                ]
            )
    return index


_FACT_INDEX: dict[str, list[str]] | None = None


def _fact_index() -> dict[str, list[str]]:
    global _FACT_INDEX
    if _FACT_INDEX is None:
        _FACT_INDEX = _build_fact_index()
    return _FACT_INDEX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_STOPWORDS = {"the", "and", "with", "from", "that", "this", "then", "was",
              "were", "she", "her", "his", "him", "they", "them", "have",
              "had", "has", "did", "does", "for", "are", "but", "not",
              "into", "onto", "over", "just", "also", "very", "some"}


def _tokens(text: str) -> list[str]:
    words = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _overlap(a_tokens: list[str], b_text: str) -> list[str]:
    """Return tokens from a that appear in b_text."""
    b = b_text.lower()
    return [t for t in a_tokens if t in b]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyse_events(events: list[SessionEvent]) -> tuple[list[EvidenceItem], list[UnsupportedItem]]:
    """
    For each spoken event, split the transcript into meaningful fragments and
    check each against the canonical story facts for that beat.

    Returns (supported, unsupported) lists.
    """
    supported: list[EvidenceItem] = []
    unsupported: list[UnsupportedItem] = []
    index = _fact_index()

    for event in events:
        if not event.spoken or not event.transcript:
            continue

        transcript_tokens = _tokens(event.transcript)
        if not transcript_tokens:
            continue

        beat_facts = index.get(event.beat_id, [])

        # Check each sentence fragment of the transcript
        sentences = re.split(r"[.!?,;]+", event.transcript)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            s_tokens = _tokens(sentence)
            if not s_tokens:
                continue

            # Find the best-matching fact
            best_fact = ""
            best_overlap = 0
            for fact in beat_facts:
                overlap = len(_overlap(s_tokens, fact))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_fact = fact

            if best_overlap >= 2:
                supported.append(EvidenceItem(
                    transcript_fragment=sentence,
                    matched_story_fact=best_fact,
                    beat_id=event.beat_id,
                    question=event.question,
                    timestamp=event.started_at,
                ))
            else:
                unsupported.append(UnsupportedItem(
                    transcript_fragment=sentence,
                    reason="not found in available patient evidence",
                    beat_id=event.beat_id,
                    question=event.question,
                    timestamp=event.started_at,
                ))

    return supported, unsupported
