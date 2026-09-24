import re
import uuid
from pathlib import Path

from ..data.stories import get_all_stories, get_story
from ..models.asset import AssetType, PatientAsset
from ..models.care_plan import CarePlan, CarePlanReminder
from ..models.game_session import GameSession
from ..models.patient import PatientProfile
from ..models.speech_job import SpeechJob
from story.game_content import create_scene_store
from .session_store import SESSION_STORE
from .story_playback import StoryAgent

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PATIENT_UPLOAD_ROOT = PROJECT_ROOT / "outputs" / "patient_assets"

PATIENTS = {
    "lakshmi_001": PatientProfile(
        patient_id="lakshmi_001",
        name="Lakshmi",
        story_id="jasmine_morning",
    )
}
ASSETS: dict[str, PatientAsset] = {}
# Keep the legacy phase-1 session registry aligned with the live session store used by /api/game/*.
SESSIONS: dict[str, GameSession] = SESSION_STORE
CARE_PLANS: dict[str, CarePlan] = {
    "lakshmi_001": CarePlan(
        patient_id="lakshmi_001",
        reminders=[
            CarePlanReminder(
                reminder_id="rem_morning_water",
                patient_id="lakshmi_001",
                task="Drink water and settle into the memory routine.",
                reminder_type="hydration",
                time="09:00",
            ),
            CarePlanReminder(
                reminder_id="rem_morning_memory",
                patient_id="lakshmi_001",
                task="Open the jasmine morning memory scene and ask about the flowers.",
                reminder_type="routine",
                time="09:30",
            ),
            CarePlanReminder(
                reminder_id="rem_evening_recall",
                patient_id="lakshmi_001",
                task="Review the mango tree memory and talk about the family moment.",
                reminder_type="routine",
                time="18:30",
            ),
        ],
    )
}
SPEECH_JOBS: dict[str, SpeechJob] = {}


def patient_profile(patient_id: str) -> PatientProfile | None:
    return PATIENTS.get(patient_id)


def story_catalog():
    return get_all_stories()


def patient_chapters():
    return create_scene_store().list_scenes()


def find_beat_for_prompt(story_id: str, prompt: str):
    story = get_story(story_id)
    if story is None:
        return None
    words = set(re.findall(r"[a-z]+", prompt.lower()))
    candidates = []
    for beat in story.beats:
        haystack = f"{beat.action} {beat.motion} {beat.narration or ''}".lower()
        score = sum(word in haystack for word in words if len(word) >= 4)
        candidates.append((score, -beat.sequence, beat))
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def create_session(patient_id: str, story_id: str) -> GameSession:
    if patient_id not in PATIENTS:
        raise ValueError("Patient not found")
    if get_story(story_id) is None:
        raise ValueError("Story not found")
    session = GameSession(session_id=str(uuid.uuid4()), patient_id=patient_id, story_id=story_id)
    SESSIONS[session.session_id] = session
    return session


def save_upload(patient_id: str, asset_type: AssetType, filename: str, content: bytes, story_reference: str | None = None) -> PatientAsset:
    if patient_id not in PATIENTS:
        raise ValueError("Patient not found")
    safe_name = Path(filename).name
    asset_id = str(uuid.uuid4())
    destination = PATIENT_UPLOAD_ROOT / patient_id / asset_type.value / f"{asset_id}_{safe_name}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    asset = PatientAsset.now(
        asset_id=asset_id,
        patient_id=patient_id,
        type=asset_type,
        original_filename=safe_name,
        path=str(destination),
        story_reference=story_reference,
    )
    ASSETS[asset_id] = asset
    return asset
