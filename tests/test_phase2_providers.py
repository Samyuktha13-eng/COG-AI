import asyncio

from backend.app.models.care_plan import CarePlan
from backend.app.models.game_session import GameSession
from backend.app.services.asr_provider import DeterministicASRProvider
from backend.app.services.gameplay import GamePlayService
from backend.app.services.story_playback import StoryAgent


class FailingVideoProvider:
    def request(self, story_id: str, beat_id: str):
        raise RuntimeError("Pixazo unavailable")


def test_video_provider_failure_stays_in_session_state():
    session = GameSession(session_id="s", patient_id="lakshmi_001", story_id="jasmine_morning")
    result = GamePlayService(
        session,
        StoryAgent("jasmine_morning"),
        CarePlan(patient_id="lakshmi_001"),
        FailingVideoProvider(),
    ).play_next()

    assert result["video"].status == "failed"
    assert result["video_error"] == "Pixazo unavailable"


def test_deterministic_asr_uses_stable_transcript_contract():
    provider = DeterministicASRProvider("She closed the door")
    job = asyncio.run(provider.submit("asset.wav", "session", "hi"))
    transcript = asyncio.run(provider.get_result(job))

    assert job.status == "completed"
    assert transcript.text == "She closed the door"
    assert transcript.language == "en"
    assert transcript.engine == "deterministic"
