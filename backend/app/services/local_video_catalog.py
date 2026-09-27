from __future__ import annotations

from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_CANDIDATES = [
    PROJECT_ROOT / "outputs",
    PROJECT_ROOT / "cogniv-ai" / "outputs",
]

_STORY_NAME_ALIASES = {
    "jasmine": "jasmine_morning",
    "jasmine_morning": "jasmine_morning",
    "mango": "mango_tree",
    "mango_tree": "mango_tree",
    "rain": "rainy_day_kitchen",
    "rainy": "rainy_day_kitchen",
    "rainy_day": "rainy_day_kitchen",
    "rainy_day_kitchen": "rainy_day_kitchen",
    "school": "school_morning",
    "school_morning": "school_morning",
    "railway": "railway_station",
    "station": "railway_station",
    "railway_station": "railway_station",
    "reminder": "care_reminders",
    "reminders": "care_reminders",
    "care_reminder": "care_reminders",
    "care_reminders": "care_reminders",
}


def _normalize_name(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")


def _find_output_root() -> Path:
    for candidate in OUTPUT_CANDIDATES:
        if candidate.exists() and any(candidate.rglob("*.mp4")):
            return candidate.resolve()
    for candidate in OUTPUT_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    return (PROJECT_ROOT / "outputs").resolve()


def _guess_story_id(relative_path: str, folder_name: str, stem: str) -> str | None:
    haystacks = [relative_path, folder_name, stem]
    joined = " ".join(_normalize_name(item) for item in haystacks)

    for key, story_id in _STORY_NAME_ALIASES.items():
        if key in joined:
            return story_id

    for clue in ("jasmine", "mango", "rain", "school", "station", "railway", "reminder"):
        if clue in joined:
            return _STORY_NAME_ALIASES.get(clue)

    return None


def _guess_beat_id(story_id: str, stem: str) -> str | None:
    normalized = _normalize_name(stem)
    base = normalized

    if "_key" in base:
        base = base.rsplit("_key", 1)[0]
    if "_story" in base:
        base = base.rsplit("_story", 1)[0]
    if "_lift" in base:
        base = base.rsplit("_lift", 1)[0]
    if "_first_test" in base:
        base = base.rsplit("_first_test", 1)[0]
    if "_after_fix" in base:
        base = base.rsplit("_after_fix", 1)[0]

    pieces = base.split("_")
    if len(pieces) >= 2 and pieces[0] in {"jasmine", "mango", "rain", "school", "railway", "station"} and pieces[1].isdigit():
        canonical_prefix = pieces[0]
        if canonical_prefix == "station":
            canonical_prefix = "railway"
        return f"{canonical_prefix}_{pieces[1]}"

    digits = "".join(ch for ch in normalized if ch.isdigit())
    if story_id == "jasmine_morning" and normalized.startswith("jasmine_"):
        return normalized if "_" in normalized else f"jasmine_{digits or '01'}"
    if story_id == "mango_tree" and normalized.startswith("mango_"):
        return normalized if "_" in normalized else f"mango_{digits or '01'}"
    if story_id == "rainy_day_kitchen" and normalized.startswith("rain_"):
        return normalized if "_" in normalized else f"rain_{digits or '01'}"
    if story_id == "school_morning" and normalized.startswith("school_"):
        return normalized if "_" in normalized else f"school_{digits or '01'}"
    if story_id == "railway_station" and normalized.startswith("railway_"):
        return normalized if "_" in normalized else f"railway_{digits or '01'}"
    if story_id == "care_reminders" and normalized.startswith("reminder_"):
        return normalized

    return base if base else normalized


def _build_generated_video_catalog(output_root: str | Path | None = None) -> dict[str, dict[str, dict[str, str]]]:
    root = Path(output_root) if output_root is not None else _find_output_root()
    root = root.resolve()
    catalog: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    if not root.exists():
        return {}

    for mp4_file in sorted(root.rglob("*.mp4")):
        relative_path = mp4_file.relative_to(root).as_posix()
        story_id = _guess_story_id(relative_path, mp4_file.parent.name, mp4_file.stem)
        if story_id is None:
            continue

        beat_id = _guess_beat_id(story_id, mp4_file.stem)
        if beat_id is None:
            continue

        catalog[story_id][beat_id] = {
            "path": relative_path,
            "filename": mp4_file.name,
            "url": f"/generated-videos/{relative_path}",
        }

    return {story_id: dict(beats) for story_id, beats in sorted(catalog.items())}


def get_generated_video_catalog() -> dict[str, dict[str, dict[str, str]]]:
    return _build_generated_video_catalog(_find_output_root())
