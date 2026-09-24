from backend.app.data.reminders import JASMINE_MORNING_REMINDERS
from backend.app.models.beat import StoryBeat
from backend.app.services.story_playback import (
    GameEngine,
    PlaybackStatus,
    ReminderAgent,
    StoryAgent,
)


class FakeVideoGenerator:
    def __init__(self):
        self.played: list[str] = []

    def play(self, beat: StoryBeat) -> str:
        self.played.append(beat.id)
        return f"video://{beat.id}"


def test_jasmine_morning_uses_delayed_recall_without_rewriting_story():
    video_generator = FakeVideoGenerator()
    engine = GameEngine(
        StoryAgent("jasmine_morning"),
        ReminderAgent(JASMINE_MORNING_REMINDERS),
        video_generator,
    )

    first = engine.play_next()
    second = engine.play_next()
    third = engine.play_next()

    assert [first["beat_id"], second["beat_id"], third["beat_id"]] == [
        "jasmine_01",
        "jasmine_02",
        "jasmine_03",
    ]
    assert first["status"] == PlaybackStatus.READY.value
    assert second["status"] == PlaybackStatus.READY.value
    assert third["status"] == PlaybackStatus.WAITING_FOR_RECALL.value
    assert third["reminder"].question.prompt == "What did Lakshmi do earlier with the door?"
    assert video_generator.played == ["jasmine_01", "jasmine_02", "jasmine_03"]

    correct = engine.answer("She closed the door.")
    assert correct.outcome == "recorded"
    assert engine.status == PlaybackStatus.READY

    fourth = engine.play_next()
    assert fourth["beat_id"] == "jasmine_04"
    assert fourth["status"] == PlaybackStatus.WAITING_FOR_RECALL.value

    partial = engine.answer("She carried a pot.")
    assert partial.outcome == "recorded"
    assert engine.status == PlaybackStatus.READY

    fifth = engine.play_next()
    assert fifth["beat_id"] == "jasmine_05"
    assert fifth["status"] == PlaybackStatus.WAITING_FOR_RECALL.value

    recorded = engine.answer("I do not remember.")
    assert recorded.outcome == "recorded"
    assert recorded.feedback == ""
    assert engine.status == PlaybackStatus.READY

    sixth = engine.play_next()
    seventh = engine.play_next()
    eighth = engine.play_next()
    assert [sixth["beat_id"], seventh["beat_id"], eighth["beat_id"]] == [
        "jasmine_06",
        "jasmine_07",
        "jasmine_08",
    ]
    assert engine.play_next()["status"] == PlaybackStatus.COMPLETED.value
