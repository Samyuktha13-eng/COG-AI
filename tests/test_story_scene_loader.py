from story.scene_loader import load_scene_data, load_scenes
from story.scene_store import SceneStore


def test_loader_reads_all_scenes_and_store_navigates():
    data = load_scene_data()
    scenes = load_scenes()
    store = SceneStore(scenes)
    assert data["patient_id"] == "P001"
    assert len(scenes) == 42
    assert store.get_next_scene("chapter_01_scene_01").scene_id == "chapter_01_scene_02"
    assert store.get_previous_scene("chapter_01_scene_02").scene_id == "chapter_01_scene_01"
    assert store.get_next_scene("chapter_05_scene_09") is None
    assert store.get_questions("chapter_01_scene_01")[0].scene_id == "chapter_01_scene_01"
    assert store.get_question("q01_flowers").scene_id == "chapter_01_scene_01"
