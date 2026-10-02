from pathlib import Path

from backend.app.services import assets


def test_populated_nested_story_image_root_beats_empty_top_level(tmp_path: Path, monkeypatch):
    top_level = tmp_path / "Patient story image"
    nested = tmp_path / "cogniv-ai" / "Patient story image"
    top_level.mkdir(parents=True)
    nested.mkdir(parents=True)
    (nested / "scene.jpg").write_bytes(b"image")
    monkeypatch.setattr(assets, "PROJECT_ROOT", tmp_path)

    assert assets._resolve_story_image_root() == nested


def test_configured_story_image_root_overrides_repository_paths(monkeypatch):
    configured = Path("/var/data/story-images")
    monkeypatch.setenv("STORY_IMAGE_DIR", str(configured))

    assert assets._resolve_story_image_root() == configured