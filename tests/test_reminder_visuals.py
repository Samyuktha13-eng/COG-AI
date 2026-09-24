from story.game_content import load_reminder_visuals
from story.scene_loader import load_scenes


EXPECTED_TYPES = {"medicine", "water", "breakfast", "lunch", "appointment", "walk", "family_call", "bedtime", "morning", "family_meal", "gardening", "get_ready"}


def test_all_reminder_visual_types_are_present_and_separate():
    reminders = load_reminder_visuals()
    assert len(reminders) == 12
    assert {item["reminder_type"] for item in reminders} == EXPECTED_TYPES
    assert all(item["image_asset"] and item["description"] and item["suggested_voice_style"] for item in reminders)
    assert all(not scene.chapter_id.startswith("reminder") for scene in load_scenes())
