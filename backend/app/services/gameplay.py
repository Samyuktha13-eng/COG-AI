from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..data.narrations import NARRATIONS
from ..models.care_plan import CarePlan
from ..models.game_session import GameSession, SessionStatus
from ..models.video_job import VideoJobStatus
from .gameplay_events import record_gameplay_event
from .story_playback import StoryAgent


class VideoProvider(Protocol):
    def request(self, patient_id: str, story_id: str, beat_id: str) -> tuple[str, str]: ...


@dataclass(frozen=True)
class PendingVideo:
    status: str
    request_id: str | None
    video_url: str | None
    preview_url: str | None = None


class LibraryVideoProvider:
    """Return a completed scene URL when available, otherwise treat the beat as unresolved."""

    def request(self, patient_id: str, story_id: str, beat_id: str) -> tuple[str, str | None]:
        from datetime import datetime, timezone

        from ..services.patient_library import VIDEO_JOBS

        matches = [
            job for job in VIDEO_JOBS.values()
            if job.patient_id == patient_id and job.story_id == story_id and job.scene_id == beat_id
        ]
        if not matches:
            return "no_job", None

        completed = [job for job in matches if job.status == VideoJobStatus.COMPLETED]
        latest = max(
            completed or matches,
            key=lambda job: (job.updated_at or datetime.min.replace(tzinfo=timezone.utc)),
        )

        if latest.status == VideoJobStatus.COMPLETED:
            if latest.output_path:
                output = Path(latest.output_path)
                try:
                    from ..services.patient_library import PATIENT_LIBRARY_ROOT
                    rel = output.resolve().relative_to(PATIENT_LIBRARY_ROOT.resolve())
                    return "completed", "/patient-library/" + rel.as_posix()
                except (OSError, ValueError):
                    pass
            if latest.output_url:
                return "completed", latest.output_url

        if latest.output_url:
            return "processing", latest.output_url

        return latest.status.value, None

    @staticmethod
    def _preview_image_url(story_id: str, beat_id: str) -> str | None:
        try:
            from ..data.stories import get_story
            from ..services.assets import STORY_IMAGE_ROOT

            story = get_story(story_id)
            if story is None:
                return None
            beat = next((b for b in story.beats if b.id == beat_id), None)
            if beat is None or not beat.image_path:
                return None
            image_path = (STORY_IMAGE_ROOT / beat.image_path).resolve()
            if image_path.exists():
                return "/story-images/" + image_path.relative_to(STORY_IMAGE_ROOT.resolve()).as_posix()
        except Exception:
            pass
        return None


class DeferredVideoProvider:
    """Fallback: returns a submit URL when no completed job exists yet."""

    def request(self, patient_id: str, story_id: str, beat_id: str) -> tuple[str, str]:
        return "pending_provider", f"/api/generation/story/{story_id}/beat/{beat_id}/submit"


