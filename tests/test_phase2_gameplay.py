from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_phase2_gameplay_speak_skip_flow():
    """
    New flow: video plays → question shown → patient speaks or skips →
    interaction stored → next beat. No right/wrong feedback.
    """
    # Set up a care plan with one reminder
    care_plan = client.put(
        "/api/patients/lakshmi_001/care-plan",
        json={
            "patient_id": "lakshmi_001",
            "reminders": [
                {
                    "reminder_id": "water_0900",
                    "patient_id": "lakshmi_001",
                    "task": "Drink water",
                    "reminder_type": "water",
                    "time": "09:00",
                }
            ],
        },
    )
    assert care_plan.status_code == 200

    # Start session
    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]

    # Play first beat
    first = client.post(f"/api/game/sessions/{session_id}/play").json()
    assert first["beat_id"] == "jasmine_01"
    assert first["status"] == "waiting_for_speech"
    assert "question" in first
    assert first["question"]  # non-empty question
    assert first["video"]["status"] in ("no_job", "pending_provider", "waiting")
    assert first["care_reminder"] == "Drink water"

    # Acknowledge care reminder
    ack = client.post(f"/api/game/sessions/{session_id}/care-reminder/acknowledge")
    assert ack.json()["acknowledged"] is True

    # Record a spoken interaction for beat 1
    interaction = client.post(
        f"/api/game/sessions/{session_id}/interaction",
        json={
            "beat_id": "jasmine_01",
            "beat_sequence": 1,
            "question": first["question"],
            "spoken": True,
            "transcript": "She was closing the wooden door",
            "transcript_language": "en",
        },
    ).json()
    assert interaction["stored"] is True
    assert "event_id" in interaction

    # Play second beat
    second = client.post(f"/api/game/sessions/{session_id}/play").json()
    assert second["beat_id"] == "jasmine_02"
    assert second["status"] == "waiting_for_speech"
    assert second["care_reminder"] is None  # reminder already acknowledged

    # Skip (no speech) for beat 2
    skip = client.post(
        f"/api/game/sessions/{session_id}/interaction",
        json={
            "beat_id": "jasmine_02",
            "beat_sequence": 2,
            "question": second["question"],
            "spoken": False,
        },
    ).json()
    assert skip["stored"] is True

    # Play third beat
    third = client.post(f"/api/game/sessions/{session_id}/play").json()
    assert third["beat_id"] == "jasmine_03"
    assert third["status"] == "waiting_for_speech"

    # Replay works and returns question
    replay = client.post(f"/api/game/sessions/{session_id}/replay").json()
    assert replay["beat_id"] == "jasmine_03"
    assert replay["status"] == "waiting_for_speech"
    assert "question" in replay

    # Audio interaction endpoint works
    audio_interaction = client.post(
        f"/api/game/sessions/{session_id}/interaction/audio",
        data={
            "beat_id": "jasmine_03",
            "beat_sequence": "3",
            "question": third["question"],
            "transcript": "She carried the brass pot",
            "transcript_language": "en",
        },
        files={"audio": ("beat_003.wav", b"RIFF\x00\x00\x00\x00WAVE", "audio/wav")},
    )
    assert audio_interaction.status_code == 200
    assert audio_interaction.json()["stored"] is True


def test_phase2_gameplay_multilingual_question():
    """Question is served in the requested language when available."""
    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning", "narration_language": "ta"},
    ).json()
    session_id = session["session_id"]

    beat = client.post(f"/api/game/sessions/{session_id}/play").json()
    assert beat["question_language"] == "ta"
    # Tamil question should contain Tamil characters or at least be non-empty
    assert beat["question"]


def test_phase2_gameplay_exposes_game_progression_states():
    """Game sessions expose explicit progress markers and caregiver guidance."""
    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]

    beat = client.post(f"/api/game/sessions/{session_id}/play").json()
    assert beat["progress"]["memory_scene_started"] is True
    assert beat["progress"]["response_recorded"] is False
    assert beat["progress"]["reminder_completed"] is False
    assert beat["progress"]["session_report_created"] is False
    assert beat["story_progression"]["current_beat"] == beat["beat_id"]
    assert beat["caregiver_guidance"]


