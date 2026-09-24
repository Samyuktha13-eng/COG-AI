"""Optional MongoDB Atlas persistence for patient files and session metadata."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_client = None
_database = None
_files = None
_initialised = False


def _connect() -> bool:
    global _client, _database, _files, _initialised
    if _initialised:
        return _database is not None
    _initialised = True
    uri = os.getenv("MONGODB_URI", "")
    if not uri or os.getenv("COGNIV_USE_MONGODB", "0").lower() not in {"1", "true", "yes"}:
        return False
    try:
        from gridfs import GridFSBucket
        from pymongo import MongoClient

        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        _database = _client[os.getenv("MONGODB_DATABASE", "cogniv_ai")]
        _files = GridFSBucket(_database)
        return True
    except Exception:
        _client = None
        _database = None
        _files = None
        return False


def persist_asset(asset: Any, content: bytes) -> None:
    if not _connect():
        return
    payload = asset.model_dump(mode="json")
    _database.patient_assets.replace_one({"asset_id": asset.asset_id}, payload, upsert=True)
    _files.upload_from_stream(
        f"patients/{asset.patient_id}/assets/{asset.asset_id}/{asset.name}",
        content,
        metadata={"kind": "patient_asset", "asset_id": asset.asset_id, "patient_id": asset.patient_id},
    )


def persist_session_audio(patient_id: str, session_id: str, relative_path: str, content: bytes) -> None:
    if not _connect():
        return
    _files.upload_from_stream(
        f"patients/{patient_id}/sessions/{session_id}/{relative_path}",
        content,
        metadata={"kind": "session_audio", "patient_id": patient_id, "session_id": session_id},
    )


def persist_session_event(event: Any) -> None:
    if not _connect():
        return
    _database.session_events.replace_one(
        {"event_id": event.event_id},
        event.model_dump(mode="json"),
        upsert=True,
    )


def persist_report(report: Any) -> None:
    if not _connect():
        return
    _database.session_reports.replace_one(
        {"session_id": report.session_id},
        report.model_dump(mode="json"),
        upsert=True,
    )
    if report.report_path:
        report_path = Path(report.report_path)
        if report_path.is_file():
            with report_path.open("rb") as stream:
                _files.upload_from_stream(
                    f"patients/{report.patient_id}/sessions/{report.session_id}/{report_path.name}",
                    stream,
                    metadata={"kind": "story_difference_report", "session_id": report.session_id},
                )