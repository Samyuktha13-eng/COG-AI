from __future__ import annotations

from .models import StoryScene
from .scene_loader import load_scenes


class SceneStore:
    def __init__(self, scenes: list[StoryScene] | None = None):
        self.scenes = scenes or load_scenes()

    def list_scenes(self) -> list[StoryScene]:
        return list(self.scenes)

    def get_scene(self, scene_id: str) -> StoryScene | None:
        return next((scene for scene in self.scenes if scene.id == scene_id), None)
