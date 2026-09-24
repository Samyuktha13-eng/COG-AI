"""Optional Firebase persistence for patient assets and session metadata."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_db = None
_bucket = None
_initialised = False


def _connect() -> bool:
    global _db, _bucket, _initialised
    if _initialised:
        return _db is not None
    _initialised = True
    if os.getenv("COGNIV_USE_FIREBASE", "0").lower() not in {"1", "true", "yes"}:
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage

        if not firebase_admin._apps:
            key_path = Path(os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS",
                Path(__file__).resolve().parents[3] / "firebase" / "serviceAccountKey.json.json",
            ))
            if not key_path.is_file():
                return False
            firebase_admin.initialize_app(
                credentials.Certificate(str(key_path)),
                {"storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", "")},
            )
        _db = firestore.client()
        _bucket = storage.bucket() if os.getenv("FIREBASE_STORAGE_BUCKET") else None
        return True
    except Exception:
        _db = None
        _bucket = None
        return False


def persist_asset(asset: Any, content: bytes) -> None:
    """Mirror asset metadata and bytes when Firebase is explicitly enabled."""
    if not _connect():
        return
    payload = asset.model_dump(mode="json")
    _db.collection("patients").document(asset.patient_id).collection("assets").document(asset.asset_id).set(payload)
    if _bucket is not None:
        blob = _bucket.blob(f"patients/{asset.patient_id}/assets/{asset.asset_id}/{asset.name}")
        blob.upload_from_string(content)


def persist_session_audio(patient_id: str, session_id: str, relative_path: str, content: bytes) -> None:
    if not _connect() or _bucket is None:
        return
    _bucket.blob(f"patients/{patient_id}/sessions/{session_id}/{relative_path}").upload_from_string(content)


def persist_session_event(event: Any) -> None:
    if not _connect():
        return
    _db.collection("patients").document(event.patient_id).collection("sessions").document(event.session_id).collection("events").document(event.event_id).set(event.model_dump(mode="json"))


def persist_report(report: Any) -> None:
    if not _connect():
        return
    _db.collection("patients").document(report.patient_id).collection("session_reports").document(report.session_id).set(report.model_dump(mode="json"))
    if _bucket is not None and report.report_path:
        report_path = Path(report.report_path)
        if report_path.is_file():
            _bucket.blob(
                f"patients/{report.patient_id}/sessions/{report.session_id}/{report_path.name}"
            ).upload_from_filename(str(report_path))