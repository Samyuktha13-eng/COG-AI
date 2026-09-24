from __future__ import annotations

from pathlib import Path

from media_generation.providers.ltx_bf16_multiscale_provider import (
    LTXBF16MultiScaleConfig,
    LTXVideoValidator,
    VideoGenerationGate,
)


def test_video_gate_selects_safe_profile() -> None:
    gate = VideoGenerationGate(LTXBF16MultiScaleConfig())
    profile = gate.select_profile("safe")

    assert profile["profile"] == "safe"
    assert profile["num_frames"] == 17
    assert profile["fps"] == 8


def test_validator_rejects_missing_file() -> None:
    validator = LTXVideoValidator()
    missing = Path("does_not_exist.mp4")

    result = validator.validate(missing)

    assert result["status"] == "fail"
    assert "missing" in result["reason"].lower()
