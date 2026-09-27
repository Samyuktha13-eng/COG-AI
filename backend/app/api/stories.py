from fastapi import APIRouter, HTTPException

from ..data.stories import get_all_stories, get_story
from ..services.local_video_catalog import get_generated_video_catalog

router = APIRouter(
    prefix="/api/stories",
    tags=["stories"],
)


def _with_generated_videos(story):
    payload = story.model_dump(mode="json") if hasattr(story, "model_dump") else story
    payload["generated_videos"] = get_generated_video_catalog().get(story.id, {})
    return payload


@router.get("")
def list_stories():
    catalog = get_generated_video_catalog()
    stories = []
    for story in get_all_stories():
        payload = _with_generated_videos(story)
        payload["generated_videos"] = catalog.get(story.id, {})
        stories.append(payload)
    return stories


@router.get("/{story_id}")
def read_story(story_id: str):
    story = get_story(story_id)

    if story is None:
        raise HTTPException(
            status_code=404,
            detail=f"Story '{story_id}' not found",
        )

    payload = _with_generated_videos(story)
    payload["generated_videos"] = get_generated_video_catalog().get(story_id, {})
    return payload
