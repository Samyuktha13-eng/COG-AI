import json
import re
import requests
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..models.asset import AssetType
from ..models.care_plan import CarePlan
from ..models.patient_folder import FolderAssetType
from ..models.video_job import VideoJob, VideoJobStatus
from ..models.recognition import SpeechTranscript
from ..models.session_event import SessionEvent
from ..services.gameplay import GamePlayService
from ..services.reminder_scheduler import CarePlanReminderScheduler
from ..services.story_playback import StoryAgent
from ..services.session_store import save_event, save_audio, finalise_session
from ..services.difference_engine import analyse_events
from ..services.patient_library import (
    BUILDS,
    VIDEO_JOBS,
    build_story,
    create_video_jobs,
    get_folder,
    _save_index,
    save_folder_asset,
    uploaded_story_supports_prompt,
)
from ..services.grounding import GroundingAgent
from ..services.phase1 import (
    ASSETS,
    CARE_PLANS,
    SPEECH_JOBS,
    SESSIONS,
    create_session,
    find_beat_for_prompt,
    patient_chapters,
    patient_profile,
    save_upload,
    story_catalog,
)
import uuid
from datetime import datetime, timezone
from ..models.speech_job import SpeechJob

router = APIRouter(prefix="/api", tags=["phase1"])


class SessionRequest(BaseModel):
    patient_id: str
    story_id: str | None = None
    prompt: str | None = None
    narration_language: str = "en"


class PromptRequest(BaseModel):
    patient_id: str
    story_id: str
    prompt: str


class TranscriptRequest(BaseModel):
    text: str
    language: str = "en"
    confidence: float | None = None


class SpeechCompletionRequest(BaseModel):
    text: str
    language: str = "en"
    confidence: float | None = None


class BuildRequest(BaseModel):
    force: bool = False


