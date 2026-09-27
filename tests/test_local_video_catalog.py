from pathlib import Path

from backend.app.services.local_video_catalog import _build_generated_video_catalog


def test_build_generated_video_catalog_detects_story_and_beat(tmp_path: Path):
    output_root = tmp_path / "outputs"
    story_dir = output_root / "school_morning_story"
    story_dir.mkdir(parents=True)
    mp4_file = story_dir / "school_01_morning_route_story.mp4"
    mp4_file.write_bytes(b"video")

    catalog = _build_generated_video_catalog(output_root)

    assert "school_morning" in catalog
    assert "school_01" in catalog["school_morning"]
    assert catalog["school_morning"]["school_01"]["url"] == "/generated-videos/school_morning_story/school_01_morning_route_story.mp4"
    assert catalog["school_morning"]["school_01"]["path"] == "school_morning_story/school_01_morning_route_story.mp4"
