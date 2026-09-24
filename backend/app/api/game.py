"""
Game API
========
POST /api/game/start          — caregiver text prompt → grounded GameSession
POST /api/game/{session_id}/next      — advance to next beat
POST /api/game/{session_id}/speak     — patient audio → ASR → recognition result
POST /api/game/{session_id}/replay    — replay current beat
POST /api/game/{session_id}/reminder/acknowledge

The caregiver prompt drives story/beat selection via the GroundingAgent.
The patient's voice is stored as a raw interaction for later story comparison.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..models.game_session import GameSession, SessionStatus
from ..models.memory_graph import MemoryGraph, MemoryNode
from ..services.gameplay import GamePlayService, LibraryVideoProvider
from ..services.grounding import GroundingAgent
from ..services.phase1 import CARE_PLANS
from ..services.recognition import RecognitionService
from ..services.session_store import SESSION_STORE, finalise_session
from ..services.story_playback import StoryAgent

router = APIRouter(prefix="/api/game", tags=["game"])

_recognition = RecognitionService()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class StartRequest(BaseModel):
    patient_id: str
    prompt: str                     # caregiver text prompt
    story_id: str | None = None     # override: skip grounding, use this story
    narration_language: str = "en"
    video_job_id: str | None = None


class StartResponse(BaseModel):
    session_id: str
    patient_id: str
    story_id: str
    beat_id: str | None
    grounded: bool
    grounding_source: str
    reference_images: list[str]
    memory_graph_node: dict | None = None
    message: str = ""


class LanguageRequest(BaseModel):
    language: str


# ---------------------------------------------------------------------------
# POST /api/game/start
# ---------------------------------------------------------------------------

@router.post("/start", response_model=StartResponse)
def start_game(request: StartRequest):
    """
    Caregiver text prompt → GroundingAgent → GameSession.

    If grounding fails (no story match), returns 422 with a clarification
    message instead of inventing a scene.
    """
    # 1. Resolve prompt unless story_id is explicitly provided
    if request.story_id:
        story_id = request.story_id
        grounding_source = f"caregiver_override:story:{story_id}"
        reference_images: list[str] = []
        beat_id_hint: str | None = None
    else:
        result = GroundingAgent().resolve(request.prompt)
        if not result.match:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_grounded_story_match",
                    "reason": result.reason,
                    "message": (
                        "No patient story matches this prompt. "
                        "Please describe the memory more specifically, "
                        "or choose one of the five available stories."
                    ),
                },
            )
        plan = result.scene_plan
        story_id = plan.story_id
        grounding_source = plan.grounding_source
        reference_images = plan.reference_images
        beat_id_hint = plan.beat_id

    # 2. Create GameSession
    session_id = str(uuid.uuid4())
    session = GameSession(
        session_id=session_id,
        patient_id=request.patient_id,
        story_id=story_id,
        narration_language=request.narration_language,
    )

    SESSION_STORE[session_id] = session

    # 4. Build a MemoryGraph node for this session
    memory_node = MemoryNode(
        beat_id=beat_id_hint or "",
        story_id=story_id,
        patient_id=request.patient_id,
        grounding_source=grounding_source,
        reference_images=reference_images,
    ) if beat_id_hint else None

    # 5. If the frontend already created a grounded video job, attach it to this session
    if request.video_job_id:
        from ..models.video_job import VideoJobStatus
        from ..services.patient_library import VIDEO_JOBS
        job = VIDEO_JOBS.get(request.video_job_id)
        if job and job.story_id == story_id and job.scene_id == beat_id_hint:
            session.video_request_id = job.provider_job_id
            if job.status == VideoJobStatus.COMPLETED and job.output_url:
                session.video_status = "completed"
                session.video_url = job.output_url
                session.video_error = None

    # 6. Play the first beat immediately
    story_agent = StoryAgent(story_id)
    service = GamePlayService(
        session,
        story_agent,
        care_plan=CARE_PLANS.get(request.patient_id),
        video_provider=LibraryVideoProvider(),
    )
    first_beat = service.play_next()
    _hydrate_session_video_status(session)

    return StartResponse(
        session_id=session_id,
        patient_id=request.patient_id,
        story_id=story_id,
        beat_id=session.current_beat_id,
        grounded=bool(beat_id_hint),
        grounding_source=grounding_source,
        reference_images=reference_images,
        memory_graph_node=memory_node.model_dump(mode="json") if memory_node else None,
        message=f"Session started. {first_beat.get('narration', {}).get('text', '')}",
    )


# ---------------------------------------------------------------------------
# Compatible session-read / session-play routes used by the live frontend
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}")
def get_live_session(session_id: str):
    session = _get_session(session_id)
    _hydrate_session_video_status(session)
    if session.video_status != "completed" and not session.preview_url:
        session.preview_url = _preview_image_url_for_session(session)
    return session.model_dump(mode="json")


@router.post("/sessions/{session_id}/language")
def set_live_session_language(session_id: str, request: LanguageRequest):
    session = _get_session(session_id)
    language = request.language.lower()
    if language not in {"en", "hi", "te", "ta", "kn", "ml", "mr", "bn", "gu", "pa", "ur", "or", "as"}:
        raise HTTPException(status_code=422, detail="Unsupported narration language")

    session.narration_language = language
    if session.current_beat_id:
        from ..data.narrations import NARRATIONS
        from ..data.stories import get_story

        story = get_story(session.story_id)
        beat = next((item for item in story.beats if item.id == session.current_beat_id), None) if story else None
        narration_data = NARRATIONS.get(session.current_beat_id, {})
        narration_by_language = beat.narration_by_language if beat else {}
        narration_by_language = narration_by_language or {"en": beat.narration if beat else narration_data.get("opening", "")}
        session.narration_text = narration_by_language.get(language) or narration_by_language.get("en", "")
        question_by_language = narration_data.get("question_by_language", {})
        session.current_question = question_by_language.get(language) or question_by_language.get("en", "")

    SESSION_STORE[session_id] = session
    payload = session.model_dump(mode="json")
    payload["question_language"] = language if session.current_question and language in narration_data.get("question_by_language", {}) else "en"
    return payload


@router.post("/sessions/{session_id}/play")
def play_live_session_beat(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(
        session,
        story_agent,
        care_plan=CARE_PLANS.get(session.patient_id),
        video_provider=LibraryVideoProvider(),
    )
    result = service.play_next()
    SESSION_STORE[session_id] = session
    return result


@router.post("/sessions/{session_id}/replay")
def replay_live_session_beat(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(
        session,
        story_agent,
        care_plan=CARE_PLANS.get(session.patient_id),
        video_provider=LibraryVideoProvider(),
    )
    result = service.replay()
    SESSION_STORE[session_id] = session
    return result


@router.post("/sessions/{session_id}/end")
def end_live_session(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(
        session,
        story_agent,
        care_plan=CARE_PLANS.get(session.patient_id),
        video_provider=LibraryVideoProvider(),
    )

    from ..models.session_event import SessionEvent
    import json
    from pathlib import Path
    from ..services.session_store import PATIENT_LIBRARY_ROOT

    transcript_dir = PATIENT_LIBRARY_ROOT / session.patient_id / "sessions" / session_id / "transcripts"
    events: list[SessionEvent] = []
    if transcript_dir.is_dir():
        for file in sorted(transcript_dir.glob("*.json")):
            try:
                events.append(SessionEvent.model_validate(json.loads(file.read_text(encoding="utf-8"))))
            except Exception:
                pass

    report = finalise_session(
        session_id=session_id,
        patient_id=session.patient_id,
        patient_name=session.patient_id,
        stories_played=[session.story_id],
        events=events,
        started_at=session.started_at,
    )

    session.status = SessionStatus.COMPLETED
    session.progress["session_report_created"] = True
    session.story_progression["current_beat"] = session.current_beat_id
    session.story_progression["current_beat_sequence"] = session.current_beat_sequence
    session.caregiver_guidance = ["Care report ready"]
    service._refresh_progress_state()
    SESSION_STORE[session_id] = session

    return {
        "session_id": session_id,
        "status": "completed",
        "total_beats": report.total_beats,
        "spoken_responses": report.spoken_responses,
        "skipped_responses": report.skipped_responses,
        "supported_content": len(report.supported_content),
        "unsupported_content": len(report.unsupported_content),
        "memory_score": report.memory_score,
        "memory_score_label": report.memory_score_label,
        "report_path": report.report_path,
        "download_url": f"/api/game/sessions/{session_id}/report",
        "progress": session.progress,
        "story_progression": session.story_progression,
        "caregiver_guidance": session.caregiver_guidance,
    }


@router.get("/sessions/{session_id}/report")
def report_live_session(session_id: str):
    session = _get_session(session_id)
    from ..services.session_store import PATIENT_LIBRARY_ROOT

    session_dir = PATIENT_LIBRARY_ROOT / session.patient_id / "sessions" / session_id
    for ext in (".docx", ".txt"):
        candidates = list(session_dir.glob(f"*Story_Differences{ext}"))
        candidates += list(session_dir.glob(f"story_difference_report{ext}"))
        if candidates:
            path = candidates[0]
            media_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if ext == ".docx" else "text/plain"
            )
            return FileResponse(str(path), media_type=media_type, filename=path.name)

    raise HTTPException(status_code=404, detail="Report not yet generated. Call /end first.")


# ---------------------------------------------------------------------------
# POST /api/game/{session_id}/next
# ---------------------------------------------------------------------------

@router.post("/{session_id}/next")
def next_beat(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(session, story_agent, video_provider=LibraryVideoProvider())
    result = service.play_next()
    SESSION_STORE[session_id] = session
    return result


# ---------------------------------------------------------------------------
# POST /api/game/{session_id}/speak  — patient audio → recognition
# ---------------------------------------------------------------------------

@router.post("/{session_id}/speak")
async def patient_speaks(
    session_id: str,
    audio: UploadFile = File(...),
    language: str = "en",
):
    """
        Receives patient audio, transcribes it, and returns the raw transcript.
        The transcript is not scored during playback; the session report performs
        the later comparison against canonical patient evidence.
    """
    session = _get_session(session_id)
    if session.status != SessionStatus.WAITING_FOR_SPEECH:
        raise HTTPException(
            status_code=409,
            detail=f"Session is in state '{session.status}', not waiting for speech.",
        )
    if not session.current_beat_id:
        raise HTTPException(status_code=409, detail="No current beat to evaluate.")

    # ensure background previews remain available while provider work is still running
    if session.video_status in {"queued", "processing", "waiting", "pending_provider"}:
        preview_url = _preview_image_url_for_session(session)
        if preview_url:
            session.video_url = session.video_url or preview_url

    # Transcribe
    transcript = await _transcribe(audio, session_id, language)

    session.last_transcript = transcript
    session.last_recognition_outcome = None
    session.status = SessionStatus.READY
    session.progress["response_recorded"] = bool(transcript)
    session.story_progression["current_beat"] = session.current_beat_id
    session.story_progression["current_beat_sequence"] = session.current_beat_sequence
    session.caregiver_guidance = ["Next memory prompt", "Care report ready" if session.status == SessionStatus.COMPLETED else "Reminder due now" if session.care_reminder else "Next memory prompt"]

    SESSION_STORE[session_id] = session

    return {
        "session_id": session_id,
        "beat_id": session.current_beat_id,
        "transcript": transcript,
        "language": language,
        "outcome": None,
        "feedback": None,
        "next_action": "play_next",
        "progress": session.progress,
        "story_progression": session.story_progression,
        "caregiver_guidance": session.caregiver_guidance,
    }


# ---------------------------------------------------------------------------
# POST /api/game/{session_id}/replay
# ---------------------------------------------------------------------------

@router.post("/{session_id}/replay")
def replay_beat(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(session, story_agent, video_provider=LibraryVideoProvider())
    result = service.replay()
    SESSION_STORE[session_id] = session
    return result


# ---------------------------------------------------------------------------
# POST /api/game/{session_id}/reminder/acknowledge
# ---------------------------------------------------------------------------

@router.post("/{session_id}/reminder/acknowledge")
def acknowledge_reminder(session_id: str):
    session = _get_session(session_id)
    story_agent = StoryAgent(session.story_id)
    service = GamePlayService(session, story_agent, video_provider=LibraryVideoProvider())
    acknowledged = service.acknowledge_care_reminder()
    SESSION_STORE[session_id] = session
    return {"acknowledged": acknowledged, "session_id": session_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session(session_id: str) -> GameSession:
    session = SESSION_STORE.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _preview_image_url_for_session(session: GameSession) -> str | None:
    try:
        from ..data.stories import get_story
        from ..services.assets import STORY_IMAGE_ROOT

        story = get_story(session.story_id)
        if story is None or not session.current_beat_id:
            return None

        beat = next((item for item in story.beats if item.id == session.current_beat_id), None)
        if beat is None or not beat.image_path:
            return None

        image_path = (STORY_IMAGE_ROOT / beat.image_path).resolve()
        if image_path.exists():
            return "/story-images/" + image_path.relative_to(STORY_IMAGE_ROOT.resolve()).as_posix()
    except Exception:
        pass
    return None


def _hydrate_session_video_status(session: GameSession) -> None:
    """Refresh an active session from the matching Pixazo/video job and persist any completion URL."""
    if not session.current_beat_id:
        return

    try:
        from datetime import datetime, timezone

        from ..models.generation import GenerationJob, GenerationStatus
        from ..models.video_job import VideoJobStatus
        from ..services.patient_library import VIDEO_JOBS
        from ..services.pixazo import PixazoVideoService

        matches = [
            job for job in VIDEO_JOBS.values()
            if job.story_id == session.story_id and job.scene_id == session.current_beat_id
        ]
        if not matches:
            return

        exact_provider_match = [
            job for job in matches
            if session.video_request_id and job.provider_job_id == session.video_request_id
        ]
        completed_matches = [
            job for job in matches
            if job.status == VideoJobStatus.COMPLETED and (job.output_url or job.output_path)
        ]
        if completed_matches:
            matched_job = max(completed_matches, key=lambda job: (job.updated_at or datetime.min.replace(tzinfo=timezone.utc)))
        elif exact_provider_match:
            matched_job = max(exact_provider_match, key=lambda job: (job.updated_at or datetime.min.replace(tzinfo=timezone.utc)))
        else:
            matched_job = max(matches, key=lambda job: (job.updated_at or datetime.min.replace(tzinfo=timezone.utc)))

        if matched_job.status == VideoJobStatus.COMPLETED and (matched_job.output_url or matched_job.output_path):
            session.video_status = "completed"
            session.video_url = matched_job.output_url
            if not session.video_url and matched_job.output_path:
                from ..services.patient_library import PATIENT_LIBRARY_ROOT
                try:
                    relative = Path(matched_job.output_path).resolve().relative_to(PATIENT_LIBRARY_ROOT.resolve())
                    session.video_url = "/patient-library/" + relative.as_posix()
                except (OSError, ValueError):
                    session.video_url = None
            session.video_request_id = matched_job.provider_job_id or session.video_request_id
            session.video_error = None
            return

        if matched_job.provider_job_id:
            provider_job = GenerationJob(
                id=matched_job.job_id,
                beat_id=matched_job.scene_id,
                provider="pixazo",
                model="ltx-video",
                status=GenerationStatus.PENDING,
                request_id=matched_job.provider_job_id,
                prompt="Grounded memory scene",
            )
            refreshed = PixazoVideoService.get_status(provider_job)

            if refreshed.output_url:
                matched_job.status = VideoJobStatus.COMPLETED
                matched_job.output_url = refreshed.output_url
                matched_job.updated_at = datetime.now(timezone.utc)
                from ..services.patient_library import _save_index
                _save_index()
                session.video_status = "completed"
                session.video_url = refreshed.output_url
                session.video_request_id = matched_job.provider_job_id
                session.video_error = None
                return

            if refreshed.status in {GenerationStatus.QUEUED, GenerationStatus.PROCESSING}:
                matched_job.status = VideoJobStatus.PROCESSING if refreshed.status == GenerationStatus.PROCESSING else VideoJobStatus.QUEUED
                matched_job.updated_at = datetime.now(timezone.utc)
                from ..services.patient_library import _save_index
                _save_index()
                session.video_status = matched_job.status.value
                session.video_url = matched_job.output_url or session.video_url
                session.video_request_id = matched_job.provider_job_id or session.video_request_id
                return

            if refreshed.status == GenerationStatus.FAILED:
                matched_job.status = VideoJobStatus.FAILED
                matched_job.error = refreshed.error or "Video generation failed"
                matched_job.updated_at = datetime.now(timezone.utc)
                from ..services.patient_library import _save_index
                _save_index()
                session.video_status = "failed"
                session.video_request_id = matched_job.provider_job_id or session.video_request_id
                session.video_error = matched_job.error
                return

        if matched_job.status in {VideoJobStatus.WAITING, VideoJobStatus.QUEUED, VideoJobStatus.PROCESSING}:
            session.video_status = matched_job.status.value
            session.video_url = matched_job.output_url or session.video_url
            session.video_request_id = matched_job.provider_job_id or session.video_request_id
            return

        if matched_job.status == VideoJobStatus.FAILED:
            session.video_status = "failed"
            session.video_request_id = matched_job.provider_job_id or session.video_request_id
            session.video_error = matched_job.error or "Video generation failed"
    except Exception as exc:
        session.video_error = str(exc)
        session.video_status = session.video_status or "waiting"


async def _transcribe(audio: UploadFile, session_id: str, language: str) -> str:
    """
    Write upload to a temp file and run the Indic Conformer ASR.
    Falls back to an empty string if the model is unavailable.
    """
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        from ..services.asr_provider import IndicConformerASRProvider
        from pathlib import Path as _Path
        project_root = _Path(__file__).resolve().parents[3]
        provider = IndicConformerASRProvider(project_root)
        job = await provider.submit(tmp_path, session_id, language)
        result = await provider.get_result(job)
        return result.text
    except Exception:
        # ASR unavailable in this environment — return empty so caller can retry
        return ""
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
