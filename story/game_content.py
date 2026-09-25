from __future__ import annotations

from pathlib import Path

from .scene_loader import load_scenes
from .scene_store import SceneStore


def create_scene_store() -> SceneStore:
    return SceneStore(load_scenes())


def load_reminder_visuals() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    visuals_path = root / "data" / "reminder_visuals.json"
    if visuals_path.exists():
        try:
            import json

            return json.loads(visuals_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
