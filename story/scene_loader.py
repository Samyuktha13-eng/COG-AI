from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import SceneAsset, StoryScene


def _default_scene() -> list[StoryScene]:
    return [
        StoryScene(
            id="chapter_01_scene_01",
            chapter_id="chapter_01",
            story_id="jasmine_morning",
            location="back door",
            objects=["door", "brass pot"],
            memory_cues=["jasmine", "garland"],
            story_section="opening",
            image_asset=SceneAsset(filename="01_jasmine_morning/jasmine_01_door.jpg", url="", kind="image"),
        )
    ]


def load_scene_data() -> list[dict[str, Any]]:
    return [scene.__dict__ for scene in load_scenes()]


def load_scenes() -> list[StoryScene]:
    project_root = Path(__file__).resolve().parents[1]
    data_file = project_root / "data" / "lakshmi_story_scenes.json"
    if data_file.exists():
        try:
            import json

            payload = json.loads(data_file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [StoryScene(**item) for item in payload]
        except Exception:
            pass
    return _default_scene()
