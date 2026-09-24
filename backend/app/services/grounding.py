"""
Story Grounding Engine
======================
Turns a caregiver's free-text (or voice-transcribed) prompt into a fully
grounded ScenePlan before anything is sent to Pixazo.

Design rules
------------
* No LLM — intent extraction is deterministic keyword matching against the
  known story registry.  Fast, testable, never invents.
* No fallback generation — if no beat matches, returns GroundingResult(match=False).
* Every ScenePlan records grounding_source so the database always knows which
  story beat and which patient images were used.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..data.stories import get_all_stories
from ..models.beat import StoryBeat
from ..models.grounding import CaregiverIntent, GroundingResult, ScenePlan
from ..models.story import Story
from story.scene_loader import load_scenes

# ---------------------------------------------------------------------------
# Keyword index — maps surface words/phrases → story_id
# ---------------------------------------------------------------------------
_STORY_KEYWORDS: dict[str, list[str]] = {
    "jasmine_morning": [
        "jasmine", "garland", "flower", "brass pot", "morning ritual",
        "back door", "wooden door", "thread", "picking flower",
    ],
    "mango_tree": [
        "mango", "tree", "climb", "branch", "father", "salt", "chilli",
        "pocket knife", "summer", "childhood mango",
    ],
    "rainy_day_kitchen": [
        "rain", "monsoon", "kitchen", "mustard", "curry leaves", "garlic",
        "iron pan", "oil", "salt", "rainy", "cooking",
    ],
    "school_morning": [
        "school", "walk", "temple", "bridge", "jaggery", "tea shop",
        "barefoot", "radha", "dirt road", "morning walk",
    ],
    "railway_station": [
        "railway", "station", "train", "sandal", "strap", "book",
        "young man", "rain", "platform",
    ],
}

# Beat-level keywords: beat_id → extra keywords that distinguish this beat
_BEAT_KEYWORDS: dict[str, list[str]] = {
    "jasmine_01": ["door", "close door", "back door"],
    "jasmine_02": ["water", "pot", "brass", "tap", "fill"],
    "jasmine_03": ["carry", "walk", "plant"],
    "jasmine_04": ["pick", "select", "collect", "pluck"],
    "jasmine_05": ["thread", "garland", "string", "make garland"],
    "mango_01": ["choose", "select", "largest", "kitchen", "bag"],
    "mango_02": ["carry", "run", "outside"],
    "mango_03": ["climb", "branch", "trunk"],
    "mango_04": ["eat", "bite", "juice", "sit"],
    "mango_05": ["father", "cut", "salt", "chilli", "knife"],
    "rain_01": ["watch", "rain", "door", "listen"],
    "rain_02": ["oil", "pan", "mustard", "heat"],
    "rain_03": ["curry leaves", "sizzle", "fry"],
    "rain_04": ["garlic", "peel", "crush", "board"],
    "rain_05": ["taste", "salt", "adjust", "spoon"],
    "school_01": ["walk", "start", "begin", "route"],
    "school_02": ["temple", "bridge", "cross"],
    "school_03": ["jaggery", "tea shop", "stop"],
    "school_04": ["barefoot", "shoes", "remove", "dirt"],
    "school_05": ["gate", "arrive", "entrance"],
    "railway_01": ["wait", "roof", "shelter", "books"],
    "railway_02": ["sandal", "broken", "strap", "fix"],
    "railway_03": ["string", "tie", "repair", "young man"],
    "railway_04": ["book", "fall", "pick up"],
    "railway_05": ["train", "leave", "depart", "watch"],
}

# Image subfolder names that correspond to each story
_STORY_IMAGE_FOLDERS: dict[str, str] = {
    "jasmine_morning": "01_jasmine_morning",
    "mango_tree": "02_Mango",
    "rainy_day_kitchen": "03_rainy_day_kitchen",
    "school_morning": "04_school_morning",
    "railway_station": "05_railway_station",
}

# Constraints that always apply regardless of beat
_UNIVERSAL_CONSTRAINTS = [
    "No invented people",
    "No invented locations",
    "No invented objects",
    "No invented dialogue",
    "No invented medical facts",
    "Preserve character identity and clothing",
    "No background morphing",
    "No scene transitions",
]

_CANONICAL_CHAPTERS = {
    "jasmine_morning": "chapter_01",
    "mango_tree": "chapter_02",
    "rainy_day_kitchen": "chapter_03",
    "school_morning": "chapter_04",
    "railway_station": "chapter_05",
}


def _tokenize(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def _score_story(tokens: list[str], story_id: str) -> int:
    keywords = _STORY_KEYWORDS.get(story_id, [])
    text = " ".join(tokens)
    return sum(1 for kw in keywords if kw in text)


def _score_beat(tokens: list[str], beat_id: str) -> int:
    keywords = _BEAT_KEYWORDS.get(beat_id, [])
    text = " ".join(tokens)
    return sum(1 for kw in keywords if kw in text)


def _canonical_scene_score(tokens: list[str], scene) -> int:
    text = " ".join(tokens)
    searchable = [
        *scene.memory_cues,
        scene.location,
        *scene.objects,
        scene.story_section,
    ]
    return sum(1 for phrase in searchable if phrase.lower() in text)


class GroundingAgent:
    """
    Stateless grounding agent.  All methods are pure functions of their inputs.
    """

    def __init__(self, patient_image_root: Path | None = None):
        from ..services.assets import STORY_IMAGE_ROOT
        self._image_root = patient_image_root or STORY_IMAGE_ROOT

    # ------------------------------------------------------------------
    # 1. Intent extraction
    # ------------------------------------------------------------------
    def extract_intent(self, prompt: str) -> CaregiverIntent:
        tokens = _tokenize(prompt)
        text = " ".join(tokens)

        # Score every story
        scores = {sid: _score_story(tokens, sid) for sid in _STORY_KEYWORDS}
        best_story = max(scores, key=lambda s: scores[s])
        story_id = best_story if scores[best_story] > 0 else None

        # Simple life-period detection
        life_period = ""
        if any(w in text for w in ["childhood", "child", "young", "school", "summer"]):
            life_period = "childhood"
        elif any(w in text for w in ["morning", "daily", "routine"]):
            life_period = "daily_routine"

        # Named entities: just pull capitalised words from the original prompt
        entities = [w for w in prompt.split() if w and w[0].isupper() and len(w) > 2]

        return CaregiverIntent(
            raw_prompt=prompt,
            topic=text[:80],
            life_period=life_period,
            entities=entities,
            story_id=story_id,
        )

    # ------------------------------------------------------------------
    # 2. Beat matching
    # ------------------------------------------------------------------
    def find_story_beat(self, intent: CaregiverIntent) -> tuple[Story, StoryBeat] | None:
        if intent.story_id is None:
            return None

        tokens = _tokenize(intent.raw_prompt)
        all_stories = get_all_stories()
        story = next((s for s in all_stories if s.id == intent.story_id), None)
        if story is None:
            return None

        # Score each beat; require at least one keyword match
        scored = [(beat, _score_beat(tokens, beat.id)) for beat in story.beats]
        best_beat, best_score = max(scored, key=lambda x: x[1])

        # No beat keyword matched — do not guess; caller gets no match
        if best_score == 0:
            canonical_scene = self._find_canonical_scene(intent)
            if canonical_scene is None:
                return None
            canonical_image = canonical_scene.image_asset.filename if canonical_scene.image_asset else ""
            canonical_beat = next(
                (candidate for candidate in story.beats if candidate.image_path == canonical_image),
                None,
            )
            if canonical_beat is None:
                return None
            return story, canonical_beat

        return story, best_beat

    def _find_canonical_scene(self, intent: CaregiverIntent):
        chapter_id = _CANONICAL_CHAPTERS.get(intent.story_id or "")
        if chapter_id is None:
            return None

        chapter_scenes = [
            scene for scene in load_scenes() if scene.chapter_id == chapter_id
        ]
        if not chapter_scenes:
            return None

        prompt_tokens = _tokenize(intent.raw_prompt)
        scored = [
            (scene, _canonical_scene_score(prompt_tokens, scene))
            for scene in chapter_scenes
        ]
        if not scored:
            return None

        scene, score = max(scored, key=lambda item: item[1])
        if score >= 2:
            return scene

        # Generic story prompts such as "Show Lakshmi's jasmine morning memory"
        # often mention the chapter but not a specific beat. In that case, anchor
        # to the first scene in the story chapter instead of rejecting the whole
        # prompt as a no-match.
        if any(word in " ".join(prompt_tokens) for word in ["memory", "story", "recall", "remember"]):
            return chapter_scenes[0]

        return None

    # ------------------------------------------------------------------
    # 3. Image selection
    # ------------------------------------------------------------------
    def select_reference_images(self, story_id: str, beat: StoryBeat) -> list[str]:
        """
        Returns relative paths (relative to STORY_IMAGE_ROOT) of images that
        support this beat.  Prefers the beat's own image_path, then adds
        neighbouring images from the same story folder.
        """
        folder_name = _STORY_IMAGE_FOLDERS.get(story_id, "")
        folder = self._image_root / folder_name
        if not folder.is_dir():
            # Fall back to just the beat's declared image
            return [beat.image_path] if beat.image_path else []

        all_images = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        relative = [img.relative_to(self._image_root).as_posix() for img in all_images]

        # Always put the beat's own image first
        primary = beat.image_path
        ordered = [primary] if primary in relative else []
        ordered += [r for r in relative if r != primary]

        # Return at most 3 reference images to keep the prompt focused
        return ordered[:3]

    # ------------------------------------------------------------------
    # 4. Scene plan
    # ------------------------------------------------------------------
    def build_scene_plan(
        self,
        story: Story,
        beat: StoryBeat,
        reference_images: list[str],
    ) -> ScenePlan:
        constraints = list(_UNIVERSAL_CONSTRAINTS)
        for c in beat.motion_constraints:
            constraints.append(f"No {c.strip()}")

        canonical_scene = self._canonical_scene_for_beat(story.id, beat)
        questions = canonical_scene.questions if canonical_scene else []
        question = questions[0] if questions else None
        plan = ScenePlan(
            story_id=story.id,
            beat_id=beat.id,
            chapter_id=canonical_scene.chapter_id if canonical_scene else None,
            scene_id=canonical_scene.scene_id if canonical_scene else None,
            facts=[canonical_scene.story_section] if canonical_scene else [beat.action],
            required_actions=list(beat.motion_sequence),
            forbidden_actions=list(constraints),
            interaction_plan={
                "required": bool(question),
                "type": "speech_or_choice" if question else "speech_or_skip",
                "question": question.prompt if question else "What do you notice?",
                "expected_response": list(question.expected_concepts) if question else [],
                "allow_speech": question.allow_voice_answer if question else True,
                "allow_no_speech": True,
                "reference_scene_id": canonical_scene.scene_id if canonical_scene else None,
            },
            action=beat.action,
            motion_sequence=beat.motion_sequence,
            constraints=constraints,
            reference_images=reference_images,
            grounding_source=f"story:{story.id}/beat:{beat.id}",
        )
        plan.video_prompt = self.compose_video_prompt(plan, beat)
        return plan

    @staticmethod
    def _canonical_scene_for_beat(story_id: str, beat: StoryBeat):
        return next(
            (
                scene
                for scene in load_scenes()
                if scene.chapter_id == _CANONICAL_CHAPTERS.get(story_id)
                and scene.image_asset
                and scene.image_asset.filename == beat.image_path
            ),
            None,
        )

    # ------------------------------------------------------------------
    # 5. Video prompt composition
    # ------------------------------------------------------------------
    def compose_video_prompt(self, plan: ScenePlan, beat: StoryBeat) -> str:
        step_block = "\n".join(
            f"{i}. {step}" for i, step in enumerate(plan.motion_sequence, 1)
        )
        constraint_block = "\n".join(f"{c}." for c in plan.constraints)
        ref_block = "\n".join(f"  - {img}" for img in plan.reference_images)

        return (
            "Starting from the exact reference image, the motion should unfold "
            "in a single continuous sequence.\n\n"
            "GROUNDING SOURCE\n"
            f"{plan.grounding_source}\n\n"
            "REFERENCE IMAGES\n"
            f"{ref_block}\n\n"
            "ACTION\n"
            f"{plan.action}\n\n"
            "MOTION SEQUENCE\n"
            f"{step_block}\n\n"
            "Each action must finish before the next begins.\n"
            "Movement must be smooth, physically plausible and continuous.\n"
            "Maintain consistent character identity, body proportions, clothing,\n"
            "objects, environment, lighting and spatial relationships throughout.\n\n"
            "CONSTRAINTS\n"
            f"{constraint_block}\n\n"
            f"Reference context: {beat.action}. {beat.motion}. {beat.camera}.\n"
            "Preserve the exact character identity, face, clothing, objects,\n"
            "architecture, lighting and composition from the reference image.\n"
            "No teleportation. No sudden pose changes. No instantaneous movement.\n"
            "No duplicated limbs. No body morphing. No face morphing.\n"
            "No background morphing. No scene transition. No new objects.\n"
            "No additional people. No camera shake. No random camera movement.\n"
            "No time jumps. No accelerated action. No change of viewpoint."
        )

    # ------------------------------------------------------------------
    # 6. Top-level resolve
    # ------------------------------------------------------------------
    def resolve(self, prompt: str) -> GroundingResult:
        intent = self.extract_intent(prompt)
        if intent.story_id is None:
            return GroundingResult(
                match=False,
                reason="no_grounded_story_match",
                intent=intent,
            )

        result = self.find_story_beat(intent)
        if result is None:
            return GroundingResult(
                match=False,
                reason="story_found_but_no_beat_matched",
                intent=intent,
            )

        story, beat = result
        images = self.select_reference_images(story.id, beat)
        plan = self.build_scene_plan(story, beat, images)

        return GroundingResult(match=True, intent=intent, scene_plan=plan)
