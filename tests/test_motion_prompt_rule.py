from backend.app.api.generation import _build_motion_prompt
from backend.app.models.beat import StoryBeat
from backend.app.services.pixazo import PixazoVideoService


def test_build_motion_prompt_uses_temporal_sequence():
    beat = StoryBeat(
        id="jasmine_01",
        story_id="jasmine_morning",
        sequence=1,
        image_path="01_jasmine_morning/jasmine_01_door.jpg",
        action="Lakshmi bends down, closes the wooden back door, and returns naturally to standing.",
        motion="Lakshmi bends toward the door, reaches for it, gently pulls it closed, and slowly straightens back up.",
        camera="static",
        motion_sequence=[
            "Lakshmi naturally bends forward toward the door and lowers her upper body",
            "Lakshmi reaches toward the door, grasps it, and gently pulls it closed on its hinges",
            "The door finishes closing, then Lakshmi slowly straightens back up to a natural standing position",
        ],
        motion_constraints=["walking"],
    )

    prompt = _build_motion_prompt(beat)

    assert "Starting from the exact reference image" in prompt
    assert "1. Lakshmi naturally bends forward toward the door" in prompt
    assert "2. Lakshmi reaches toward the door, grasps it, and gently pulls it closed" in prompt
    assert "3. The door finishes closing, then Lakshmi slowly straightens back up" in prompt
    assert "No walking." in prompt
    assert "Each action must finish before the next action begins." in prompt
    assert "Do not jump between moments." in prompt
    assert "The final frame should be a natural continuation" in prompt


def test_quality_pixazo_payload_uses_image_strength_and_prompt_controls(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"request_id": "req_123"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setenv("PIXAZO_API_KEY", "test-key")
    monkeypatch.setattr("requests.post", fake_post)

    service = PixazoVideoService()
    service.submit(
        beat_id="jasmine_01",
        image_url="https://example.com/image.jpg",
        prompt="test prompt",
        duration=6,
        image_strength=1.0,
        guidance_scale=1.0,
        enable_prompt_expansion=False,
        num_frames=121,
        frames_per_second=24,
    )

    assert captured["json"]["image_strength"] == 1.0
    assert captured["json"]["guidance_scale"] == 1.0
    assert captured["json"]["enable_prompt_expansion"] is False
    assert "negative_prompt" in captured["json"]
    assert "ghosting" in captured["json"]["negative_prompt"]
    assert "camera_motion" not in captured["json"]
