import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def system_status():
    mongodb_enabled = os.getenv("COGNIV_USE_MONGODB", "0").lower() in {"1", "true", "yes"}
    uri = os.getenv("MONGODB_URI", "")
    database = os.getenv("MONGODB_DATABASE", "cogniv_ai")

    return {
        "service": "cogniv-ai",
        "storage_mode": "mongodb-atlas" if mongodb_enabled and uri else "local-filesystem",
        "mongodb_enabled": mongodb_enabled,
        "mongodb_database": database,
        "mongodb_uri_configured": bool(uri),
        "patient_library_root": "/patient-library",
        "reminder_support": True,
        "difference_report_support": True,
        "grounding_enabled": True,
        "video_generation_enabled": True,
        "asr_enabled": True,
    }
