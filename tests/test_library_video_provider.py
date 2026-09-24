"""
Regression tests for LibraryVideoProvider.

Covers the exact integration point fixed in the smoke-test pass:
  completed VideoJob + output_path  →  /patient-library/<rel>  →  play_next() video_url
  no job                            →  video_url = None
  job processing                    →  video_url = None
  job completed, path outside root  →  video_url = None
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.models.game_session import GameSession
from backend.app.models.video_job import VideoJob, VideoJobStatus
from backend.app.services.gameplay import GamePlayService, LibraryVideoProvider
from backend.app.services.story_playback import StoryAgent


# ── helpers ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _job(status: VideoJobStatus, output_path: str | None = None) -> VideoJob:
    return VideoJob(
        job_id=str(uuid.uuid4()),
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
        scene_id="jasmine_01",
        status=status,
        output_path=output_path,
        created_at=_now(),
        updated_at=_now(),
    )


def _session() -> GameSession:
    return GameSession(
        session_id=str(uuid.uuid4()),
        patient_id="lakshmi_001",
        story_id="jasmine_morning",
    )


FAKE_LIBRARY_ROOT = Path("/fake/patient_library")
FAKE_OUTPUT = FAKE_LIBRARY_ROOT / "lakshmi_001" / "video" / "jasmine_morning" / "jasmine_01.mp4"


# ── LibraryVideoProvider unit tests ──────────────────────────────────────────
# VIDEO_JOBS is imported inside LibraryVideoProvider.request() from patient_library,
# so we patch it there, not on the gameplay module.

class TestLibraryVideoProvider:

    def _call(self, jobs: dict, story_id="jasmine_morning", beat_id="jasmine_01"):
        provider = LibraryVideoProvider()
        with patch("backend.app.services.patient_library.VIDEO_JOBS", jobs), \
             patch("backend.app.services.patient_library.PATIENT_LIBRARY_ROOT", FAKE_LIBRARY_ROOT):
            return provider.request(story_id, beat_id)

    def test_completed_job_returns_served_url(self):
        job = _job(VideoJobStatus.COMPLETED, str(FAKE_OUTPUT))
        status, url = self._call({job.job_id: job})
        assert status == "completed"
        assert url == "/patient-library/lakshmi_001/video/jasmine_morning/jasmine_01.mp4"

    def test_no_job_returns_none_url(self):
        status, url = self._call({})
        assert status == "no_job"
        assert url is None

    def test_processing_job_returns_none_url(self):
        job = _job(VideoJobStatus.PROCESSING)
        status, url = self._call({job.job_id: job})
        assert status == "processing"
        assert url is None

    def test_waiting_job_returns_none_url(self):
        job = _job(VideoJobStatus.WAITING)
        status, url = self._call({job.job_id: job})
        assert status == "waiting"
        assert url is None

    def test_completed_job_path_outside_library_returns_none_url(self):
        outside_path = "/some/other/directory/jasmine_01.mp4"
        job = _job(VideoJobStatus.COMPLETED, outside_path)
        status, url = self._call({job.job_id: job})
        assert status == "completed"
        assert url is None

    def test_completed_job_no_output_path_returns_none_url(self):
        job = _job(VideoJobStatus.COMPLETED, None)
        status, url = self._call({job.job_id: job})
        assert status == "completed"
        assert url is None

    def test_different_story_not_matched(self):
        job = _job(VideoJobStatus.COMPLETED, str(FAKE_OUTPUT))
        status, url = self._call({job.job_id: job}, story_id="mango_tree")
        assert status == "no_job"
        assert url is None

    def test_different_beat_not_matched(self):
        job = _job(VideoJobStatus.COMPLETED, str(FAKE_OUTPUT))
        status, url = self._call({job.job_id: job}, beat_id="jasmine_02")
        assert status == "no_job"
        assert url is None


# ── play_next() integration: video_url flows through session ─────────────────

class TestPlayNextVideoUrl:

    def _make_service(self, video_jobs: dict) -> GamePlayService:
        session = _session()
        agent = StoryAgent("jasmine_morning")

        class _FakeProvider:
            def __init__(self, jobs):
                self._jobs = jobs

            def request(self, story_id, beat_id):
                for job in self._jobs.values():
                    if job.story_id == story_id and job.scene_id == beat_id:
                        if job.status == VideoJobStatus.COMPLETED and job.output_path:
                            output = Path(job.output_path)
                            try:
                                rel = output.relative_to(FAKE_LIBRARY_ROOT)
                                return "completed", "/patient-library/" + rel.as_posix()
                            except ValueError:
                                return "completed", None
                        return job.status.value, None
                return "no_job", None

        return GamePlayService(session, agent, video_provider=_FakeProvider(video_jobs))

    def test_play_next_with_completed_job_sets_video_url(self):
        job = _job(VideoJobStatus.COMPLETED, str(FAKE_OUTPUT))
        svc = self._make_service({job.job_id: job})
        result = svc.play_next()
        assert result["video"].video_url == "/patient-library/lakshmi_001/video/jasmine_morning/jasmine_01.mp4"
        assert result["video"].status == "completed"

    def test_play_next_with_no_job_video_url_is_none(self):
        svc = self._make_service({})
        result = svc.play_next()
        assert result["video"].video_url is None
        assert result["video"].status == "no_job"

    def test_play_next_with_processing_job_video_url_is_none(self):
        job = _job(VideoJobStatus.PROCESSING)
        svc = self._make_service({job.job_id: job})
        result = svc.play_next()
        assert result["video"].video_url is None
        assert result["video"].status == "processing"

    def test_play_next_action_field_is_human_readable(self):
        """action must be the beat's action text, not the beat id."""
        svc = self._make_service({})
        result = svc.play_next()
        assert result["beat_id"] == "jasmine_01"
        assert "door" in result["action"].lower() or "bends" in result["action"].lower()

    def test_play_next_narration_is_nested_object(self):
        """narration must be {language, text, fallback_used}."""
        svc = self._make_service({})
        result = svc.play_next()
        narration = result["narration"]
        assert "language" in narration
        assert "text" in narration
        assert "fallback_used" in narration
        assert narration["text"]  # non-empty


# ── replay() also returns video_url ──────────────────────────────────────────

class TestReplayVideoUrl:

    def test_replay_with_completed_job_sets_video_url(self):
        job = _job(VideoJobStatus.COMPLETED, str(FAKE_OUTPUT))
        session = _session()
        session.current_beat_id = "jasmine_01"

        class _FakeProvider:
            def request(self, story_id, beat_id):
                return "completed", "/patient-library/lakshmi_001/video/jasmine_morning/jasmine_01.mp4"

        svc = GamePlayService(session, StoryAgent("jasmine_morning"), video_provider=_FakeProvider())
        result = svc.replay()
        assert result["video"].video_url == "/patient-library/lakshmi_001/video/jasmine_morning/jasmine_01.mp4"

    def test_replay_with_no_job_video_url_is_none(self):
        session = _session()
        session.current_beat_id = "jasmine_01"

        class _FakeProvider:
            def request(self, story_id, beat_id):
                return "no_job", None

        svc = GamePlayService(session, StoryAgent("jasmine_morning"), video_provider=_FakeProvider())
        result = svc.replay()
        assert result["video"].video_url is None
