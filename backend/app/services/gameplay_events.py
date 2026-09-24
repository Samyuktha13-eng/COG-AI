from __future__ import annotations

from pathlib import Path

from ..models.gameplay_event import GameplayEvent

GAMEPLAY_EVENTS: dict[str, list[GameplayEvent]] = {}


def record_gameplay_event(
    *,
    session_id: str,
    patient_id: str,
    story_id: str,
    event_type: str,
    beat_id: str | None = None,
    chapter_id: str | None = None,
    question: str | None = None,
    transcript: str | None = None,
    audio_path: str | None = None,
    metadata: dict[str, object] | None = None,
) -> GameplayEvent:
    event = GameplayEvent(
        event_type=event_type,
        session_id=session_id,
        patient_id=patient_id,
        story_id=story_id,
        beat_id=beat_id,
        chapter_id=chapter_id,
        question=question,
        transcript=transcript,
        audio_path=audio_path,
        metadata=metadata or {},
    )
    GAMEPLAY_EVENTS.setdefault(session_id, []).append(event)
    return event


def get_gameplay_events(session_id: str) -> list[GameplayEvent]:
    return GAMEPLAY_EVENTS.get(session_id, [])


def persist_gameplay_events(session_id: str, patient_id: str) -> Path:
    root = Path(__file__).resolve().parents[3] / 'outputs' / 'patient_library' / patient_id / 'sessions' / session_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'gameplay_events.json'
    events = [event.model_dump(mode='json') for event in GAMEPLAY_EVENTS.get(session_id, [])]
    path.write_text(__import__('json').dumps(events, indent=2, ensure_ascii=False), encoding='utf-8')
    return path
