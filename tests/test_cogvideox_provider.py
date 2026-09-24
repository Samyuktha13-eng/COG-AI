from pathlib import Path
from tempfile import TemporaryDirectory

from media_generation.models import MediaGenerationRequest, VideoGenerationResult
from media_generation.providers.cogvideox_provider import CogVideoXConfig, CogVideoXProvider, CogVideoXUnavailableError
from media_generation.prompt_builder import MediaPromptBuilder
from reminiscence.memory_selector import MemoryCandidate
from story.scene_loader import load_scenes


class FakeImage:
    size = (640, 480)


class FakePipeline:
    def __init__(self):
        self.calls = []

    def __call__(self, image, prompt, num_frames, num_inference_steps, guidance_scale, generator, negative_prompt=None):
        self.calls.append({"image": image, "prompt": prompt, "num_frames": num_frames, "steps": num_inference_steps, "guidance": guidance_scale, "generator": generator, "negative_prompt": negative_prompt})
        return type("Output", (), {"frames": [["frame"]]})()


class TestProvider(CogVideoXProvider):
    def _save_video(self, frames, request_id):
        return Path("outputs") / f"{request_id}.mp4"


def request():
    return MediaGenerationRequest(
        request_id="media_school",
        memory_id="school",
        patient_id="P001",
        source_type="story_scene",
        factual_memory="Lakshmi walked to school with Radha.",
        life_stage="childhood",
        people=["Lakshmi", "Radha"],
        place="school route",
        objects=["blue cloth bag"],
        sensory_cues=["morning"],
        emotional_tone="warm and gentle",
        visual_scene="Lakshmi and Radha walking on the school route.",
        image_prompt="image",
        video_prompt="slow walking motion",
        continuity_constraints=["Keep Radha consistent."],
        negative_constraints=["Do not add new events."],
        reference_asset="reference.jpg",
    )


def test_config_defaults_and_lazy_loading():
    provider = CogVideoXProvider(CogVideoXConfig())
    assert provider.config.model_id == "THUDM/CogVideoX-5b-I2V"
    assert provider.config.seed == 42
    assert provider.is_loaded is False


def test_provider_propagates_reference_prompt_constraints_and_seed():
    with TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        reference = tmp_path / "reference.jpg"
        reference.write_bytes(b"test")
        pipeline = FakePipeline()
        provider = TestProvider(
            CogVideoXConfig(seed=None, asset_root=str(tmp_path)),
            pipeline=pipeline,
            image_loader=lambda path: FakeImage(),
        )
        value = request()
        value = MediaGenerationRequest.from_dict({**value.to_dict(), "reference_asset": reference.name})
        result = provider.generate(value)
        assert isinstance(result, VideoGenerationResult)
        assert pipeline.calls[0]["prompt"] == "slow walking motion"
        assert pipeline.calls[0]["negative_prompt"] == "Do not add new events."
        assert result.provider == "cogvideox"
        assert result.metadata["synthetic_memory_cue"] is True
        assert result.width == 640 and result.height == 480


def test_provider_propagates_configured_seed_with_injected_generator():
    with TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        reference = tmp_path / "reference.jpg"
        reference.write_bytes(b"test")
        pipeline = FakePipeline()
        seen = []
        provider = TestProvider(
            CogVideoXConfig(seed=123, asset_root=str(tmp_path)),
            pipeline=pipeline,
            image_loader=lambda path: FakeImage(),
            generator_factory=lambda seed, device: seen.append((seed, device)) or "seeded-generator",
        )
        provider.generate(MediaGenerationRequest.from_dict({**request().to_dict(), "reference_asset": reference.name}))
        assert seen == [(123, "cpu")]
        assert pipeline.calls[0]["generator"] == "seeded-generator"


def test_step11_school_scene_integrates_with_fake_provider():
    scene = next(item for item in load_scenes() if item.scene_id == "chapter_04_scene_01")
    candidate = MemoryCandidate.from_scene(scene)
    media_request = MediaPromptBuilder().build(candidate, "P001", life_stage="childhood")
    assert media_request.reference_asset == "04_school_morning/school_01_morning_route.jpg"
    pipeline = FakePipeline()
    provider = TestProvider(
        CogVideoXConfig(seed=None, asset_root=str(Path.cwd() / "Patient story image")),
        pipeline=pipeline,
        image_loader=lambda path: FakeImage(),
    )
    result = provider.generate(media_request)
    assert result.request_id == media_request.request_id
    assert pipeline.calls[0]["prompt"] == media_request.video_prompt


def test_missing_optional_runtime_has_clear_error():
    with TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        reference = tmp_path / "reference.jpg"
        reference.write_bytes(b"test")
        provider = CogVideoXProvider(CogVideoXConfig(seed=None, asset_root=str(tmp_path)))
        try:
            provider.generate(MediaGenerationRequest.from_dict({**request().to_dict(), "reference_asset": reference.name}))
        except CogVideoXUnavailableError as error:
            assert "torch" in str(error) or "diffusers" in str(error)
