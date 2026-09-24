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
from ..models.session_report import EvidenceItem, SessionReport, UnsupportedItem
from ..services.difference_engine import analyse_events

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
) -> SessionReport:
    ended_at = _now()
    supported, unsupported = analyse_events(events)
    scored_responses = len(supported) + len(unsupported)
    memory_score = round(len(supported) / scored_responses * 100) if scored_responses else 0
    memory_score_label = (
        "Strong story match" if memory_score >= 75 else
        "Partial story match" if memory_score >= 40 else
        "No scored responses" if not scored_responses else
        "Additional content to review"
    )

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
        ("Story evidence match", f"{report.memory_score}% — {report.memory_score_label}"),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(info):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    doc.add_paragraph()

    # ── Section 2: Transcript log ────────────────────────────────────────────
    doc.add_heading("Transcript Log", level=1)
    doc.add_paragraph(
        "The following table records each scene, the question shown to the patient, "
        "and the patient's spoken response exactly as recognised. "
        "No corrections have been applied."
    )
    doc.add_paragraph()

    spoken_events = [e for e in report.events if e.get("spoken")]
    if spoken_events:
        tbl = doc.add_table(rows=1 + len(spoken_events), cols=5)
        tbl.style = "Table Grid"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Scene"
        hdr[1].text = "Question"
        hdr[2].text = "Patient transcript"
        hdr[3].text = "Audio"
        hdr[4].text = "Timestamp"
        for i, ev in enumerate(spoken_events, 1):
            row = tbl.rows[i].cells
            row[0].text = ev.get("beat_id", "").replace("_", " ")
            row[1].text = ev.get("question", "")
            row[2].text = ev.get("transcript") or "(no transcript)"
            row[3].text = ev.get("audio_path") or "(not provided)"
            row[4].text = ev.get("started_at", "")
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
        "",
        "TRANSCRIPT LOG",
        "-" * 40,
    ]
    for ev in report.events:
        if ev.get("spoken"):
            lines.append(f"[{ev.get('beat_id')}] Q: {ev.get('question')}")
            lines.append(f"  Patient: {ev.get('transcript') or '(none)'}")
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
