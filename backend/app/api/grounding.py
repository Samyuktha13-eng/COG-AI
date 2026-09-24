"""
Grounding API
=============
POST /api/grounding/resolve   — resolve a caregiver prompt to a ScenePlan (dry-run)
POST /api/grounding/generate  — resolve + create VideoJob + submit to Pixazo
"""
from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.grounding import GroundingResult
from ..services.grounding import GroundingAgent

router = APIRouter(prefix="/api/grounding", tags=["grounding"])


class GroundingRequest(BaseModel):
    patient_id: str
    prompt: str


class GenerateRequest(BaseModel):
    patient_id: str
    prompt: str


@router.post("/resolve", response_model=GroundingResult)
def resolve_prompt(request: GroundingRequest) -> GroundingResult:
    """
    Resolve a caregiver prompt to a grounded ScenePlan without generating anything.
    Returns match=False with a reason if no story beat can be found.
    """
    result = GroundingAgent().resolve(request.prompt)
    if not result.match:
        # Still 200 — the caller decides what to do with a no-match
        return result
    return result


@router.post("/generate")
def grounded_generate(request: GenerateRequest):
    """
    Full pipeline:
      1. Resolve prompt → ScenePlan
      2. Create a VideoJob for the matched beat
      3. Submit to Pixazo using the grounded video prompt
      4. Return the job + scene plan
    """
    from ..services.patient_library import create_video_job_for_beat, VIDEO_JOBS, _save_index
    from ..services.assets import STORY_IMAGE_ROOT, StoryAssetService, AssetPublishError, UnsupportedAssetError
    from ..services.pixazo import PixazoVideoService
    from ..data.stories import get_story
    from .generation import _motion_prompt

    result = GroundingAgent().resolve(request.prompt)
    if not result.match:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_grounded_story_match",
                "reason": result.reason,
                "prompt": request.prompt,
                "message": "No patient story matches this prompt. Please clarify the memory you want to show.",
            },
        )

    plan = result.scene_plan
    story = get_story(plan.story_id)
    if story is None:
        raise HTTPException(status_code=500, detail="Grounded story not found in registry")
    if not next((beat for beat in story.beats if beat.id == plan.beat_id), None):
        raise HTTPException(status_code=500, detail="Grounded beat not found in story registry")

    beats = sorted(story.beats, key=lambda item: item.sequence)
    generated_jobs = []
    try:
        asset_service = StoryAssetService()
        video_service = PixazoVideoService()
        from ..models.video_job import VideoJobStatus

        for scene_beat in beats:
            existing_job = next(
                (
                    item for item in VIDEO_JOBS.values()
                    if item.patient_id == request.patient_id
                    and item.story_id == plan.story_id
                    and item.scene_id == scene_beat.id
                    and item.provider_job_id
                    and item.status in {VideoJobStatus.WAITING, VideoJobStatus.QUEUED, VideoJobStatus.PROCESSING}
                ),
                None,
            )
            if existing_job:
                generated_jobs.append(existing_job)
                continue

            image_path = (STORY_IMAGE_ROOT / scene_beat.image_path).resolve()
            try:
                image_path.relative_to(STORY_IMAGE_ROOT.resolve())
            except ValueError as error:
                raise HTTPException(status_code=400, detail="Invalid source image path") from error
            if not image_path.is_file():
                raise HTTPException(status_code=404, detail="Source image file not found")

            job = create_video_job_for_beat(
                request.patient_id,
                plan.story_id,
                scene_beat.id,
                plan.reference_images if scene_beat.id == plan.beat_id else [],
            )
            image_url = asset_service.publish_image(image_path)
            asset_service.validate_public_image_url(image_url)
            scene_prompt = plan.video_prompt if scene_beat.id == plan.beat_id else _motion_prompt(scene_beat)
            pixazo_job = video_service.submit(
                beat_id=scene_beat.id,
                image_url=image_url,
                prompt=scene_prompt,
                duration=max(4, round(scene_beat.duration)),
                image_strength=float(scene_beat.image_strength or 1.0),
                guidance_scale=float(scene_beat.guidance_scale or 1.0),
                enable_prompt_expansion=False,
                num_frames=min(96, int(scene_beat.num_frames or 72)),
                frames_per_second=min(18, int(scene_beat.frames_per_second or 18)),
            )
            job.provider_job_id = pixazo_job.request_id
            job.status = VideoJobStatus.PROCESSING
            VIDEO_JOBS[job.job_id] = job
            generated_jobs.append(job)

        _save_index()
        first_job = next(job for job in generated_jobs if job.scene_id == plan.beat_id)
        scene_plan = plan.model_dump() if hasattr(plan, "model_dump") else plan.dict()
        return {
            "job_id": first_job.job_id,
            "provider_job_id": first_job.provider_job_id,
            "story_id": plan.story_id,
            "beat_id": plan.beat_id,
            "total_scenes": len(generated_jobs),
            "jobs": [
                {
                    "job_id": job.job_id,
                    "provider_job_id": job.provider_job_id,
                    "beat_id": job.scene_id,
                    "status": job.status.value,
                }
                for job in generated_jobs
            ],
            "grounding_source": plan.grounding_source,
            "reference_images": plan.reference_images,
            "scene_plan": scene_plan,
            "status": "processing",
            "polling_url": f"https://gateway.pixazo.ai/v2/requests/status/{first_job.provider_job_id}",
        }
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except UnsupportedAssetError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AssetPublishError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except requests.RequestException as error:
        detail = error.response.text if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"Pixazo submission failed: {detail}") from error
