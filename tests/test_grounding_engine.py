"""Tests for the Story Grounding Engine."""
import pytest
from pathlib import Path
from unittest.mock import patch

from backend.app.services.grounding import GroundingAgent
from backend.app.models.grounding import GroundingResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def agent(tmp_image_root: Path | None = None) -> GroundingAgent:
    return GroundingAgent(patient_image_root=tmp_image_root)


# ---------------------------------------------------------------------------
# 1. Intent extraction
# ---------------------------------------------------------------------------

class TestExtractIntent:
    def test_jasmine_prompt_maps_to_jasmine_morning(self):
        intent = agent().extract_intent("Show Lakshmi picking jasmine flowers in the morning")
        assert intent.story_id == "jasmine_morning"

    def test_mango_prompt_maps_to_mango_tree(self):
        intent = agent().extract_intent("Let's talk about Lakshmi and the mango tree")
        assert intent.story_id == "mango_tree"

    def test_rain_prompt_maps_to_rainy_day_kitchen(self):
        intent = agent().extract_intent("Show the monsoon kitchen with mustard seeds")
        assert intent.story_id == "rainy_day_kitchen"

    def test_school_prompt_maps_to_school_morning(self):
        intent = agent().extract_intent("Lakshmi and Radha walking to school past the temple")
        assert intent.story_id == "school_morning"

    def test_railway_prompt_maps_to_railway_station(self):
        intent = agent().extract_intent("The railway station where the sandal broke")
        assert intent.story_id == "railway_station"

    def test_generic_railway_memory_uses_canonical_scene(self):
        result = agent().resolve("Show me Lakshmi's railway station memory")
        assert result.match is True
        assert result.scene_plan.chapter_id == "chapter_05"
        assert result.scene_plan.scene_id == "chapter_05_scene_01"

    def test_generic_jasmine_memory_uses_story_fallback(self):
        result = agent().resolve("Show Lakshmi's jasmine morning memory.")
        assert result.match is True
        assert result.scene_plan.story_id == "jasmine_morning"
        assert result.scene_plan.chapter_id == "chapter_01"

    def test_unrecognised_prompt_returns_none_story(self):
        intent = agent().extract_intent("Show me something about space rockets")
        assert intent.story_id is None

    def test_childhood_period_detected(self):
        intent = agent().extract_intent("Lakshmi's childhood mango memories")
        assert intent.life_period == "childhood"

    def test_raw_prompt_preserved(self):
        prompt = "Show Lakshmi's jasmine morning"
        intent = agent().extract_intent(prompt)
        assert intent.raw_prompt == prompt


# ---------------------------------------------------------------------------
# 2. Beat matching
# ---------------------------------------------------------------------------

class TestFindStoryBeat:
    def test_garland_prompt_matches_jasmine_05(self):
        a = agent()
        intent = a.extract_intent("Lakshmi threading flowers into a garland")
        result = a.find_story_beat(intent)
        assert result is not None
        _, beat = result
        assert beat.id == "jasmine_05"

    def test_picking_flowers_matches_jasmine_04(self):
        a = agent()
        intent = a.extract_intent("Lakshmi picking and selecting jasmine flowers")
        result = a.find_story_beat(intent)
        assert result is not None
        _, beat = result
        assert beat.id == "jasmine_04"

    def test_father_salt_chilli_matches_mango_05(self):
        a = agent()
        intent = a.extract_intent("father cuts mango with salt and chilli")
        result = a.find_story_beat(intent)
        assert result is not None
        _, beat = result
        assert beat.id == "mango_05"

    def test_no_story_id_returns_none(self):
        a = agent()
        from backend.app.models.grounding import CaregiverIntent
        intent = CaregiverIntent(raw_prompt="rockets", story_id=None)
        assert a.find_story_beat(intent) is None

    def test_story_with_no_beat_keywords_returns_none(self):
        # Safety rule: story matched but no beat keyword → no match, nothing sent to Pixazo
        a = agent()
        intent = a.extract_intent("jasmine morning")  # story matched, no specific beat keyword
        result = a.find_story_beat(intent)
        assert result is None