class GamePlayService:
    def __init__(
        self,
        session: GameSession,
        story_agent: StoryAgent,
        care_plan: CarePlan | None = None,
        video_provider: VideoProvider | None = None,
    ):
        self.session = session
        self.story_agent = story_agent
        self.care_plan = care_plan or CarePlan(patient_id=session.patient_id)
        self.video_provider = video_provider or LibraryVideoProvider()

    @staticmethod
    def _preview_image_url(story_id: str, beat_id: str | None) -> str | None:
        if not beat_id:
            return None
        try:
            from ..data.stories import get_story
            from ..services.assets import STORY_IMAGE_ROOT

            story = get_story(story_id)
            if story is None:
                return None
            beat = next((b for b in story.beats if b.id == beat_id), None)
            if beat is None or not beat.image_path:
                return None
            image_path = (STORY_IMAGE_ROOT / beat.image_path).resolve()
            if image_path.exists():
                return "/story-images/" + image_path.relative_to(STORY_IMAGE_ROOT.resolve()).as_posix()
        except Exception:
            pass
        return None

    def _refresh_progress_state(self) -> None:
        beats = self.story_agent.beats()
        total_beats = len(beats)
        completed_count = len(self.session.completed_beat_ids)
        next_beat = next((b for b in beats if b.id not in self.session.completed_beat_ids), None)

        self.session.progress["memory_scene_started"] = bool(self.session.current_beat_id or self.session.completed_beat_ids)
        self.session.progress["response_recorded"] = bool(self.session.last_transcript or self.session.event_ids)
        self.session.progress["reminder_completed"] = bool(self.session.acknowledged_care_reminder_ids)
        self.session.progress["session_report_created"] = self.session.status == SessionStatus.COMPLETED

        self.session.story_progression = {
            "level": "chapter_1" if total_beats else "intro",
            "chapter": max(1, min(3, (completed_count + 1))),
            "current_beat": self.session.current_beat_id,
            "current_beat_sequence": self.session.current_beat_sequence,
            "completed_beats": completed_count,
            "total_beats": total_beats,
            "next_beat_unlocked": next_beat.id if next_beat else None,
            "progress_percent": round((completed_count / total_beats) * 100, 1) if total_beats else 0.0,
        }

        guidance: list[str] = []
        if self.session.current_beat_id:
            guidance.append("Next memory prompt")
        if self.session.care_reminder:
            guidance.append("Reminder due now")
        if self.session.status == SessionStatus.COMPLETED:
            guidance.append("Care report ready")
        if not guidance:
            guidance = ["Start the memory scene"]
        self.session.caregiver_guidance = guidance

    def play_next(self) -> dict[str, object]:
        beats = self.story_agent.beats()
        if self.session.current_beat_id and self.session.current_beat_id not in self.session.completed_beat_ids:
            self.session.completed_beat_ids.append(self.session.current_beat_id)
        next_beats = [b for b in beats if b.id not in self.session.completed_beat_ids]
        if not next_beats:
            self.session.status = SessionStatus.COMPLETED
            self.session.progress["session_report_created"] = True
            self._refresh_progress_state()
            return {"status": self.session.status.value, "progress": self.session.progress, "story_progression": self.session.story_progression, "caregiver_guidance": self.session.caregiver_guidance}

        beat = next_beats[0]
        self.session.current_beat_id = beat.id
        self.session.current_beat_sequence = beat.sequence
        self.session.status = SessionStatus.PLAYING

        try:
            self.session.video_status, video_url = self.video_provider.request(
                self.session.patient_id, self.session.story_id, beat.id
            )
            self.session.video_request_id = None
            self.session.video_url = video_url if self.session.video_status == "completed" else None
            self.session.preview_url = self._preview_image_url(self.session.story_id, beat.id)
            self.session.video_error = None
        except Exception as error:
            self.session.video_status = "failed"
            self.session.video_request_id = None
            self.session.video_url = None
            self.session.preview_url = None
            self.session.video_error = str(error)

        # Narration
        requested_language = self.session.narration_language or "en"
        narration_data = NARRATIONS.get(beat.id, {})
        narration_by_language = beat.narration_by_language or {"en": beat.narration or narration_data.get("opening", "")}
        self.session.narration_language = requested_language
        self.session.narration_text = narration_by_language.get(requested_language) or narration_by_language.get("en", beat.narration)

        # Question — multilingual
        question_by_language = narration_data.get("question_by_language", {})
        question = question_by_language.get(requested_language) or narration_data.get("question", "")
        question_language = requested_language if requested_language in question_by_language else "en"
        self.session.current_question = question

        # Keep the current beat pending until the patient answers or skips it.
        self.session.status = SessionStatus.WAITING_FOR_SPEECH
        record_gameplay_event(
            session_id=self.session.session_id,
            patient_id=self.session.patient_id,
            story_id=self.session.story_id,
            event_type="memory_scene_started",
            beat_id=beat.id,
            chapter_id=self.session.story_id,
            question=self.session.current_question,
            metadata={"beat_sequence": beat.sequence, "video_status": self.session.video_status},
        )

        # Care reminder
        reminder = self._active_care_reminder()
        self.session.care_reminder_id = reminder.reminder_id if reminder else None
        self.session.care_reminder = reminder.task if reminder else None
        self.session.progress["memory_scene_started"] = True
        self._refresh_progress_state()

        preview_url = self.session.preview_url or (
            self._preview_image_url(self.session.story_id, beat.id)
            if self.session.video_status in {"no_job", "processing", "queued", "waiting", "pending_provider"}
            else None
        )
        self.session.preview_url = preview_url

        return {
            "status": self.session.status.value,
            "beat_id": beat.id,
            "beat_sequence": beat.sequence,
            "action": beat.action,
            "motion_sequence": beat.motion_sequence,
            "video": PendingVideo(
                self.session.video_status,
                self.session.video_request_id,
                self.session.video_url,
                preview_url,
            ),
            "preview_url": preview_url,
            "video_error": self.session.video_error,
            "narration": {
                "language": self.session.narration_language,
                "text": self.session.narration_text,
                "fallback_used": requested_language not in narration_by_language,
            },
            "question": question,
            "question_language": question_language,
            "care_reminder": self.session.care_reminder,
            "progress": self.session.progress,
            "story_progression": self.session.story_progression,
            "caregiver_guidance": self.session.caregiver_guidance,
        }

    def replay(self) -> dict[str, object]:
        if not self.session.current_beat_id:
            raise RuntimeError("There is no current beat to replay.")
        self.session.status = SessionStatus.PLAYING
        try:
            self.session.video_status, video_url = self.video_provider.request(
                self.session.patient_id, self.session.story_id, self.session.current_beat_id
            )
            self.session.video_url = video_url if self.session.video_status == "completed" else None
            self.session.preview_url = self._preview_image_url(self.session.story_id, self.session.current_beat_id)
            self.session.video_request_id = None
            self.session.video_error = None
        except Exception as error:
            self.session.video_status = "failed"
            self.session.video_request_id = None
            self.session.video_url = None
            self.session.preview_url = None
            self.session.video_error = str(error)
        self.session.status = SessionStatus.WAITING_FOR_SPEECH
        self._refresh_progress_state()
        preview_url = self.session.preview_url or (
            self._preview_image_url(self.session.story_id, self.session.current_beat_id)
            if self.session.video_status in {"no_job", "processing", "queued", "waiting", "pending_provider"}
            else None
        )
        self.session.preview_url = preview_url

        return {
            "status": self.session.status.value,
            "beat_id": self.session.current_beat_id,
            "question": self.session.current_question,
            "video": PendingVideo(
                self.session.video_status,
                self.session.video_request_id,
                self.session.video_url,
                preview_url,
            ),
            "preview_url": preview_url,
            "video_error": self.session.video_error,
            "progress": self.session.progress,
            "story_progression": self.session.story_progression,
            "caregiver_guidance": self.session.caregiver_guidance,
        }

    def acknowledge_care_reminder(self) -> bool:
        reminder_id = self.session.care_reminder_id
        if not reminder_id:
            return False
        if reminder_id not in self.session.acknowledged_care_reminder_ids:
            self.session.acknowledged_care_reminder_ids.append(reminder_id)
        self.session.progress["reminder_completed"] = True
        self.session.care_reminder = None
        self.session.care_reminder_id = None
        record_gameplay_event(
            session_id=self.session.session_id,
            patient_id=self.session.patient_id,
            story_id=self.session.story_id,
            event_type="care_reminder_acknowledged",
            beat_id=self.session.current_beat_id,
            chapter_id=self.session.story_id,
            metadata={"reminder_id": reminder_id},
        )
        self._refresh_progress_state()
        return True

    def _active_care_reminder(self):
        for item in self.care_plan.reminders:
            if item.enabled and item.reminder_id not in self.session.presented_care_reminder_ids:
                self.session.presented_care_reminder_ids.append(item.reminder_id)
                return item
        return None
