from story.models import AnswerOutcome, Question, SceneAsset, StoryScene


def test_models_support_scene_question_and_assets():
    asset = SceneAsset("image", "jasmine_01_door.jpg", "door")
    question = Question("q", "scene", "recall", "What?", "en", ["jasmine"], ["jasmine"])
    scene = StoryScene("scene", "P001", "chapter_01", 1, "Title", "Exact text", "Source", "Summary", image_asset=asset, questions=[question])
    assert scene.image_asset.filename == "jasmine_01_door.jpg"
    assert scene.questions[0].expected_concepts == ["jasmine"]
    assert {state.value for state in AnswerOutcome} == {"remembered", "almost_remembered", "needs_support"}
