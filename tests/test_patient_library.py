from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_patient_library_build_and_video_registry():
    # Reset folder state so this test is independent of prior runs
    from backend.app.services.patient_library import FOLDERS, VIDEO_JOBS
    if "lakshmi_001" in FOLDERS:
        FOLDERS["lakshmi_001"].story_status = "not_built"
        FOLDERS["lakshmi_001"].generation_status = "not_started"
        FOLDERS["lakshmi_001"].documents.clear()
        FOLDERS["lakshmi_001"].image_assets.clear()
        FOLDERS["lakshmi_001"].voice_story = None
    # Clear any existing video jobs for this patient
    for jid in [k for k, v in VIDEO_JOBS.items() if v.patient_id == "lakshmi_001"]:
        del VIDEO_JOBS[jid]

    before = client.get("/api/patients/lakshmi_001/folder")
    assert before.status_code == 200

    blocked = client.post("/api/patients/lakshmi_001/videos/generate")
    assert blocked.status_code == 409

    document = client.post(
        "/api/patients/lakshmi_001/folder/story-document",
        files={"document": ("Story 01 - The Jasmine Morning.docx", b"story", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert document.status_code == 200
    assert document.json()["type"] == "story_document"

    images = client.post(
        "/api/patients/lakshmi_001/folder/images",
        files=[
            ("images", ("jasmine_01.jpg", b"image-one", "image/jpeg")),
            ("images", ("jasmine_02.jpg", b"image-two", "image/jpeg")),
            ("relative_paths", (None, "jasmine/jasmine_01.jpg")),
            ("relative_paths", (None, "jasmine/jasmine_02.jpg")),
        ],
    )
    assert images.status_code == 200
    assert [item["relative_path"] for item in images.json()] == [
        "jasmine/jasmine_01.jpg",
        "jasmine/jasmine_02.jpg",
    ]

    voice = client.post(
        "/api/patients/lakshmi_001/folder/voice",
        files={"audio": ("lakshmi_story_recording.wav", b"audio", "audio/wav")},
    )
    assert voice.status_code == 200
    assert voice.json()["transcript_status"] == "queued"

    build = client.post("/api/patients/lakshmi_001/story/build")
    assert build.status_code == 200
    assert build.json()["status"] == "completed"
    # chapters_found = len(get_all_stories()) = 5 stories in the registry
    assert build.json()["chapters_found"] == 5
    assert build.json()["narration_prepared"] == 25  # 5 stories x 5 beats each

    jobs = client.post("/api/patients/lakshmi_001/videos/generate")
    assert jobs.status_code == 200
    assert len(jobs.json()) == 25
    assert all(job["status"] == "waiting" for job in jobs.json())

    status = client.get("/api/patients/lakshmi_001/videos/status")
    assert status.json()["total"] == 25
    assert status.json()["waiting"] == 25


def test_patient_library_bundle_upload_persists_assets():
    from backend.app.services.patient_library import FOLDERS

    if "lakshmi_001" in FOLDERS:
        FOLDERS["lakshmi_001"].documents.clear()
        FOLDERS["lakshmi_001"].image_assets.clear()
        FOLDERS["lakshmi_001"].voice_story = None
        FOLDERS["lakshmi_001"].document_text.clear()

    response = client.post(
        "/api/patients/lakshmi_001/folder/bundle",
        files=[
            ("files", ("story_note.txt", b"Jasmine morning at the back door", "text/plain")),
            ("files", ("mango_photo.jpg", b"image-one", "image/jpeg")),
            ("files", ("voice_story.wav", b"audio-bytes", "audio/wav")),
        ],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 3
    assert any(item["type"] == "story_document" for item in payload)
    assert any(item["type"] == "image" for item in payload)
    assert any(item["type"] == "voice_story" for item in payload)

    folder = client.get("/api/patients/lakshmi_001/folder")
    assert folder.status_code == 200
    body = folder.json()
    assert len(body["documents"]) == 1
    assert len(body["image_assets"]) == 1
    assert body["voice_story"] is not None


def test_patient_library_accepts_json_array_relative_paths():
    from backend.app.services.patient_library import FOLDERS

    if "lakshmi_001" in FOLDERS:
        FOLDERS["lakshmi_001"].image_assets.clear()

    response = client.post(
        "/api/patients/lakshmi_001/folder/images",
        files=[
            ("images", ("album_01.jpg", b"image-one", "image/jpeg")),
            ("images", ("album_02.jpg", b"image-two", "image/jpeg")),
            ("relative_paths", (None, '["album/album_01.jpg", "album/album_02.jpg"]')),
        ],
    )

    assert response.status_code == 200, response.text
    assert [item["relative_path"] for item in response.json()] == [
        "album/album_01.jpg",
        "album/album_02.jpg",
    ]
    assert all("/patient-library/" in item["url"] for item in response.json())


def test_patient_library_reset_generation_jobs_on_regenerate():
    from backend.app.services.patient_library import FOLDERS, VIDEO_JOBS

    if "lakshmi_001" not in FOLDERS:
        client.get("/api/patients/lakshmi_001/folder")

    folder = FOLDERS["lakshmi_001"]
    folder.story_status = "ready"
    folder.documents.clear()
    folder.image_assets.clear()
    folder.voice_story = None

    client.post(
        "/api/patients/lakshmi_001/folder/story-document",
        files={"document": ("story.docx", b"story", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    client.post(
        "/api/patients/lakshmi_001/folder/images",
        files=[
            ("images", ("a.jpg", b"one", "image/jpeg")),
            ("images", ("b.jpg", b"two", "image/jpeg")),
            ("relative_paths", (None, '["a.jpg", "b.jpg"]')),
        ],
    )
    client.post(
        "/api/patients/lakshmi_001/folder/voice",
        files={"audio": ("voice.wav", b"voice", "audio/wav")},
    )
    client.post("/api/patients/lakshmi_001/story/build")

    first = client.post("/api/patients/lakshmi_001/videos/generate")
    assert first.status_code == 200
    assert len(first.json()) == 25

    second = client.post("/api/patients/lakshmi_001/videos/generate")
    assert second.status_code == 200
    assert len(second.json()) == 25
    assert sum(1 for job in VIDEO_JOBS.values() if job.patient_id == "lakshmi_001") == 25


def test_patient_library_exposes_frontend_asset_urls():
    response = client.get("/api/patients/lakshmi_001/folder")
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"]
    assert payload["documents"][0]["url"].startswith("/patient-library/")
    assert payload["image_assets"][0]["url"].startswith("/patient-library/")


def test_grounded_generation_requires_real_pixazo_configuration(monkeypatch):
    from backend.app.api import phase1

    class DummyResult:
        match = True
        scene_plan = type("Plan", (), {
            "story_id": "jasmine_morning",
            "beat_id": "jasmine_01",
            "reference_images": ["01_jasmine_morning/jasmine_01_door.jpg"],
            "video_prompt": "Test motion prompt",
            "grounding_source": "prompt",
        })()
        reason = "matched"

    class DummyService:
        def __init__(self):
            pass

        def publish_image(self, path):
            return "http://localhost:8000/story-images/01_jasmine_morning/jasmine_01_door.jpg"

        def validate_public_image_url(self, image_url):
            return None

    monkeypatch.setattr(phase1.GroundingAgent, "resolve", lambda self, prompt: DummyResult())
    monkeypatch.setattr("backend.app.services.assets.StoryAssetService.publish_image", DummyService().publish_image)
    monkeypatch.setattr("backend.app.services.assets.StoryAssetService.validate_public_image_url", DummyService().validate_public_image_url)
    monkeypatch.setenv("PIXAZO_API_KEY", "")

    from backend.app.services.patient_library import FOLDERS

    folder = FOLDERS.setdefault("lakshmi_001", __import__("backend.app.models.patient_folder", fromlist=["PatientFolder"]).PatientFolder(patient_id="lakshmi_001"))
    folder.story_status = "ready"

    response = client.post(
        "/api/grounding/generate",
        json={"patient_id": "lakshmi_001", "prompt": "The jasmine morning at the back door"},
    )

    assert response.status_code == 503, response.text
    assert "PIXAZO_API_KEY" in response.text


def test_grounded_generation_submits_to_pixazo(monkeypatch):
    from backend.app.api import phase1

    class DummyResult:
        match = True
        scene_plan = type("Plan", (), {
            "story_id": "jasmine_morning",
            "beat_id": "jasmine_01",
            "reference_images": ["01_jasmine_morning/jasmine_01_door.jpg"],
            "video_prompt": "Test motion prompt",
        })()
        reason = "matched"

    class DummyPixazo:
        def submit(self, **kwargs):
            class DummyJob:
                request_id = "pixazo-123"
            return DummyJob()

    class DummyService:
        def __init__(self):
            pass

        def publish_image(self, path):
            return "http://localhost:8000/story-images/01_jasmine_morning/jasmine_01_door.jpg"

        def validate_public_image_url(self, image_url):
            return None

    monkeypatch.setattr(phase1.GroundingAgent, "resolve", lambda self, prompt: DummyResult())
    monkeypatch.setattr("backend.app.services.pixazo.PixazoVideoService.submit", DummyPixazo().submit)
    monkeypatch.setattr("backend.app.services.assets.StoryAssetService.publish_image", DummyService().publish_image)
    monkeypatch.setattr("backend.app.services.assets.StoryAssetService.validate_public_image_url", DummyService().validate_public_image_url)

    response = client.post(
        "/api/patients/lakshmi_001/videos/generate",
        json={"prompt": "The jasmine morning at the back door"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["story_id"] == "jasmine_morning"
    assert payload[0]["scene_id"] == "jasmine_01"