def classify_live_response(transcript: str) -> dict[str, str]:
    """Turn a spoken response into safe playback guidance, without judging memory accuracy."""
    text = " ".join(transcript.split()).strip()
    lowered = text.casefold()
    if not text:
        return {
            "response_kind": "uncertain",
            "next_action": "play_next",
            "guidance": "That is okay. We can continue with the next memory scene.",
        }
    if re.search(r"\b(repeat|again|replay|say that again)\b|"
                 r"(दोबारा|फिर से|మళ్లీ|మళ్ళీ|மீண்டும்|ಮತ್ತೆ|വീണ്ടും|पुन्हा|আবার)", lowered):
        return {
            "response_kind": "command",
            "next_action": "replay",
            "guidance": "I will replay this memory scene.",
        }
    if re.search(r"\b(finish|end|stop|done|that is all)\b|"
                 r"(समाप्त|खत्म|रोक दो|ముగించు|ఆపు|முடி|நிறுத்து|ಮುಗಿಸಿ|நಿಲ್ಲಿಸಿ|"
                 r"അവസാനിപ്പിക്കുക|നിർത്തുക|समाप्त करा|थांबा|শেষ করুন|থামুন)", lowered):
        return {
            "response_kind": "command",
            "next_action": "finish",
            "guidance": "I will finish this memory session and prepare the report.",
        }
    if re.search(r"\b(skip|next|continue|move on|don't remember|do not remember|not sure|forgot|can't remember)\b|"
                 r"(अगला|आगे बढ़ो|याद नहीं|पता नहीं|मुझे याद नहीं|తదుపరి|కొనసాగించు|గుర్తు లేదు|"
                 r"அடுத்த|தொடரவும்|நினைவில்லை|ಮುಂದಿನ|ಮುಂದುವರಿಸಿ|ನೆನಪಿಲ್ಲ|അടുത്ത|തുടരുക|ഓർമ്മയില്ല|"
                 r"पुढील|पुढे जा|आठवत नाही|পরের|চালিয়ে যান|মনে নেই)", lowered):
        return {
            "response_kind": "uncertain",
            "next_action": "play_next",
            "guidance": "That is okay. We will continue with the next memory scene.",
        }
    return {
        "response_kind": "response",
        "next_action": "play_next",
        "guidance": "Thank you. I recorded your response and will show the next memory scene.",
    }


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    patient = patient_profile(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/patient/{patient_id}/story")
def get_patient_story(patient_id: str):
    patient = patient_profile(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient": patient, "chapters": patient_chapters(), "stories": story_catalog()}


@router.get("/patients/{patient_id}/folder")
def get_patient_folder(patient_id: str):
    try:
        return get_folder(patient_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/patients/{patient_id}/folder/bundle")
async def upload_patient_bundle(
    patient_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] | None = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided for upload.")

    parsed_relative_paths: list[str] | None = None
    if relative_paths is not None:
        if len(relative_paths) == 1 and relative_paths[0].strip().startswith("["):
            try:
                parsed_relative_paths = json.loads(relative_paths[0])
            except json.JSONDecodeError:
                parsed_relative_paths = [relative_paths[0]]
        else:
            parsed_relative_paths = relative_paths

    if parsed_relative_paths is not None and len(parsed_relative_paths) != len(files):
        raise HTTPException(
            status_code=400,
            detail=f"relative_paths count ({len(parsed_relative_paths)}) must match uploaded files count ({len(files)})",
        )

    folder = get_folder(patient_id)
    folder.documents = []
    folder.image_assets = []
    folder.voice_story = None
    folder.document_text = {}

    assets = []
    try:
        for index, file in enumerate(files):
            filename = file.filename or f"bundle_{index}"
            suffix = Path(filename).suffix.lower()
            content_type = (file.content_type or "").lower()
            if content_type.startswith("audio/") or suffix in {".wav", ".mp3", ".m4a", ".webm", ".ogg"}:
                asset_type = FolderAssetType.VOICE_STORY
            elif suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
                asset_type = FolderAssetType.IMAGE
            else:
                asset_type = FolderAssetType.STORY_DOCUMENT

            raw_relative = parsed_relative_paths[index] if parsed_relative_paths else file.filename
            relative_path = str(raw_relative) if raw_relative is not None else file.filename
            assets.append(
                save_folder_asset(
                    patient_id,
                    asset_type,
                    filename,
                    await file.read(),
                    relative_path=relative_path,
                )
            )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return assets


@router.post("/patients/{patient_id}/folder/story-document")
async def upload_story_document(patient_id: str, document: UploadFile = File(...), story_reference: str | None = None):
    try:
        return save_folder_asset(
            patient_id,
            FolderAssetType.STORY_DOCUMENT,
            document.filename or "story-document",
            await document.read(),
            story_reference=story_reference,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/patients/{patient_id}/folder/images")
async def upload_story_images(
    patient_id: str,
    images: list[UploadFile] = File(...),
    relative_paths: list[str] | None = Form(None),
):
    parsed_relative_paths: list[str] | None = None
    if relative_paths is not None:
        if len(relative_paths) == 1 and relative_paths[0].strip().startswith("["):
            try:
                parsed_relative_paths = json.loads(relative_paths[0])
            except json.JSONDecodeError:
                parsed_relative_paths = [relative_paths[0]]
        else:
            parsed_relative_paths = relative_paths

    if parsed_relative_paths is not None and len(parsed_relative_paths) != len(images):
        raise HTTPException(
            status_code=400,
            detail=f"relative_paths count ({len(parsed_relative_paths)}) must match uploaded files count ({len(images)})",
        )

    assets = []
    try:
        for index, image in enumerate(images):
            raw_relative = parsed_relative_paths[index] if parsed_relative_paths else image.filename
            relative_path = str(raw_relative) if raw_relative is not None else image.filename
            assets.append(save_folder_asset(
                patient_id,
                FolderAssetType.IMAGE,
                image.filename or "image",
                await image.read(),
                relative_path=relative_path,
            ))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return assets


@router.post("/patients/{patient_id}/folder/voice")
async def upload_story_voice(patient_id: str, audio: UploadFile = File(...)):
    try:
        asset = save_folder_asset(
            patient_id,
            FolderAssetType.VOICE_STORY,
            audio.filename or "story-recording.wav",
            await audio.read(),
        )
        return {"asset": asset, "transcript_status": "queued"}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/patients/{patient_id}/story/build")
def build_patient_story(patient_id: str, request: BuildRequest | None = None):
    try:
        return build_story(patient_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/patients/{patient_id}/story/build-status")
def get_story_build_status(patient_id: str):
    try:
        folder = get_folder(patient_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    build = BUILDS.get(folder.build_id) if folder.build_id else None
    return build or {"status": "not_built", "patient_id": patient_id}


@router.post("/patients/{patient_id}/videos/generate")
def generate_patient_videos(patient_id: str, request: dict | None = None):
    try:
        if request and request.get("prompt"):
            from ..services.grounding import GroundingAgent
            from ..services.assets import STORY_IMAGE_ROOT, StoryAssetService
            from ..services.pixazo import PixazoVideoService
            from ..data.stories import get_story
            from ..models.video_job import VideoJobStatus
            from ..services.patient_library import create_video_job_for_beat, VIDEO_JOBS, _save_index

            result = GroundingAgent().resolve(str(request["prompt"]))
            if not result.match or result.scene_plan is None:
                raise HTTPException(status_code=422, detail={
                    "error": "no_grounded_story_match",
                    "reason": result.reason,
                    "prompt": request.get("prompt"),
                })

            story = get_story(result.scene_plan.story_id)
            if story is None:
                raise HTTPException(status_code=500, detail="Grounded story not found in registry")
            beat = next((item for item in story.beats if item.id == result.scene_plan.beat_id), None)
            if beat is None:
                raise HTTPException(status_code=500, detail="Grounded beat not found in the story registry")

            image_path = (STORY_IMAGE_ROOT / beat.image_path).resolve()
            image_path.relative_to(STORY_IMAGE_ROOT.resolve())
            if not image_path.is_file():
                raise HTTPException(status_code=404, detail="Source image file not found")

            asset_service = StoryAssetService()
            image_url = asset_service.publish_image(image_path)
            asset_service.validate_public_image_url(image_url)

            job = create_video_job_for_beat(
                patient_id,
                result.scene_plan.story_id,
                result.scene_plan.beat_id,
                result.scene_plan.reference_images,
            )

            pixazo_job = PixazoVideoService().submit(
                beat_id=beat.id,
                image_url=image_url,
                prompt=result.scene_plan.video_prompt,
                duration=6,
                image_strength=beat.image_strength,
                guidance_scale=beat.guidance_scale,
                enable_prompt_expansion=beat.enable_prompt_expansion,
                num_frames=beat.num_frames,
                frames_per_second=beat.frames_per_second,
            )
            job.provider_job_id = pixazo_job.request_id
            job.status = VideoJobStatus.PROCESSING
            VIDEO_JOBS[job.job_id] = job
            _save_index()
            return [job]

        return create_video_jobs(patient_id)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"Pixazo submission failed: {detail}") from error


@router.get("/patients/{patient_id}/videos")
def list_patient_videos(patient_id: str):
    return [job for job in VIDEO_JOBS.values() if job.patient_id == patient_id]


@router.get("/patients/{patient_id}/videos/status")
def patient_video_status(patient_id: str):
    jobs = [job for job in VIDEO_JOBS.values() if job.patient_id == patient_id]
    counts = {status.value: 0 for status in VideoJobStatus}
    for job in jobs:
        counts[job.status.value] += 1
    return {
        "status": "completed" if jobs and counts.get("completed", 0) == len(jobs) else "processing" if jobs else "not_started",
        "total": len(jobs),
        "completed": counts.get("completed", 0),
        "processing": counts.get("processing", 0),
        "waiting": counts.get("waiting", 0) + counts.get("queued", 0),
        "failed": counts.get("failed", 0),
    }


@router.post("/assets/{patient_id}/image")
async def upload_image(patient_id: str, image: UploadFile = File(...), story_reference: str | None = None):
    try:
        return save_upload(patient_id, AssetType.IMAGE, image.filename or "image", await image.read(), story_reference)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/assets/{patient_id}/voice")
async def upload_voice(patient_id: str, audio: UploadFile = File(...)):
    try:
        asset = save_upload(patient_id, AssetType.VOICE, audio.filename or "voice", await audio.read())
        return {"asset": asset, "status": "received", "transcription_status": "pending"}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/assets/{patient_id}")
def list_assets(patient_id: str):
    return [asset for asset in ASSETS.values() if asset.patient_id == patient_id]


@router.post("/story/resolve")
def resolve_prompt(request: PromptRequest):
    patient = patient_profile(request.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    beat = find_beat_for_prompt(request.story_id, request.prompt)
    if beat is None:
        raise HTTPException(status_code=404, detail="No matching story beat found")
    return {
        "story_id": request.story_id,
        "beat_id": beat.id,
        "action": beat.action,
        "motion_sequence": beat.motion_sequence,
        "narration": beat.narration,
        "image_path": beat.image_path,
    }


@router.post("/game/sessions")
def start_session(request: SessionRequest):
    try:
        story_id = request.story_id
        if story_id is None and request.prompt:
            folder = get_folder(request.patient_id)
            if folder.story_status != "ready" or not folder.documents:
                raise HTTPException(
                    status_code=409,
                    detail="Upload patient story documents and build the story before starting from a prompt",
                )
            result = GroundingAgent().resolve(request.prompt)
            if not result.match or result.scene_plan is None:
                raise HTTPException(status_code=422, detail={
                    "error": "no_grounded_story_match",
                    "reason": result.reason,
                })
            if not uploaded_story_supports_prompt(folder, request.prompt, result.scene_plan.story_id):
                raise HTTPException(status_code=422, detail={
                    "error": "prompt_not_found_in_uploaded_patient_story",
                    "reason": "no_uploaded_story_evidence_match",
                })
            story_id = result.scene_plan.story_id
        if story_id is None:
            raise HTTPException(status_code=422, detail="Provide story_id or prompt")
        session = create_session(request.patient_id, story_id)
        session.narration_language = request.narration_language
        return session
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/patients/{patient_id}/care-plan/reminders/due")
def get_due_care_reminders(patient_id: str, now: str | None = None, window_minutes: int = 0):
    if patient_profile(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    care_plan = CARE_PLANS.get(patient_id)
    if care_plan is None:
        care_plan = CarePlan(patient_id=patient_id)
        CARE_PLANS[patient_id] = care_plan

    parsed_now = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    scheduler = CarePlanReminderScheduler(care_plan)
    due = scheduler.trigger_due(parsed_now, window_minutes=window_minutes or 0)
    if not due:
        due = scheduler.due_at(parsed_now)
    next_reminder = scheduler.next_due(parsed_now)
    next_action = due[0].task if due else (next_reminder.task if next_reminder else "No reminder is due at this time.")
    return {
        "patient_id": patient_id,
        "timestamp": parsed_now.isoformat(),
        "count": len(due),
        "due_reminders": [item.model_dump(mode="json") for item in due],
        "next_reminder": next_reminder.model_dump(mode="json") if next_reminder else None,
        "next_action": next_action,
    }


@router.post("/patients/{patient_id}/care-plan/reminders/videos/prewarm")
def prewarm_reminder_videos(patient_id: str, now: str | None = None, lead_minutes: int = 15):
    """Request reminder clips early enough for the scheduled care cue."""
    if patient_profile(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    care_plan = CARE_PLANS.get(patient_id) or CarePlan(patient_id=patient_id)
    CARE_PLANS[patient_id] = care_plan
    parsed_now = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    reminders = CarePlanReminderScheduler(care_plan).upcoming_within(parsed_now, max(1, min(lead_minutes, 120)))
    results: list[dict] = []

    from ..services.assets import STORY_IMAGE_ROOT, StoryAssetService
    from ..services.pixazo import PixazoVideoService

    asset_service = StoryAssetService()
    reminder_actions = {
        "medicine": "The person picks up the medicine with one hand, brings it calmly toward the mouth with water, completes the action, and rests both hands naturally.",
        "water": "The person picks up the glass, slowly drinks the water, lowers the glass, and places it back on the table.",
        "breakfast": "The person calmly lifts one bite of breakfast, eats it, lowers the hand, and settles into a relaxed seated pose.",
        "lunch": "The person calmly lifts one bite of lunch, eats it, lowers the hand, and settles into a relaxed seated pose.",
        "appointment": "The person calmly picks up the appointment bag, stands, takes one careful step toward the exit, and stops in a ready-to-leave pose.",
        "walk": "The person takes a few slow, steady walking steps along the path, then stops naturally and faces forward.",
        "family_call": "The person picks up the phone, brings it to the ear, smiles gently as if listening, and holds the completed call pose.",
        "bedtime": "The person slowly lies down, pulls the blanket into place, closes the eyes, and becomes still in a comfortable sleeping pose.",
        "morning": "The person slowly sits up, stretches gently once, and settles into an awake seated pose.",
        "family_meal": "The person calmly lifts one bite of the meal, eats it, lowers the hand, and settles into a relaxed seated pose.",
        "gardening": "The person gently waters one plant, lowers the watering can, and pauses beside the plant in a completed gardening pose.",
        "get_ready": "The person calmly adjusts one item of clothing, picks up the bag, and finishes in a ready-to-leave standing pose.",
    }
    def reminder_image_path(reminder):
        standard = STORY_IMAGE_ROOT / "reminders" / f"reminder_{reminder.reminder_type}.jpg"
        if standard.is_file():
            return standard
        task = reminder.task.casefold()
        reminder_fallbacks = (
            (("family", "talk", "call"), "family_call"),
            (("meal", "food", "lunch", "breakfast"), "family_meal"),
            (("walk", "outside"), "walk"),
            (("garden", "plant", "flowers"), "gardening"),
            (("sleep", "bed"), "bedtime"),
        )
        for keywords, reminder_type in reminder_fallbacks:
            if any(keyword in task for keyword in keywords):
                return STORY_IMAGE_ROOT / f"reminders/reminder_{reminder_type}.jpg"
        return STORY_IMAGE_ROOT / "reminders/reminder_morning.jpg"

    for reminder in reminders:
        existing = next(
            (
                job for job in VIDEO_JOBS.values()
                if job.patient_id == patient_id
                and job.story_id == "care_reminders"
                and job.scene_id == reminder.reminder_id
                and job.status not in {VideoJobStatus.FAILED}
            ),
            None,
        )
        if existing:
            results.append(existing.model_dump(mode="json"))
            continue

        image_path = reminder_image_path(reminder)
        if not image_path.is_file():
            results.append({"reminder_id": reminder.reminder_id, "status": "missing_asset", "task": reminder.task})
            continue

        try:
            image_url = asset_service.publish_image(image_path)
            asset_service.validate_public_image_url(image_url)
            provider_job = PixazoVideoService().submit(
                beat_id=f"reminder_{reminder.reminder_id}",
                image_url=image_url,
                prompt=(
                    f"Create a clear healthcare reminder video for {reminder.task}. "
                    f"Starting from the exact reminder image, perform only this one complete action: "
                    f"{reminder_actions.get(reminder.reminder_type, 'The person performs one slow, clear reminder action and finishes in a calm still pose.')} "
                    "Use one continuous shot with a locked camera and a clear beginning, middle, and ending. "
                    "Keep the exact person, objects, layout, lighting, and reminder meaning from the image. "
                    "Do not combine actions, add people, change locations, or stop before the action is complete."
                ),
                duration=4,
                image_strength=0.95,
                guidance_scale=1.0,
                num_frames=72,
                frames_per_second=18,
            )
            job = VideoJob(
                job_id=str(uuid.uuid4()),
                patient_id=patient_id,
                story_id="care_reminders",
                scene_id=reminder.reminder_id,
                status=VideoJobStatus.PROCESSING,
                provider_job_id=provider_job.request_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            VIDEO_JOBS[job.job_id] = job
            _save_index()
            results.append(job.model_dump(mode="json"))
        except Exception as error:
            results.append({"reminder_id": reminder.reminder_id, "status": "not_started", "error": str(error)})

    return {
        "patient_id": patient_id,
        "timestamp": parsed_now.isoformat(),
        "lead_minutes": lead_minutes,
        "scheduled": results,
    }


@router.put("/patients/{patient_id}/care-plan")
def set_care_plan(patient_id: str, care_plan: CarePlan):
    if patient_profile(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if care_plan.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="Care plan patient_id does not match route")
    CARE_PLANS[patient_id] = care_plan
    return care_plan


@router.get("/game/sessions/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        from .game import _hydrate_session_video_status
        _hydrate_session_video_status(session)
    except Exception:
        pass
    return session


@router.post("/game/sessions/{session_id}/play")
def play_session_beat(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        result = GamePlayService(
            session,
            StoryAgent(session.story_id),
            CARE_PLANS.get(session.patient_id),
        ).play_next()
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return result


@router.post("/game/sessions/{session_id}/recognition")
def submit_recognition(session_id: str, request: TranscriptRequest):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        return GamePlayService(
            session,
            StoryAgent(session.story_id),
            CARE_PLANS.get(session.patient_id),
        ).submit_transcript(SpeechTranscript(**request.model_dump()))
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/game/sessions/{session_id}/recognition/audio")
async def submit_recognition_audio(session_id: str, audio: UploadFile = File(...)):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        asset = save_upload(session.patient_id, AssetType.VOICE, audio.filename or "recognition.wav", await audio.read())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    job = SpeechJob(job_id=str(uuid.uuid4()), session_id=session_id, asset_id=asset.asset_id)
    SPEECH_JOBS[job.job_id] = job
    return job


@router.get("/speech/jobs/{job_id}")
def get_speech_job(job_id: str):
    job = SPEECH_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Speech job not found")
    return job


@router.post("/speech/jobs/{job_id}/complete")
def complete_speech_job(job_id: str, request: SpeechCompletionRequest):
    job = SPEECH_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Speech job not found")
    job.status = "completed"
    job.transcript = request.text
    job.language = request.language
    job.confidence = request.confidence
    return job


@router.post("/game/sessions/{session_id}/replay")
def replay_session_beat(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        return GamePlayService(
            session,
            StoryAgent(session.story_id),
            CARE_PLANS.get(session.patient_id),
        ).replay()
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/game/sessions/{session_id}/care-reminder/acknowledge")
def acknowledge_care_reminder(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    acknowledged = GamePlayService(
        session,
        StoryAgent(session.story_id),
        CARE_PLANS.get(session.patient_id),
    ).acknowledge_care_reminder()
    return {"acknowledged": acknowledged, "session_id": session_id}


# ---------------------------------------------------------------------------
# Interaction endpoints  (speak / skip / end session / report)
# ---------------------------------------------------------------------------

class InteractionRequest(BaseModel):
    beat_id: str
    beat_sequence: int
    question: str
    spoken: bool
    transcript: str | None = None
    transcript_language: str = "en"
    asr_confidence: float | None = None
    audio_path: str | None = None


@router.post("/game/sessions/{session_id}/interaction")
async def record_interaction(
    session_id: str,
    request: InteractionRequest,
):
    """Store one beat interaction (speak or skip). No right/wrong feedback."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")

    now = datetime.now(timezone.utc)

    event = SessionEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        patient_id=session.patient_id,
        story_id=session.story_id,
        beat_id=request.beat_id,
        sequence=request.beat_sequence,
        question=request.question,
        question_language=request.transcript_language,
        spoken=request.spoken,
        audio_path=request.audio_path,
        transcript=request.transcript,
        transcript_language=request.transcript_language if request.spoken else None,
        asr_confidence=request.asr_confidence,
        started_at=now,
        completed_at=now,
    )
    save_event(event)
    session.event_ids.append(event.event_id)
    session.last_transcript = request.transcript
    session.progress["response_recorded"] = bool(request.transcript or request.spoken)
    session.story_progression["current_beat"] = request.beat_id
    session.story_progression["current_beat_sequence"] = request.beat_sequence
    session.caregiver_guidance = ["Next memory prompt"]

    supported, unsupported = analyse_events([event])
    score = 100 if supported else 0 if unsupported else None
    return {
        "event_id": event.event_id,
        "stored": True,
        "score": score,
        "score_label": "Story match" if supported else "Different or unclear response" if unsupported else "Not scored",
    }


# In-memory event store keyed by event_id (session events are also on disk)
_SESSION_EVENTS: dict[str, list[SessionEvent]] = {}


@router.post("/game/sessions/{session_id}/interaction/audio")
async def record_interaction_audio(
    session_id: str,
    beat_id: str = Form(...),
    beat_sequence: int = Form(...),
    question: str = Form(...),
    transcript: str | None = Form(default=None),
    transcript_language: str = Form(default="en"),
    asr_confidence: float | None = Form(default=None),
    audio: UploadFile = File(...),
):
    """Multipart form version: audio file + metadata in one request."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")

    data = await audio.read()
    audio_path = save_audio(session.patient_id, session_id, beat_id, beat_sequence, data) if data else None
    await audio.seek(0)
    try:
        from .voice import _run_asr
        transcript = transcript or await _run_asr(audio, session_id, transcript_language)
    except Exception:
        transcript = transcript or ""
    response = classify_live_response(transcript)
    now = datetime.now(timezone.utc)

    event = SessionEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        patient_id=session.patient_id,
        story_id=session.story_id,
        beat_id=beat_id,
        sequence=beat_sequence,
        question=question,
        question_language=transcript_language,
        spoken=True,
        audio_path=audio_path,
        transcript=transcript,
        transcript_language=transcript_language,
        asr_confidence=asr_confidence,
        response_kind=response["response_kind"],
        started_at=now,
        completed_at=now,
    )
    supported, unsupported = analyse_events([event])
    response["match_status"] = "matched" if supported else "unmatched" if unsupported else "unscored"
    response["feedback_emoji"] = "✅" if supported else "🤔" if unsupported else "💬"
    response["score"] = 100 if supported else 0 if unsupported else None
    response["score_label"] = (
        "Story match" if supported else
        "Different or unclear response" if unsupported else
        "Not scored"
    )
    save_event(event)
    session.event_ids.append(event.event_id)
    session.last_transcript = transcript
    session.progress["response_recorded"] = bool(transcript)
    session.story_progression["current_beat"] = beat_id
    session.story_progression["current_beat_sequence"] = beat_sequence
    session.caregiver_guidance = [response["guidance"]]
    return {
        "event_id": event.event_id,
        "stored": True,
        "transcript": transcript,
        **response,
    }


@router.post("/game/sessions/{session_id}/end")
def end_session(session_id: str):
    """Finalise session: write session_transcript.json + story_difference_report.docx."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")

    from ..services.session_store import PATIENT_LIBRARY_ROOT
    import json
    from pathlib import Path

    # Reload events from disk for this session
    transcript_dir = (
        PATIENT_LIBRARY_ROOT / session.patient_id / "sessions" / session_id / "transcripts"
    )
    events: list[SessionEvent] = []
    if transcript_dir.is_dir():
        for f in sorted(transcript_dir.glob("*.json")):
            try:
                events.append(SessionEvent.model_validate(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass

    patient = patient_profile(session.patient_id)
    patient_name = patient.name if patient else session.patient_id

    report = finalise_session(
        session_id=session_id,
        patient_id=session.patient_id,
        patient_name=patient_name,
        stories_played=[session.story_id],
        events=events,
        started_at=session.started_at,
    )

    from ..models.game_session import SessionStatus
    session.status = SessionStatus.COMPLETED
    session.progress["session_report_created"] = True
    session.story_progression["current_beat"] = session.current_beat_id
    session.story_progression["current_beat_sequence"] = session.current_beat_sequence
    session.caregiver_guidance = ["Care report ready"]

    return {
        "session_id": session_id,
        "status": "completed",
        "total_beats": report.total_beats,
        "spoken_responses": report.spoken_responses,
        "skipped_responses": report.skipped_responses,
        "supported_content": len(report.supported_content),
        "unsupported_content": len(report.unsupported_content),
        "report_path": report.report_path,
        "download_url": f"/api/game/sessions/{session_id}/report",
        "progress": session.progress,
        "story_progression": session.story_progression,
        "caregiver_guidance": session.caregiver_guidance,
    }


@router.get("/game/sessions/{session_id}/report")
def download_report(session_id: str):
    """Download the story difference report (.docx or .txt fallback)."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")

    from ..services.session_store import PATIENT_LIBRARY_ROOT
    from pathlib import Path

    session_dir = PATIENT_LIBRARY_ROOT / session.patient_id / "sessions" / session_id
    for ext in (".docx", ".txt"):
        candidates = list(session_dir.glob(f"*Story_Differences{ext}"))
        candidates += list(session_dir.glob(f"story_difference_report{ext}"))
        if candidates:
            path = candidates[0]
            media = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if ext == ".docx" else "text/plain"
            )
            return FileResponse(str(path), media_type=media, filename=path.name)

    raise HTTPException(status_code=404, detail="Report not yet generated. Call /end first.")
