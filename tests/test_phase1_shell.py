from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.phase1 import ASSETS, SESSIONS


client = TestClient(app)


def test_phase1_patient_story_and_prompt_resolution():
    story_response = client.get("/api/patient/lakshmi_001/story")
    assert story_response.status_code == 200
    payload = story_response.json()
    assert payload["patient"]["name"] == "Lakshmi"
    assert len(payload["chapters"]) == 42
    assert len(payload["stories"]) == 5

    resolved = client.post(
        "/api/story/resolve",
        json={
            "patient_id": "lakshmi_001",
            "story_id": "jasmine_morning",
            "prompt": "Tell me about the jasmine flowers",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["beat_id"] in {"jasmine_04", "jasmine_05"}


def test_phase1_uploads_and_session_are_patient_scoped():
    image = client.post(
        "/api/assets/lakshmi_001/image",
        files={"image": ("memory.jpg", b"fake-image", "image/jpeg")},
    )
    assert image.status_code == 200
    assert image.json()["patient_id"] == "lakshmi_001"

    voice = client.post(
        "/api/assets/lakshmi_001/voice",
        files={"audio": ("memory.wav", b"fake-audio", "audio/wav")},
    )
    assert voice.status_code == 200
    assert voice.json()["transcription_status"] == "pending"

    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning"},
    )
    assert session.status_code == 200
    assert session.json()["story_id"] == "jasmine_morning"
    assert session.json()["session_id"] in SESSIONS
    assert len(ASSETS) >= 2
