from pathlib import Path

from ..api.generation import _motion_prompt
from ..data.stories import get_story
from ..services.assets import STORY_IMAGE_ROOT, StoryAssetService
from ..services.pixazo import PixazoVideoService


class PixazoGameVideoProvider:
    """Real Pixazo adapter; inject this only when generation is explicitly enabled."""

    def __init__(self, asset_service: StoryAssetService | None = None):
        self.asset_service = asset_service or StoryAssetService()

    def request(self, story_id: str, beat_id: str) -> tuple[str, str]:
        story = get_story(story_id)
        beat = next((item for item in story.beats if item.id == beat_id), None) if story else None
        if beat is None:
            raise ValueError("Story beat not found")
        image_path = (STORY_IMAGE_ROOT / beat.image_path).resolve()
        image_path.relative_to(STORY_IMAGE_ROOT.resolve())
        image_url = self.asset_service.publish_image(image_path)
        self.asset_service.validate_public_image_url(image_url)
        job = PixazoVideoService().submit(
            beat_id=beat.id,
            image_url=image_url,
            prompt=_motion_prompt(beat),
            duration=6,
            image_strength=beat.image_strength,
            guidance_scale=beat.guidance_scale,
            enable_prompt_expansion=beat.enable_prompt_expansion,
            num_frames=beat.num_frames,
            frames_per_second=beat.frames_per_second,
        )
        return job.status.value, job.request_id or ""
