from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException

from ..data.stories import get_story
from ..models.generation import GenerationJob
from ..services.assets import (
    AssetPublishError,
    STORY_IMAGE_ROOT,
    StoryAssetService,
    UnsupportedAssetError,
)
from ..services.pixazo import PixazoVideoService

JOBS: dict[str, GenerationJob] = {}

router = APIRouter(
    prefix="/api/generation",
    tags=["generation"],
)


def _normalize_motion_sequence(beat) -> list[str]:
    raw_sequence = getattr(beat, "motion_sequence", None) or []
    cleaned = [str(step).strip() for step in raw_sequence if str(step).strip()]
    if cleaned:
        return cleaned
    if getattr(beat, "motion", None):
        return [str(beat.motion).strip()]
    return ["The subject performs the described action continuously and naturally."]


def _build_motion_prompt(beat) -> str:
    motion_steps = _normalize_motion_sequence(beat)
    step_block = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(motion_steps, start=1)
    )
    constraints = getattr(beat, "motion_constraints", None) or []
    constraint_block = "\n".join(f"No {constraint.strip()}." for constraint in constraints if constraint.strip())
    constraint_text = f"{constraint_block}\n" if constraint_block else ""

    return (
        "Starting from the exact reference image, create a sharp, clear, well-lit video with the motion unfolding in a single continuous sequence.\n\n"
        "Perform the action continuously and in the correct natural order:\n\n"
        f"{step_block}\n\n"
        "Each action must finish before the next action begins.\n"
        "Movement must be smooth, physically plausible and continuous.\n"
        "Keep the subject and all important objects in sharp focus throughout.\n"
        "Maintain consistent character identity, body proportions, clothing,\n"
        "objects, environment, lighting and spatial relationships throughout.\n\n"
        "Do not jump between moments.\n"
        "Do not teleport objects or body parts.\n"
        "Do not create intermediate events that were not described.\n"
        "Do not reverse direction unexpectedly.\n"
        "Do not morph the character or background.\n"
        "Do not introduce new people or objects.\n"
        "Do not create scene transitions.\n\n"
        "The final frame should be a natural continuation of the described action.\n\n"
        f"Reference context: {beat.action}. {beat.motion}. {beat.camera}.\n"
        "Preserve the exact character identity, face, clothing, objects,\n"
        "architecture, lighting and composition from the reference image.\n"
        "No teleportation. No sudden pose changes. No instantaneous movement.\n"
        "No duplicated limbs. No body morphing. No face morphing.\n"
        "No background morphing. No scene transition. No new objects.\n"
        "No additional people. No camera shake. No random camera movement.\n"
        "No time jumps. No accelerated action.\n"
        f"{constraint_text}"
        "No change of viewpoint."
    )


def _motion_prompt(beat) -> str:
    """Build a grounded video prompt via the GroundingAgent when possible."""
    try:
        from ..services.grounding import GroundingAgent
        from ..models.grounding import ScenePlan
        from ..services.assets import STORY_IMAGE_ROOT
        agent = GroundingAgent()
        images = agent.select_reference_images(beat.story_id, beat)
        plan = ScenePlan(
            story_id=beat.story_id,
            beat_id=beat.id,
            action=beat.action,
            motion_sequence=beat.motion_sequence,
            constraints=[f"No {c}" for c in (beat.motion_constraints or [])],
            reference_images=images,
            grounding_source=f"story:{beat.story_id}/beat:{beat.id}",
        )
        return agent.compose_video_prompt(plan, beat)
    except Exception:
        return _build_motion_prompt(beat)


@router.post("/story/{story_id}/beat/{beat_id}")
def generate_beat(
    story_id: str,
    beat_id: str,
):
    story = get_story(story_id)

    if story is None:
        raise HTTPException(
            status_code=404,
            detail="Story not found",
        )

    beat = next(
        (b for b in story.beats if b.id == beat_id),
        None,
    )

    if beat is None:
        raise HTTPException(
            status_code=404,
            detail="Beat not found",
        )

    if not beat.image_path:
        raise HTTPException(
            status_code=400,
            detail="Beat has no source image.",
        )

    return {
        "status": "ready_for_generation",
        "story_id": story_id,
        "beat_id": beat_id,
        "image_path": beat.image_path,
        "prompt": _motion_prompt(beat),
    }

@router.get("/status/{request_id}")
def get_generation_status(request_id: str):
    job = JOBS.get(request_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found.")

    try:
        job = PixazoVideoService.get_status(job)
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"Pixazo status check failed: {detail}") from error

    JOBS[request_id] = job
    return job


@router.post("/story/{story_id}/beat/{beat_id}/submit")
def submit_beat(story_id: str, beat_id: str):
    story = get_story(story_id)

    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    beat = next((item for item in story.beats if item.id == beat_id), None)
    if beat is None:
        raise HTTPException(status_code=404, detail="Beat not found")
    if not beat.image_path:
        raise HTTPException(status_code=400, detail="Beat has no source image.")

    image_path = STORY_IMAGE_ROOT / beat.image_path
    try:
        image_path = image_path.resolve()
        image_path.relative_to(STORY_IMAGE_ROOT.resolve())
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid source image path.") from error

    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Source image file not found.")

    try:
        asset_service = StoryAssetService()
        image_url = asset_service.publish_image(image_path)
        asset_service.validate_public_image_url(image_url)

        end_image_url = None
        if beat.end_image_path:
            end_image_path = (STORY_IMAGE_ROOT / beat.end_image_path).resolve()
            end_image_path.relative_to(STORY_IMAGE_ROOT.resolve())
            end_image_url = asset_service.publish_image(end_image_path)
            asset_service.validate_public_image_url(end_image_url)

        job = PixazoVideoService().submit(
            beat_id=beat.id,
            image_url=image_url,
            prompt=_motion_prompt(beat),
            duration=max(4, round(beat.duration)),
            image_strength=float(beat.image_strength or 1.0),
            guidance_scale=float(beat.guidance_scale or 1.0),
            enable_prompt_expansion=False,
            num_frames=min(96, int(beat.num_frames or 72)),
            frames_per_second=min(18, int(beat.frames_per_second or 18)),
            end_image_url=end_image_url,
        )
    except UnsupportedAssetError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AssetPublishError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"Pixazo submission failed: {detail}") from error

    JOBS[job.request_id] = job

    return {
        "status": job.status,
        "story_id": story_id,
        "beat_id": beat_id,
        "request_id": job.request_id,
        "polling_url": f"https://gateway.pixazo.ai/v2/requests/status/{job.request_id}",
        "image_path": beat.image_path,
        "prompt": job.prompt,
    }
