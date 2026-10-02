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

def test_build_generated_video_catalog_discovers_webm_files(tmp_path: Path):
    output_root = tmp_path / "outputs"
    story_dir = output_root / "mango_tree"
    story_dir.mkdir(parents=True)
    webm_file = story_dir / "mango_03_tree_climb.webm"
    webm_file.write_bytes(b"video")

    catalog = _build_generated_video_catalog(output_root)

    assert catalog["mango_tree"]["mango_03"]["filename"] == webm_file.name
    assert catalog["mango_tree"]["mango_03"]["url"] == "/generated-videos/mango_tree/mango_03_tree_climb.webm"


def test_story_directory_wins_over_other_story_words_in_filename(tmp_path: Path):
    output_root = tmp_path / "outputs"
    railway_dir = output_root / "railway_station_story"
    kitchen_dir = output_root / "rainy_day_batch_3"
    railway_dir.mkdir(parents=True)
    kitchen_dir.mkdir(parents=True)
    (railway_dir / "station_01_rain_arrival_story.mp4").write_bytes(b"video")
    (kitchen_dir / "rain_01_kitchen_story.mp4").write_bytes(b"video")

    catalog = _build_generated_video_catalog(output_root)

    assert "railway_01" in catalog["railway_station"]
    assert "railway_01" not in catalog.get("rainy_day_kitchen", {})
    assert "rain_01" in catalog["rainy_day_kitchen"]


def test_catalog_ignores_video_files_without_a_canonical_beat(tmp_path: Path):
    output_root = tmp_path / "outputs"
    story_dir = output_root / "mango_tree"
    story_dir.mkdir(parents=True)
    (story_dir / "mango_02_largest_mango.mp4").write_bytes(b"video")
    (story_dir / "mango_08_unrelated_scene.mp4").write_bytes(b"video")

    catalog = _build_generated_video_catalog(output_root)

    assert "mango_02" in catalog["mango_tree"]
    assert "mango_08" not in catalog["mango_tree"]
