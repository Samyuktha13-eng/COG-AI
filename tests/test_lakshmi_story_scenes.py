from story.scene_loader import load_scenes


CHAPTERS = ["chapter_01", "chapter_02", "chapter_03", "chapter_04", "chapter_05"]
ASSET_PREFIXES = ["jasmine_", "mango_", "rain_", "school_", "station_"]
ASSET_COUNTS = [8, 8, 8, 9, 9]


def test_five_chapters_order_and_contiguous_sequences():
    scenes = load_scenes()
    assert [scene.chapter_id for scene in scenes if scene.sequence == 1] == CHAPTERS
    assert len({scene.scene_id for scene in scenes}) == len(scenes)
    for chapter_id, expected_count in zip(CHAPTERS, ASSET_COUNTS):
        chapter = [scene for scene in scenes if scene.chapter_id == chapter_id]
        assert [scene.sequence for scene in chapter] == list(range(1, expected_count + 1))


def test_scene_links_and_questions_are_consistent():
    scenes = load_scenes()
    by_id = {scene.scene_id: scene for scene in scenes}
    questions = [question for scene in scenes for question in scene.questions]
    assert len({question.question_id for question in questions}) == len(questions)
    assert len(questions) == 15
    assert all(question.scene_id == scene.scene_id for scene in scenes for question in scene.questions)
    assert all(question.expected_concepts and question.acceptable_answers for question in questions)
    for scene in scenes:
        if scene.next_scene_id:
            assert by_id[scene.next_scene_id].previous_scene_id == scene.scene_id
        if scene.previous_scene_id:
            assert by_id[scene.previous_scene_id].next_scene_id == scene.scene_id


def test_image_filenames_match_existing_chapter_conventions():
    scenes = load_scenes()
    for chapter_index, (prefix, count) in enumerate(zip(ASSET_PREFIXES, ASSET_COUNTS), 1):
        chapter = [scene for scene in scenes if scene.chapter_id == f"chapter_{chapter_index:02d}"]
        filenames = [scene.image_asset.filename.rsplit("/", 1)[-1] for scene in chapter]
        assert all(filename.startswith(prefix) and filename.endswith(".jpg") for filename in filenames)
        assert [int(filename.split("_")[1].split(".")[0]) for filename in filenames] == list(range(1, count + 1))
