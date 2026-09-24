from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol

from ..data.reminders import JASMINE_MORNING_REMINDERS
from ..data.story_activities import LAKSHMI_STORY_ACTIVITIES
from ..data.stories import get_story
from ..models.beat import StoryBeat
from ..models.care_plan import CarePlan, CarePlanReminder
from ..models.reminder import BeatReminder
from ..models.story_activity import StoryDerivedActivity


class PlaybackStatus(str, Enum):
    READY = "ready"
    PLAYING = "playing"
    WAITING_FOR_RECALL = "waiting_for_recall"
    COMPLETED = "completed"
    REPLAY_REQUIRED = "replay_required"


class VideoGenerator(Protocol):
    def play(self, beat: StoryBeat) -> str: ...


@dataclass(frozen=True)
class RecallResult:
    outcome: str
    feedback: str
    next_status: PlaybackStatus


class StoryAgent:
    def __init__(self, story_id: str):
        story = get_story(story_id)
        if story is None:
            raise ValueError(f"Story not found: {story_id}")
        self.story = story

    def beats(self) -> list[StoryBeat]:
        return sorted(self.story.beats, key=lambda beat: beat.sequence)

    def activities(self) -> list[StoryDerivedActivity]:
        return list(LAKSHMI_STORY_ACTIVITIES)


class ReminderAgent:
    def __init__(
        self,
        reminders: dict[str, BeatReminder] | None = None,
        care_plan: CarePlan | None = None,
    ):
        self.reminders = JASMINE_MORNING_REMINDERS if reminders is None else reminders
        self.care_plan = care_plan or CarePlan(patient_id="P001")

    def after_video(self, beat_id: str) -> BeatReminder | None:
        reminder = self.reminders.get(beat_id)
        if reminder and reminder.enabled:
            return reminder
        return None

    def story_activities(self) -> list[StoryDerivedActivity]:
        return list(LAKSHMI_STORY_ACTIVITIES)

    def care_plan_reminders(self) -> list[CarePlanReminder]:
        return [reminder for reminder in self.care_plan.reminders if reminder.enabled]


class GameEngine:
    def __init__(self, story_agent: StoryAgent, reminder_agent: ReminderAgent, video_generator: VideoGenerator):
        self.story_agent = story_agent
        self.reminder_agent = reminder_agent
        self.video_generator = video_generator
        self.status = PlaybackStatus.READY
        self.current_beat: StoryBeat | None = None
        self.pending_reminder: BeatReminder | None = None
        self.completed_beats: list[str] = []

    def play_next(self) -> dict[str, object]:
        if self.status == PlaybackStatus.WAITING_FOR_RECALL:
            raise RuntimeError("Answer the pending recall before continuing.")
        if self.status == PlaybackStatus.REPLAY_REQUIRED:
            raise RuntimeError("Replay the current beat before continuing.")

        next_beats = [beat for beat in self.story_agent.beats() if beat.id not in self.completed_beats]
        if not next_beats:
            self.status = PlaybackStatus.COMPLETED
            return {"status": self.status.value}

        beat = next_beats[0]
        self.current_beat = beat
        self.status = PlaybackStatus.PLAYING
        video_url = self.video_generator.play(beat)
        self.completed_beats.append(beat.id)

        reminder = self.reminder_agent.after_video(beat.id)
        if reminder:
            self.pending_reminder = reminder
            self.status = PlaybackStatus.WAITING_FOR_RECALL
            return {
                "status": self.status.value,
                "beat_id": beat.id,
                "video_url": video_url,
                "reminder": reminder,
            }

        self.status = PlaybackStatus.READY
        return {"status": self.status.value, "beat_id": beat.id, "video_url": video_url}

    def answer(self, response: str) -> RecallResult:
        if self.status != PlaybackStatus.WAITING_FOR_RECALL or self.pending_reminder is None:
            raise RuntimeError("There is no pending recall question.")

        self.pending_reminder = None
        self.status = PlaybackStatus.READY
        return RecallResult("recorded", "", PlaybackStatus.READY)

    @staticmethod
    def _matches_part_of_concept(response: str, concept: str) -> bool:
        concept_words = [word for word in GameEngine._normalize_answer(concept).split() if len(word) >= 3]
        return any(word in response for word in concept_words)

    @staticmethod
    def _normalize_answer(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", value.lower()).split())

    def replay_current(self) -> dict[str, object]:
        if self.status != PlaybackStatus.REPLAY_REQUIRED or self.current_beat is None:
            raise RuntimeError("There is no beat waiting for replay.")
        video_url = self.video_generator.play(self.current_beat)
        reminder = self.reminder_agent.after_video(self.current_beat.id)
        self.pending_reminder = reminder
        self.status = PlaybackStatus.WAITING_FOR_RECALL if reminder else PlaybackStatus.READY
        return {"status": self.status.value, "beat_id": self.current_beat.id, "video_url": video_url}