def test_session_fetch_hydrates_completed_pixazo_video_url(monkeypatch):
    """A completed provider job should populate the active session's video_url."""
    from datetime import datetime, timezone

    from backend.app.models.generation import GenerationJob, GenerationStatus
    from backend.app.models.video_job import VideoJob, VideoJobStatus
    from backend.app.services.patient_library import VIDEO_JOBS

    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]

    client.post(f"/api/game/sessions/{session_id}/play")

    VIDEO_JOBS.clear()
    VIDEO_JOBS["job_ready_1"] = VideoJob(
        job_id="job_ready_1",
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
        scene_id="jasmine_01",
        status=VideoJobStatus.PROCESSING,
        provider_job_id="pixazo-abc",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    def fake_get_status(job):
        job.status = GenerationStatus.COMPLETED
        job.output_url = "https://example.com/generated/jasmine_01.mp4"
        return job

    monkeypatch.setattr("backend.app.services.pixazo.PixazoVideoService.get_status", fake_get_status)

    refreshed = client.get(f"/api/game/sessions/{session_id}").json()

    assert refreshed["current_beat_id"] == "jasmine_01"
    assert refreshed["video_status"] == "completed"
    assert refreshed["video_url"] == "https://example.com/generated/jasmine_01.mp4"


def test_session_fetch_uses_latest_completed_job_when_same_beat_has_multiple_entries(monkeypatch):
    """The active beat should prefer the newest completed job, not the first stale match."""
    from datetime import datetime, timedelta, timezone

    from backend.app.models.generation import GenerationStatus
    from backend.app.models.video_job import VideoJob, VideoJobStatus
    from backend.app.services.patient_library import VIDEO_JOBS

    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "mango_tree", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]
    client.post(f"/api/game/sessions/{session_id}/play")

    now = datetime.now(timezone.utc)
    VIDEO_JOBS.clear()
    VIDEO_JOBS["stale_pending"] = VideoJob(
        job_id="stale_pending",
        patient_id="lakshmi_001",
        story_id="mango_tree",
        scene_id="mango_01",
        status=VideoJobStatus.PROCESSING,
        provider_job_id="pixazo-stale",
        created_at=now,
        updated_at=now,
    )
    VIDEO_JOBS["fresh_completed"] = VideoJob(
        job_id="fresh_completed",
        patient_id="lakshmi_001",
        story_id="mango_tree",
        scene_id="mango_01",
        status=VideoJobStatus.PROCESSING,
        provider_job_id="pixazo-fresh",
        created_at=now + timedelta(minutes=2),
        updated_at=now + timedelta(minutes=2),
    )

    def fake_get_status(job):
        if job.request_id == "pixazo-fresh":
            job.status = GenerationStatus.COMPLETED
            job.output_url = "https://example.com/generated/mango_01.mp4"
        else:
            job.status = GenerationStatus.PROCESSING
        return job

    monkeypatch.setattr("backend.app.services.pixazo.PixazoVideoService.get_status", fake_get_status)

    refreshed = client.get(f"/api/game/sessions/{session_id}").json()

    assert refreshed["current_beat_id"] == "mango_01"
    assert refreshed["video_status"] == "completed"
    assert refreshed["video_url"] == "https://example.com/generated/mango_01.mp4"


def test_library_video_provider_prefers_newest_matching_job():
    """A non-completed match should stay unresolved instead of pretending the video is ready."""
    from datetime import datetime, timedelta, timezone

    from backend.app.models.video_job import VideoJob, VideoJobStatus
    from backend.app.services.gameplay import LibraryVideoProvider
    from backend.app.services.patient_library import VIDEO_JOBS

    now = datetime.now(timezone.utc)
    VIDEO_JOBS.clear()
    VIDEO_JOBS["stale_waiting"] = VideoJob(
        job_id="stale_waiting",
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
        scene_id="jasmine_03",
        status=VideoJobStatus.WAITING,
        provider_job_id="old-provider",
        created_at=now,
        updated_at=now,
    )
    VIDEO_JOBS["fresh_processing"] = VideoJob(
        job_id="fresh_processing",
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
        scene_id="jasmine_03",
        status=VideoJobStatus.PROCESSING,
        provider_job_id="new-provider",
        created_at=now + timedelta(minutes=5),
        updated_at=now + timedelta(minutes=5),
    )

    status, video_url = LibraryVideoProvider().request("jasmine_morning", "jasmine_03")

    assert status == "no_job"
    assert video_url is None


def test_phase2_gameplay_end_session_generates_report():
    """End session creates session_transcript.json and a report file."""
    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "mango_tree", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]

    # Play one beat and record a spoken response
    beat = client.post(f"/api/game/sessions/{session_id}/play").json()
    client.post(
        f"/api/game/sessions/{session_id}/interaction",
        json={
            "beat_id": beat["beat_id"],
            "beat_sequence": beat["beat_sequence"],
            "question": beat["question"],
            "spoken": True,
            "transcript": "She was looking for the biggest mango in the kitchen",
            "transcript_language": "en",
        },
    )

    # End session
    result = client.post(f"/api/game/sessions/{session_id}/end").json()
    assert result["status"] == "completed"
    assert result["total_beats"] >= 1
    assert result["spoken_responses"] == 1
    assert result["skipped_responses"] == 0
    assert "download_url" in result

    # Report download endpoint exists
    report = client.get(f"/api/game/sessions/{session_id}/report")
    assert report.status_code == 200
    content_type = report.headers.get("content-type", "")
    assert "wordprocessingml" in content_type or "text/plain" in content_type


def test_phase2_gameplay_exposes_preview_url_while_video_is_processing():
    """The scene should show a preview still immediately while the Pixazo video is still processing."""
    session = client.post(
        "/api/game/sessions",
        json={"patient_id": "lakshmi_001", "story_id": "jasmine_morning", "narration_language": "en"},
    ).json()
    session_id = session["session_id"]

    beat = client.post(f"/api/game/sessions/{session_id}/play").json()

    assert beat["video"]["status"] in {"no_job", "processing", "pending_provider", "waiting"}
    assert beat["video"].get("preview_url") or beat.get("preview_url")


def test_library_video_provider_accepts_completed_http_output_url():
    """A completed Pixazo job should expose its public output URL as a playable video."""
    from datetime import datetime, timezone
    from unittest.mock import patch

    from backend.app.models.video_job import VideoJob, VideoJobStatus
    from backend.app.services.gameplay import LibraryVideoProvider

    completed_job = VideoJob(
        job_id="job_http_1",
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
        scene_id="jasmine_04",
        status=VideoJobStatus.COMPLETED,
        output_url="https://example.com/output/jasmine_04.mp4",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.dict("backend.app.services.patient_library.VIDEO_JOBS", {"job_http_1": completed_job}, clear=True):
        status, url = LibraryVideoProvider().request("jasmine_morning", "jasmine_04")

    assert status == "completed"
    assert url == "https://example.com/output/jasmine_04.mp4"
