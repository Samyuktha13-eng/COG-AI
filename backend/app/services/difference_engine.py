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
from .story_translation import translate_to_english

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
            image_description = ""
            if scene.image_asset is not None:
                image_description = getattr(scene.image_asset, "description", "")
            if not image_description:
                image_description = getattr(scene, "narrative_summary", "") or getattr(scene, "location", "") or ""
            index.setdefault(beat.id, []).extend(
                [
                    scene.story_section.lower(),
                    scene.narrative_summary.lower(),
                    image_description.lower(),
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


def original_story_fact(beat_id: str | None) -> str:
    """Return the canonical action for a beat, or an empty string if unknown."""
    facts = _fact_index().get(beat_id or "", [])
    return facts[0] if facts else ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_STOPWORDS = {"the", "and", "with", "from", "that", "this", "then", "was",
              "were", "she", "her", "his", "him", "they", "them", "have",
              "had", "has", "did", "does", "for", "are", "but", "not",
              "into", "onto", "over", "just", "also", "very", "some", "lakshmi"}

_JASMINE_LOCALIZED_TERMS = {
    "te": {
        "jasmine_01": ("తలుపు",),
        "jasmine_02": ("నీళ్లు", "నీళ్ళు", "నీళ్ల", "నీళ్ళ", "నీరు", "నీరును", "నీల్ని"),
        "jasmine_03": ("మల్లెచెట్టు", "మల్లె చెట్టు", "మల్లెమొక్క", "మల్లె మొక్క", "మల్లె"),
        "jasmine_04": ("మల్లెపూ", "మల్లె పూ", "మల్లెపువ్వు", "మల్లె"),
        "jasmine_05": ("పూలదండ", "పువ్వులదండ", "దండ", "మాల", "పువ్వులల్ల", "పువ్వులళ్ల"),
        "jasmine_06": ("దారం", "దారాన్ని", "నూలు", "నూలును"),
        "jasmine_07": ("పూవు", "పువ్వు", "మల్లెపూ"),
        "jasmine_08": ("మల్లెపూల", "పూలదండ", "దండ", "మాల"),
    },
    "hi": {
        "jasmine_01": ("दरवाज़ा", "दरवाजा"),
        "jasmine_02": ("पानी", "जल"),
        "jasmine_03": ("चमेली", "फूलों का पौधा"),
        "jasmine_04": ("चमेली",),
        "jasmine_05": ("फूलों की माला", "माला"),
        "jasmine_06": ("धागा",),
        "jasmine_07": ("फूल", "कलियाँ"),
        "jasmine_08": ("माला",),
    },
    "ta": {
        "jasmine_01": ("கதவு",),
        "jasmine_02": ("தண்ணீர்", "நீர்"),
        "jasmine_03": ("மல்லிகை", "செடி"),
        "jasmine_04": ("மல்லிகை",),
        "jasmine_05": ("பூமாலை", "மாலை"),
        "jasmine_06": ("நூல்", "நூலை"),
        "jasmine_07": ("பூ", "மலர்"),
        "jasmine_08": ("பூமாலை", "மாலை"),
    },
    "kn": {
        "jasmine_01": ("ಬಾಗಿಲು",),
        "jasmine_02": ("ನೀರು",),
        "jasmine_03": ("ಮಲ್ಲಿಗೆ", "ಗಿಡ"),
        "jasmine_04": ("ಮಲ್ಲಿಗೆ",),
        "jasmine_05": ("ಹೂವಿನ ಹಾರ", "ಹಾರ"),
        "jasmine_06": ("ದಾರ",),
        "jasmine_07": ("ಹೂವು", "ಹೂ"),
        "jasmine_08": ("ಹೂವಿನ ಹಾರ", "ಹಾರ"),
    },
}


def _localized_story_fact(beat_id: str | None, text: str, language: str) -> str | None:
    normalized = " ".join(text.lower().split())
    for term in _JASMINE_LOCALIZED_TERMS.get(language, {}).get(beat_id or "", ()):
        if term in normalized:
            return f"{beat_id}: {term}"
    return None


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

        language = (getattr(event, "transcript_language", None) or "en").lower().split("-")[0]
        translated_transcript = translate_to_english(event.transcript, language) if language != "en" else None
        analysis_text = translated_transcript or event.transcript
        analysis_language = "en" if translated_transcript else language
        transcript_tokens = _tokens(analysis_text)
        if not transcript_tokens and analysis_language not in _JASMINE_LOCALIZED_TERMS:
            continue

        beat_facts = index.get(event.beat_id, [])

        # Check each sentence fragment of the transcript
        sentences = re.split(r"[.!?,;]+", analysis_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            localized_fact = (
                _localized_story_fact(event.beat_id, sentence, language)
                if not translated_transcript else None
            )
            if localized_fact:
                supported.append(EvidenceItem(
                    transcript_fragment=sentence,
                    matched_story_fact=localized_fact,
                    beat_id=event.beat_id,
                    question=event.question,
                    timestamp=event.started_at,
                ))
                continue
            s_tokens = _tokens(sentence)
            if not s_tokens:
                if analysis_language in _JASMINE_LOCALIZED_TERMS:
                    unsupported.append(UnsupportedItem(
                        transcript_fragment=sentence,
                        reason="not found in available patient evidence",
                        beat_id=event.beat_id,
                        question=event.question,
                        timestamp=event.started_at,
                    ))
                continue

            # Find the best-matching fact
            best_fact = ""
            best_overlap = 0
            for fact in beat_facts:
                overlap = len(_overlap(s_tokens, fact))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_fact = fact

            single_anchor_match = (
                translated_transcript is not None
                and len(s_tokens) == 1
                and best_overlap == 1
            )
            if best_overlap >= 2 or single_anchor_match:
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
