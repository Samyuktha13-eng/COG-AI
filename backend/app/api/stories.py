from fastapi import APIRouter, HTTPException

from ..data.stories import get_all_stories, get_story

router = APIRouter(
    prefix="/api/stories",
    tags=["stories"],
)


@router.get("")
def list_stories():
    return get_all_stories()


@router.get("/{story_id}")
def read_story(story_id: str):
    story = get_story(story_id)

    if story is None:
        raise HTTPException(
            status_code=404,
            detail=f"Story '{story_id}' not found",
        )

    return story
