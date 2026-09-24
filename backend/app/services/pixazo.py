import os
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

from ..models.generation import GenerationJob, GenerationStatus

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env", override=True)

PIXAZO_ENDPOINT = os.getenv(
    "PIXAZO_IMAGE_TO_VIDEO_ENDPOINT",
    "https://gateway.pixazo.ai/ltx-video/v1/image-to-video",
)

PIXAZO_STATUS_ENDPOINT = "https://gateway.pixazo.ai/v2/requests/status"
QUALITY_LTX_NEGATIVE_PROMPT = (
    "ghosting, blur, temporal blur, motion blur, defocus, soft focus, low detail, double exposure, body morphing, "
    "face morphing, duplicate body, duplicate limbs, disappearing limbs, "
    "teleportation, sudden pose changes, background morphing, architecture changing, "
    "object duplication, scene transition, camera movement, camera shake, zoom, pan, "
    "flickering, unstable clothing, reversed action, backwards motion, opposite action"
)


class PixazoVideoService:
    def __init__(self):
        self.api_key = os.getenv("PIXAZO_API_KEY") or ""

    @property
    def headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        return headers

    @staticmethod
    def _require_api_key(api_key: str | None = None) -> str:
        resolved = api_key or os.getenv("PIXAZO_API_KEY") or ""
        if not resolved:
            raise RuntimeError("PIXAZO_API_KEY is not configured.")
        return resolved

    def submit(
        self,
        *,
        beat_id: str,
        image_url: str,
        prompt: str,
        duration: int = 4,
        image_strength: float = 0.8,
        guidance_scale: float = 0.8,
        enable_prompt_expansion: bool = False,
        negative_prompt: str | None = None,
        num_frames: int = 72,
        frames_per_second: int = 18,
        end_image_url: str | None = None,
    ) -> GenerationJob:
        self._require_api_key()

        job = GenerationJob(
            id=str(uuid.uuid4()),
            beat_id=beat_id,
            provider="pixazo",
            model="ltx-video",
            status=GenerationStatus.PENDING,
            source_image_url=image_url,
            prompt=prompt,
        )

        payload = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "image_strength": max(0.0, min(1.0, float(image_strength))),
            "guidance_scale": max(0.0, float(guidance_scale)),
            "enable_prompt_expansion": bool(enable_prompt_expansion),
            "negative_prompt": negative_prompt or QUALITY_LTX_NEGATIVE_PROMPT,
            "num_frames": int(num_frames),
            "frames_per_second": int(frames_per_second),
        }
        if end_image_url:
            payload["end_image_url"] = end_image_url

        for attempt in range(3):
            response = requests.post(
                PIXAZO_ENDPOINT,
                headers=self.headers,
                json=payload,
                timeout=60,
            )
            if response.status_code != 429 or attempt == 2:
                break
            retry_after = response.headers.get("Retry-After", "30")
            try:
                delay = max(1, min(90, int(float(retry_after))))
            except ValueError:
                delay = 30
            time.sleep(delay)

        response.raise_for_status()

        data = response.json()
        job.request_id = data["request_id"]
        job.status = GenerationStatus.QUEUED

        return job

    @staticmethod
    def get_status(job: GenerationJob) -> GenerationJob:
        if not job.request_id:
            raise RuntimeError("Generation job has no Pixazo request_id.")

        api_key = PixazoVideoService._require_api_key()

        url = f"{PIXAZO_STATUS_ENDPOINT}/{job.request_id}"
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": api_key,
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()
        status = data.get("status")

        if status == "QUEUED":
            job.status = GenerationStatus.QUEUED
        elif status == "PROCESSING":
            job.status = GenerationStatus.PROCESSING
        elif status == "COMPLETED":
            job.status = GenerationStatus.COMPLETED

            media = data.get("output", {}).get("media_url", [])
            if media:
                job.output_url = media[0]
        elif status in {"FAILED", "ERROR"}:
            job.status = GenerationStatus.FAILED
            job.error = data.get("error", "Pixazo generation failed.")

        return job

    def wait_for_completion(
        self,
        job: GenerationJob,
        *,
        poll_interval: int = 8,
        timeout: int = 900,
    ) -> GenerationJob:
        start = time.time()

        while True:
            job = PixazoVideoService.get_status(job)

            if job.status == GenerationStatus.COMPLETED:
                return job

            if job.status == GenerationStatus.FAILED:
                return job

            if time.time() - start > timeout:
                job.status = GenerationStatus.FAILED
                job.error = "Generation timeout."
                return job

            time.sleep(poll_interval)

    def download(self, job: GenerationJob, output_dir: str | Path) -> GenerationJob:
        if not job.output_url:
            raise RuntimeError("Generation has no output URL.")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{job.beat_id}.mp4"

        response = requests.get(job.output_url, timeout=180)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        job.local_path = str(output_path)

        return job
