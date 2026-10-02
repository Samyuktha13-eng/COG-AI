"""
Session Store
=============
Persists session events and generates the Story Difference Report (.docx).

Folder layout
-------------
outputs/patient_library/{patient_id}/sessions/{session_id}/
    audio/          beat audio files
    transcripts/    one JSON per beat
    session_transcript.json
    story_difference_report.docx
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models.session_event import SessionEvent
from ..models.session_report import EvidenceItem, SessionReport, StoryComparison, StoryScore, UnsupportedItem
from ..services.difference_engine import analyse_events, original_story_fact

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PATIENT_LIBRARY_ROOT = PROJECT_ROOT / "outputs" / "patient_library"

# In-memory active session registry (session_id → GameSession)
# Imported by api/game.py for fast lookup during a live session.
from ..models.game_session import GameSession  # noqa: E402
SESSION_STORE: dict[str, GameSession] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_dir(patient_id: str, session_id: str) -> Path:
    d = PATIENT_LIBRARY_ROOT / patient_id / "sessions" / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build_story_scores(
    stories_played: list[str],
    comparisons: list[StoryComparison],
) -> list[StoryScore]:
    totals: dict[str, dict[str, int]] = {}
    for story_id in stories_played:
        if story_id:
            totals.setdefault(story_id, {"spoken_responses": 0, "matched_fragments": 0, "scored_fragments": 0})

    for comparison in comparisons:
        story_id = comparison.story_id or (stories_played[0] if len(stories_played) == 1 else "")
        if not story_id:
            continue
        total = totals.setdefault(story_id, {"spoken_responses": 0, "matched_fragments": 0, "scored_fragments": 0})
        total["spoken_responses"] += 1
        total["matched_fragments"] += comparison.matched_fragments
        total["scored_fragments"] += comparison.scored_fragments

    result = []
    for story_id, total in totals.items():
        scored_fragments = total["scored_fragments"]
        score = round(total["matched_fragments"] * 100 / scored_fragments) if scored_fragments else None
        score_label = (
            "No scored responses" if score is None else
            "Strong story match" if score >= 75 else
            "Partial story match" if score >= 40 else
            "Additional content to review"
        )
        result.append(StoryScore(
            story_id=story_id,
            score=score,
            score_label=score_label,
            spoken_responses=total["spoken_responses"],
            matched_fragments=total["matched_fragments"],
            scored_fragments=scored_fragments,
        ))
    return result


def _format_utc_timestamp(value: str | None) -> str:
    if not value:
        return "Time unavailable"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Save a single event
# ---------------------------------------------------------------------------
def save_event(event: SessionEvent) -> None:
    d = _session_dir(event.patient_id, event.session_id) / "transcripts"
    d.mkdir(exist_ok=True)
    path = d / f"beat_{event.sequence:03d}_{event.beat_id}.json"
    path.write_text(
        json.dumps(event.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    from .mongo_store import persist_session_event
    persist_session_event(event)


# ---------------------------------------------------------------------------
# Save audio bytes for a beat
# ---------------------------------------------------------------------------
def save_audio(patient_id: str, session_id: str, beat_id: str, sequence: int, data: bytes) -> str:
    d = _session_dir(patient_id, session_id) / "audio"
    d.mkdir(exist_ok=True)
    filename = f"beat_{sequence:03d}_{beat_id}.wav"
    (d / filename).write_bytes(data)
    relative_path = f"audio/{filename}"
    from .mongo_store import persist_session_audio
    persist_session_audio(patient_id, session_id, relative_path, data)
    return relative_path


# ---------------------------------------------------------------------------
# Finalise session → session_transcript.json + report.docx
# ---------------------------------------------------------------------------
def finalise_session(
    session_id: str,
    patient_id: str,
    patient_name: str,
    stories_played: list[str],
    events: list[SessionEvent],
    started_at: datetime,
    ended_at: datetime | None = None,
) -> SessionReport:
    ended_at = ended_at or _now()
    supported, unsupported = analyse_events(events)
    scored_responses = len(supported) + len(unsupported)
    memory_score = round(len(supported) / scored_responses * 100) if scored_responses else None
    memory_score_label = (
        "No scored responses" if memory_score is None else
        "Strong story match" if memory_score >= 75 else
        "Partial story match" if memory_score >= 40 else
        "Additional content to review"
    )
    story_comparisons = []
    for event in events:
        if not event.spoken or not event.transcript:
            continue
        event_supported, event_unsupported = analyse_events([event])
        event_count = len(event_supported) + len(event_unsupported)
        event_score = round(len(event_supported) * 100 / event_count) if event_count else None
        if event_score is None:
            match_summary = "Not scored: no match could be established in this language."
        elif event_score == 100:
            match_summary = "Story details matched."
        elif event_score > 0:
            match_summary = f"Partial story match ({event_score}%)."
        else:
            match_summary = "No story detail matched."
        unmatched = [item.transcript_fragment for item in event_unsupported]
        difference = match_summary
        if unmatched:
            difference += " Unmatched answer: " + " / ".join(unmatched)
        story_id = event.story_id or (stories_played[0] if len(stories_played) == 1 else "")
        story_comparisons.append(StoryComparison(
            story_id=story_id,
            beat_id=event.beat_id or "",
            timestamp=event.started_at,
            question=event.question or "",
            original_story=original_story_fact(event.beat_id) or "No canonical story text is stored for this beat.",
            patient_answer=event.transcript,
            match_score=event_score,
            matched_fragments=len(event_supported),
            scored_fragments=event_count,
            difference=difference,
        ))

    story_scores = _build_story_scores(stories_played, story_comparisons)

    report = SessionReport(
        session_id=session_id,
        patient_id=patient_id,
        patient_name=patient_name,
        stories_played=stories_played,
        started_at=started_at,
        ended_at=ended_at,
        total_beats=len(events),
        spoken_responses=sum(1 for e in events if e.spoken),
        skipped_responses=sum(1 for e in events if not e.spoken),
        events=[e.model_dump(mode="json") for e in events],
        story_comparisons=story_comparisons,
        story_scores=story_scores,
        supported_content=supported,
        unsupported_content=unsupported,
        memory_score=memory_score,
        memory_score_label=memory_score_label,
    )

    session_dir = _session_dir(patient_id, session_id)

    # Write session_transcript.json
    (session_dir / "session_transcript.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Generate docx
    docx_path = _write_docx(report, session_dir)
    report.report_path = str(docx_path)

    from .mongo_store import persist_report
    persist_report(report)

    # Re-write with report_path populated
    (session_dir / "session_transcript.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


# ---------------------------------------------------------------------------
# DOCX generation
# ---------------------------------------------------------------------------
def _write_docx(report: SessionReport, session_dir: Path) -> Path:
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        # python-docx not installed — write a plain-text fallback
        txt_path = session_dir / "story_difference_report.txt"
        txt_path.write_text(_plain_text_report(report), encoding="utf-8")
        return txt_path

    doc = Document()

    # Title
    title = doc.add_heading(f"{report.patient_name} — Story Difference Report", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ── Section 1: Session information ──────────────────────────────────────
    doc.add_heading("Session Information", level=1)
    info = [
        ("Patient", report.patient_name),
        ("Patient ID", report.patient_id),
        ("Session ID", report.session_id),
        ("Date", report.started_at.strftime("%Y-%m-%d")),
        ("Start time", report.started_at.strftime("%H:%M UTC")),
        ("End time", report.ended_at.strftime("%H:%M UTC")),
        ("Stories played", ", ".join(s.replace("_", " ").title() for s in report.stories_played)),
        ("Total beats", str(report.total_beats)),
        ("Spoken responses", str(report.spoken_responses)),
        ("Skipped (no speech)", str(report.skipped_responses)),
        (
            "Story evidence match",
            f"{report.memory_score}% — {report.memory_score_label}"
            if report.memory_score is not None else f"N/A — {report.memory_score_label}",
        ),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(info):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    doc.add_paragraph()

    doc.add_heading("Story-Level Evidence Scores", level=1)
    doc.add_paragraph(
        "Scores measure alignment with the stored story evidence, not whether a spoken account is objectively true."
    )
    score_table = doc.add_table(rows=1 + len(report.story_scores), cols=5)
    score_table.style = "Table Grid"
    for cell, label in zip(score_table.rows[0].cells, ("Stored story", "Evidence match", "Spoken answers", "Matched fragments", "Scored fragments")):
        cell.text = label
    for row, story_score in zip(score_table.rows[1:], report.story_scores):
        row.cells[0].text = story_score.story_id.replace("_", " ").title()
        row.cells[1].text = (
            f"{story_score.score}% — {story_score.score_label}"
            if story_score.score is not None else story_score.score_label
        )
        row.cells[2].text = str(story_score.spoken_responses)
        row.cells[3].text = str(story_score.matched_fragments)
        row.cells[4].text = str(story_score.scored_fragments)

    doc.add_paragraph()

    # ── Section 2: Answer compared with original story ───────────────────────
    doc.add_heading("Patient Answers Compared with Original Story", level=1)
    doc.add_paragraph(
        "Patient answers are shown exactly as recognised beside the canonical story detail for that beat. "
        "A missing match means the detail could not be verified against the stored story; it is not a clinical conclusion."
    )
    doc.add_paragraph()

    if report.story_comparisons:
        tbl = doc.add_table(rows=1 + len(report.story_comparisons), cols=7)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Story"
        hdr[1].text = "Scene"
        hdr[2].text = "Spoken at (UTC)"
        hdr[3].text = "Original story"
        hdr[4].text = "Question"
        hdr[5].text = "Patient answer (ASR, unchanged)"
        hdr[6].text = "Match score / difference"
        for i, comparison in enumerate(report.story_comparisons, 1):
            row = tbl.rows[i].cells
            row[0].text = comparison.story_id.replace("_", " ").title()
            row[1].text = comparison.beat_id.replace("_", " ")
            row[2].text = _format_utc_timestamp(comparison.timestamp)
            row[3].text = comparison.original_story
            row[4].text = comparison.question
            row[5].text = comparison.patient_answer
            score = f"{comparison.match_score}%" if comparison.match_score is not None else "N/A"
            row[6].text = f"{score} — {comparison.difference}"
    else:
        doc.add_paragraph("No spoken responses were recorded in this session.")

    doc.add_paragraph()

    # ── Section 3: Story-grounded content ───────────────────────────────────
    doc.add_heading("Story-Grounded Content", level=1)
    doc.add_paragraph(
        "The following patient statements contain words or phrases that appear "
        "in the canonical patient story evidence."
    )
    doc.add_paragraph()

    if report.supported_content:
        for item in report.supported_content:
            p = doc.add_paragraph(style="List Bullet")
            run = p.add_run(f'"{item.transcript_fragment}"')
            run.bold = True
            p.add_run(
                f"  →  matched: {item.matched_story_fact}  "
                f"[{item.beat_id}]  Question: {item.question}  "
                f"Time: {item.timestamp or 'unknown'}"
            )
    else:
        doc.add_paragraph("No story-grounded content identified in this session.")

    doc.add_paragraph()

    # ── Section 4: Additional / unsupported content ──────────────────────────
    doc.add_heading("Additional Content — Not Found in Available Patient Evidence", level=1)
    doc.add_paragraph(
        "The following patient statements were not matched to the available story documents, "
        "story chapters, or reference images. "
        "This does not mean the patient is incorrect — absence from the stored material "
        "does not prove that the event never happened. "
        "These observations should be reviewed by a qualified clinician."
    )
    doc.add_paragraph()

    if report.unsupported_content:
        for item in report.unsupported_content:
            p = doc.add_paragraph(style="List Bullet")
            run = p.add_run(f'"{item.transcript_fragment}"')
            run.bold = True
            p.add_run(
                f"  —  {item.reason}  [{item.beat_id}]  "
                f"Question: {item.question}  Time: {item.timestamp or 'unknown'}"
            )
    else:
        doc.add_paragraph("No additional content identified in this session.")

    doc.add_paragraph()

    # ── Footer note ──────────────────────────────────────────────────────────
    doc.add_paragraph(
        "IMPORTANT: This document is a memory-support observation record, "
        "not a clinical diagnosis. All findings should be interpreted by a "
        "qualified healthcare professional in the context of the patient's full history.",
    ).runs[0].italic = True

    date_str = report.started_at.strftime("%Y-%m-%d")
    filename = f"{report.patient_name}_Session_{date_str}_Story_Differences.docx"
    path = session_dir / filename
    doc.save(str(path))
    return path


def _plain_text_report(report: SessionReport) -> str:
    lines = [
        f"{report.patient_name} — Story Difference Report",
        "=" * 60,
        f"Patient: {report.patient_name}",
        f"Session: {report.session_id}",
        f"Date: {report.started_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Stories: {', '.join(report.stories_played)}",
        f"Total beats: {report.total_beats}",
        f"Spoken: {report.spoken_responses}  Skipped: {report.skipped_responses}",
        f"Story evidence match: {report.memory_score}% — {report.memory_score_label}"
        if report.memory_score is not None
        else f"Story evidence match: N/A — {report.memory_score_label}",
        "",
        "STORY-LEVEL EVIDENCE SCORES",
        "-" * 40,
        "Scores measure alignment with stored story evidence, not whether an account is objectively true.",
    ]
    for story_score in report.story_scores:
        score = f"{story_score.score}% — {story_score.score_label}" if story_score.score is not None else story_score.score_label
        lines.append(
            f"  {story_score.story_id}: {score}; {story_score.spoken_responses} spoken answers; "
            f"{story_score.matched_fragments}/{story_score.scored_fragments} matched fragments"
        )
    lines += [
        "",
        "PATIENT ANSWERS COMPARED WITH ORIGINAL STORY",
        "-" * 40,
    ]
    for comparison in report.story_comparisons:
        score = f"{comparison.match_score}%" if comparison.match_score is not None else "N/A"
        lines.append(
            f"Story: {comparison.story_id or 'Not available'}  "
            f"Date and time (UTC): {_format_utc_timestamp(comparison.timestamp)}"
        )
        lines.append(f"[{comparison.beat_id}] Q: {comparison.question}")
        lines.append(f"  Original story: {comparison.original_story}")
        lines.append(f"  Patient answer (ASR, unchanged): {comparison.patient_answer}")
        lines.append(f"  Match score: {score}")
        lines.append(f"  Difference / review: {comparison.difference}")
    lines += [
        "",
        "STORY-GROUNDED CONTENT",
        "-" * 40,
    ]
    for item in report.supported_content:
        lines.append(f'  "{item.transcript_fragment}" → {item.matched_story_fact}')
    lines += [
        "",
        "NOT FOUND IN AVAILABLE PATIENT EVIDENCE",
        "-" * 40,
    ]
    for item in report.unsupported_content:
        lines.append(f'  "{item.transcript_fragment}" — {item.reason}')
    lines.append(
        "\nIMPORTANT: This is a memory-support observation record, not a clinical diagnosis."
    )
    return "\n".join(lines)
