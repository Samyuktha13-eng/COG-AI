from memory.store import MemoryStore
from media_generation.models import MediaGenerationRequest, MemorySceneSpecification
from media_generation.prompt_builder import MediaPromptBuilder
from reminiscence.memory_selector import MemoryCandidate, PersonalMemorySource
from story.scene_loader import load_scenes


def test_story_scene_builds_deterministic_provider_independent_request():
    scene = load_scenes()[0]
    candidate = MemoryCandidate.from_scene(scene)
    request = MediaPromptBuilder().build(candidate, "P001", life_stage="unspecified")
    repeated = MediaPromptBuilder().build(candidate, "P001", life_stage="unspecified")
    assert request.to_dict() == repeated.to_dict()
    assert request.source_type == "story_scene"
    assert request.memory_id == scene.scene_id
    assert request.reference_asset == scene.image_asset.filename
    assert scene.story_section in request.factual_memory
    assert request.requested_media_type == "image_or_video"
    assert any("Do not invent autobiographical facts" in constraint for constraint in request.negative_constraints)
    assert "quiz" in " ".join(request.negative_constraints)


def test_personal_memory_facts_are_preserved_without_new_story_details():
    store = MemoryStore()
    memory = store.save_memory({
        "memory_id": "memory_school_radha", "patient_id": "P001", "title": "School walk",
        "story": "Lakshmi walked to school with Radha.", "source": "caregiver", "confidence": 1,
        "sensitive": False, "language": "en", "people": ["Radha"], "place": "school route",
        "objects": ["blue cloth bag"], "tags": ["childhood", "school"],
    })
    candidate = PersonalMemorySource(store).candidates("P001")[0]
    request = MediaPromptBuilder().build(candidate, "P001", life_stage="childhood")
    assert request.factual_memory == memory["story"]
    assert request.life_stage == "childhood"
    assert "Radha" in request.image_prompt
    assert "school route" in request.video_prompt
    assert "do not add new events" in request.video_prompt.casefold()
    assert request.patient_id == "P001"


def test_scene_specification_and_request_round_trip():
    scene = load_scenes()[0]
    specification = MemorySceneSpecification("m", "P001", "story_scene", "fact", "childhood")
    assert MemorySceneSpecification.from_dict(specification.to_dict()) == specification
    request = MediaPromptBuilder().build(MemoryCandidate.from_scene(scene), "P001")
    assert MediaGenerationRequest.from_dict(request.to_dict()) == request
