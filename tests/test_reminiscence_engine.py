from memory.store import MemoryStore
from reminiscence.conversation_state import ConversationState
from reminiscence.memory_selector import MemorySelector, PersonalMemorySource
from reminiscence.reminiscence_engine import ReminiscenceEngine
from story.scene_store import SceneStore


def test_story_cue_opens_conversation_and_state_serializes():
    engine = ReminiscenceEngine(MemorySelector(scene_store=SceneStore()))
    state, turn = engine.start("P001", {"topics": ["school"], "time_of_day": "morning"})
    assert turn.media.purpose == "reminiscence_cue"
    assert turn.prompt.startswith("Does this")
    restored = ConversationState.from_dict(state.to_dict())
    assert restored.current_scene_id == state.current_scene_id
    assert "quiz" not in turn.prompt.casefold()


def test_patient_concepts_drive_follow_up_without_matching_answer_text():
    store = MemoryStore()
    store.save_memory({"memory_id": "school_memory", "patient_id": "P001", "title": "School mornings", "story": "Lakshmi walked to school with Radha.", "source": "caregiver", "confidence": 1, "sensitive": False, "language": "en", "people": ["Radha"], "tags": ["school", "morning"]})
    store.save_memory({"memory_id": "food_memory", "patient_id": "P001", "title": "Family lunch", "story": "Lakshmi shared lunch with family.", "source": "caregiver", "confidence": 1, "sensitive": False, "language": "en", "people": ["family"], "tags": ["lunch"]})
    engine = ReminiscenceEngine(MemorySelector([PersonalMemorySource(store)]))
    state, _ = engine.start("P001", {"topics": ["school"]})
    state, turn = engine.handle_meaning_result(state, {"entities": {"person": "Radha", "concepts": ["school", "walking"]}, "needs_clarification": False}, "I used to walk with my friend")
    assert state.mentioned_people == ["Radha"]
    assert "school" in state.active_topics
    assert "walking" in state.active_topics
    assert turn is not None
    assert "Radha" in turn.prompt
