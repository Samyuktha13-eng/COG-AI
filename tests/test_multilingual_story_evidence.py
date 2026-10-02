from datetime import datetime, timezone

import pytest

from backend.app.models.session_event import SessionEvent
from backend.app.models.session_report import SessionReport, StoryComparison, StoryScore
from backend.app.services.difference_engine import analyse_events
from backend.app.services.session_store import _build_story_scores, _plain_text_report, finalise_session


@pytest.mark.parametrize(
    ("beat_id", "transcript"),
    [
        ("jasmine_01", "లక్ష్మి తలుపు మూస్తుంది."),
        ("jasmine_02", "తను నీల్ని నింపి చెడ్ల నీళ్లుబోస్తుంది."),
        ("jasmine_03", "తను మల్లెచెట్టుకి నీళ్లు పోస్తుంది."),
        ("jasmine_04", "మల్లెపూవ్వు."),
        ("jasmine_05", "పువ్వులళ్లుతుంది. నానం తీసుకొని."),
        ("jasmine_06", "ఆకులు విడదీపెట్టడానికి."),
        ("jasmine_07", "పూవులను మల్లె పూల."),
        ("jasmine_08", "మల్లెపూల దండం."),
    ],
)
def test_telugu_jasmine_answers_are_scored_against_their_beat(beat_id, transcript, monkeypatch):
    monkeypatch.setattr("backend.app.services.difference_engine.translate_to_english", lambda *_: None)
    event = SessionEvent(
        beat_id=beat_id,
        transcript=transcript,
        transcript_language="te",
        spoken=True,
    )

    supported, unsupported = analyse_events([event])

    if beat_id == "jasmine_06":
        assert not supported
        assert unsupported
    else:
        assert supported


@pytest.mark.parametrize(
    ("language", "beat_id", "transcript"),
    [
        ("hi", "jasmine_08", "चमेली की माला"),
        ("ta", "jasmine_06", "நூல்"),
        ("kn", "jasmine_02", "ನೀರು"),
    ],
)
def test_other_narrated_languages_match_story_concepts(language, beat_id, transcript, monkeypatch):
    monkeypatch.setattr("backend.app.services.difference_engine.translate_to_english", lambda *_: None)
    event = SessionEvent(
        beat_id=beat_id,
        transcript=transcript,
        transcript_language=language,
        spoken=True,
    )

    supported, unsupported = analyse_events([event])

    assert supported
    assert not unsupported


def test_translated_answer_matches_a_non_jasmine_story_beat(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.difference_engine.translate_to_english",
        lambda text, language: "Lakshmi chooses the largest mango from the bag." if language == "brx" else None,
    )
    event = SessionEvent(
        beat_id="mango_01",
        transcript="बागि बाहायनाय",
        transcript_language="brx",
        spoken=True,
    )

    supported, unsupported = analyse_events([event])

    assert supported
    assert not unsupported


def test_memory_report_shows_original_story_next_to_unchanged_answer():
    report = SessionReport(
        patient_name="Lakshmi",
        started_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        ended_at=datetime(2026, 9, 30, 0, 1, tzinfo=timezone.utc),
        story_scores=[StoryScore(
            story_id="jasmine_morning",
            score=50,
            score_label="Partial story match",
            spoken_responses=1,
            matched_fragments=1,
            scored_fragments=2,
        )],
        story_comparisons=[StoryComparison(
            story_id="jasmine_morning",
            beat_id="jasmine_02",
            timestamp="2026-09-30T10:00:30+00:00",
            question="What is Lakshmi filling at the tap?",
            original_story="Lakshmi fills the small brass pot halfway at the tap.",
            patient_answer="తను నీల్ని నింపి చెడ్ల నీళ్లుబోస్తుంది.",
            match_score=50,
            matched_fragments=1,
            scored_fragments=2,
            difference="Partial story match (50%). Unmatched answer: చెడ్ల నీళ్లుబోస్తుంది",
        )],
    )

    rendered = _plain_text_report(report)

    assert "Original story: Lakshmi fills the small brass pot halfway at the tap." in rendered
    assert "Patient answer (ASR, unchanged): తను నీల్ని నింపి చెడ్ల నీళ్లుబోస్తుంది." in rendered
    assert "Match score: 50%" in rendered
    assert "jasmine_morning: 50%" in rendered
    assert "2026-09-30 10:00 UTC" in rendered
    assert "Unmatched answer:" in rendered
    assert "Story evidence match: N/A" in rendered


def test_story_scores_are_weighted_by_scored_fragments():
    comparisons = [
        StoryComparison(story_id="story_one", matched_fragments=1, scored_fragments=1),
        StoryComparison(story_id="story_one", matched_fragments=1, scored_fragments=3),
        StoryComparison(story_id="story_two", matched_fragments=0, scored_fragments=0),
    ]

    scores = _build_story_scores(["story_one", "story_two"], comparisons)

    assert [(item.story_id, item.score, item.spoken_responses) for item in scores] == [
        ("story_one", 50, 2),
        ("story_two", None, 1),
    ]


def test_finalise_session_preserves_supplied_end_time(monkeypatch, tmp_path):
    from backend.app.services import session_store

    started_at = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    ended_at = datetime(2026, 9, 30, 10, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(session_store, "PATIENT_LIBRARY_ROOT", tmp_path)

    def write_report_file(report, session_dir):
        path = session_dir / "story_difference_report.txt"
        path.write_text("test report", encoding="utf-8")
        return path

    monkeypatch.setattr(session_store, "_write_docx", write_report_file)
    monkeypatch.setattr("backend.app.services.mongo_store.persist_report", lambda report: None)

    report = finalise_session(
        session_id="completed-session",
        patient_id="lakshmi_001",
        patient_name="Lakshmi",
        stories_played=["jasmine_morning"],
        events=[],
        started_at=started_at,
        ended_at=ended_at,
    )

    assert report.started_at == started_at
    assert report.ended_at == ended_at