# ---------------------------------------------------------------------------
# 3. Image selection
# ---------------------------------------------------------------------------

class TestSelectReferenceImages:
    def test_returns_beat_image_when_folder_missing(self, tmp_path):
        a = agent(tmp_image_root=tmp_path)
        from backend.app.data.stories import get_story
        story = get_story("jasmine_morning")
        beat = story.beats[3]  # jasmine_04
        images = a.select_reference_images("jasmine_morning", beat)
        assert beat.image_path in images

    def test_primary_image_is_first(self, tmp_path):
        folder = tmp_path / "01_jasmine_morning"
        folder.mkdir(parents=True)
        (folder / "jasmine_01_door.jpg").write_bytes(b"x")
        (folder / "jasmine_04_picking_flowers.jpg").write_bytes(b"x")
        a = agent(tmp_image_root=tmp_path)
        from backend.app.data.stories import get_story
        beat = get_story("jasmine_morning").beats[3]  # jasmine_04
        images = a.select_reference_images("jasmine_morning", beat)
        assert images[0] == beat.image_path

    def test_returns_at_most_three_images(self, tmp_path):
        folder = tmp_path / "01_jasmine_morning"
        folder.mkdir(parents=True)
        for i in range(8):
            (folder / f"jasmine_0{i}.jpg").write_bytes(b"x")
        a = agent(tmp_image_root=tmp_path)
        from backend.app.data.stories import get_story
        beat = get_story("jasmine_morning").beats[0]
        images = a.select_reference_images("jasmine_morning", beat)
        assert len(images) <= 3


# ---------------------------------------------------------------------------
# 4. No-match safety
# ---------------------------------------------------------------------------

class TestNoMatchSafety:
    def test_unrecognised_prompt_returns_no_match(self):
        result = agent().resolve("Show me something about space rockets")
        assert result.match is False
        assert result.scene_plan is None

    def test_no_match_reason_is_set(self):
        result = agent().resolve("completely unrelated topic xyz")
        assert result.reason != ""

    def test_no_match_does_not_raise(self):
        # Must never raise — always return a GroundingResult
        result = agent().resolve("")
        assert isinstance(result, GroundingResult)


# ---------------------------------------------------------------------------
# 5. Full resolve
# ---------------------------------------------------------------------------

class TestResolve:
    def test_jasmine_resolve_returns_match(self):
        result = agent().resolve("Show Lakshmi picking jasmine flowers")
        assert result.match is True
        assert result.scene_plan is not None
        assert result.scene_plan.story_id == "jasmine_morning"

    def test_scene_plan_has_grounding_source(self):
        result = agent().resolve("Lakshmi threading jasmine garland")
        assert result.scene_plan.grounding_source.startswith("story:jasmine_morning/beat:")

    def test_scene_plan_has_video_prompt(self):
        result = agent().resolve("Show Lakshmi picking jasmine flowers")
        assert len(result.scene_plan.video_prompt) > 100

    def test_scene_plan_carries_story_grounded_interaction(self):
        result = agent().resolve("Show Lakshmi picking jasmine flowers")
        plan = result.scene_plan
        assert plan.facts
        assert plan.required_actions
        assert plan.forbidden_actions
        assert plan.interaction_plan["allow_no_speech"] is True

    def test_video_prompt_contains_grounding_source(self):
        result = agent().resolve("Show Lakshmi picking jasmine flowers")
        assert result.scene_plan.grounding_source in result.scene_plan.video_prompt

    def test_video_prompt_contains_no_invented_people_constraint(self):
        result = agent().resolve("Show Lakshmi picking jasmine flowers")
        assert "No invented people" in result.scene_plan.video_prompt

    def test_mango_resolve_returns_correct_story(self):
        result = agent().resolve("Lakshmi climbing the mango tree")
        assert result.match is True
        assert result.scene_plan.story_id == "mango_tree"

    def test_intent_preserved_in_result(self):
        prompt = "Show Lakshmi picking jasmine flowers"
        result = agent().resolve(prompt)
        assert result.intent.raw_prompt == prompt
