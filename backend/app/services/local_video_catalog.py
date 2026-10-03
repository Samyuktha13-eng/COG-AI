from __future__ import annotations

import os
import shutil
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".ogv"}


def _env_dir(*names: str) -> list[Path]:
    paths: list[Path] = []
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            paths.append(Path(value))
    return paths


OUTPUT_CANDIDATES = [
    *_env_dir("GENERATED_VIDEOS_DIR", "OUTPUTS_DIR"),
    PROJECT_ROOT / "cogniv-ai" / "outputs",
    PROJECT_ROOT / "outputs",
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
        if candidate.exists() and any(
            path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
            for path in candidate.rglob("*")
        ):
            return candidate.resolve()
    for candidate in OUTPUT_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    return (PROJECT_ROOT / "outputs").resolve()


def _seed_bundled_videos(target_root: Path, source_root: Path) -> None:
    if not source_root.is_dir():
        return
    for source in source_root.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        destination = target_root / source.relative_to(source_root)
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _guess_story_id(relative_path: str, folder_name: str, stem: str) -> str | None:
    def match_name(value: str, prefix_only: bool = False) -> str | None:
        tokens = _normalize_name(value).split("_")
        aliases = sorted(_STORY_NAME_ALIASES, key=lambda alias: (len(alias.split("_")), len(alias)), reverse=True)
        for alias in aliases:
            alias_tokens = alias.split("_")
            starts = (0,) if prefix_only else range(max(0, len(tokens) - len(alias_tokens) + 1))
            for start in starts:
                if tokens[start:start + len(alias_tokens)] == alias_tokens:
                    return _STORY_NAME_ALIASES[alias]
        return None

    story_id = match_name(folder_name)
    if story_id:
        return story_id

    for parent in reversed(Path(relative_path).parts[:-1]):
        story_id = match_name(parent)
        if story_id:
            return story_id

    return match_name(stem, prefix_only=True)


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
    from ..data.stories import get_all_stories

    root = Path(output_root) if output_root is not None else _find_output_root()
    root = root.resolve()
    catalog: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    canonical_beats = {
        story.id: {beat.id for beat in story.beats}
        for story in get_all_stories()
    }

    if not root.exists():
        return {}

    video_files = (
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    for video_file in sorted(video_files):
        relative_path = video_file.relative_to(root).as_posix()
        story_id = _guess_story_id(relative_path, video_file.parent.name, video_file.stem)
        if story_id is None:
            continue

        beat_id = _guess_beat_id(story_id, video_file.stem)
        if beat_id is None or beat_id not in canonical_beats.get(story_id, set()):
            continue

        catalog[story_id][beat_id] = {
            "path": relative_path,
            "filename": video_file.name,
            "url": f"/generated-videos/{relative_path}",
        }

    return {story_id: dict(beats) for story_id, beats in sorted(catalog.items())}


def get_generated_video_catalog() -> dict[str, dict[str, dict[str, str]]]:
    return _build_generated_video_catalog(_find_output_root())
