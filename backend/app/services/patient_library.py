import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models.patient_folder import FolderAsset, FolderAssetType, PatientFolder
from ..models.story_build import BuildStatus, StoryBuild
from ..models.video_job import VideoJob, VideoJobStatus
from ..data.stories import get_all_stories
from .phase1 import PATIENTS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PATIENT_LIBRARY_ROOT = PROJECT_ROOT / "outputs" / "patient_library"
INDEX_PATH = PATIENT_LIBRARY_ROOT / "index.json"
BUILDS_PATH = PATIENT_LIBRARY_ROOT / "builds.json"
VIDEO_JOBS_PATH = PATIENT_LIBRARY_ROOT / "video_jobs.json"
FOLDERS: dict[str, PatientFolder] = {}
BUILDS: dict[str, StoryBuild] = {}
VIDEO_JOBS: dict[str, VideoJob] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_index() -> None:
    if INDEX_PATH.is_file():
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        for patient_id, payload in data.items():
            FOLDERS[patient_id] = PatientFolder.model_validate(payload)
    if BUILDS_PATH.is_file():
        data = json.loads(BUILDS_PATH.read_text(encoding="utf-8"))
        for bid, payload in data.items():
            BUILDS[bid] = StoryBuild.model_validate(payload)
    if VIDEO_JOBS_PATH.is_file():
        data = json.loads(VIDEO_JOBS_PATH.read_text(encoding="utf-8"))
        for jid, payload in data.items():
            VIDEO_JOBS[jid] = VideoJob.model_validate(payload)


def _save_index() -> None:
    PATIENT_LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps({pid: f.model_dump(mode="json") for pid, f in FOLDERS.items()}, indent=2),
        encoding="utf-8",
    )
    BUILDS_PATH.write_text(
        json.dumps({bid: b.model_dump(mode="json") for bid, b in BUILDS.items()}, indent=2),
        encoding="utf-8",
    )
    VIDEO_JOBS_PATH.write_text(
        json.dumps({jid: j.model_dump(mode="json") for jid, j in VIDEO_JOBS.items()}, indent=2),
        encoding="utf-8",
    )


def get_folder(patient_id: str) -> PatientFolder:
    if patient_id not in PATIENTS:
        raise ValueError("Patient not found")
    if patient_id not in FOLDERS:
        FOLDERS[patient_id] = PatientFolder(patient_id=patient_id)
    return FOLDERS[patient_id]


def _safe_relative_path(relative_path: str, fallback_name: str) -> tuple[str, str]:
    candidate = Path(relative_path or fallback_name)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Invalid relative upload path")
    clean = Path(*[part for part in candidate.parts if part not in {"", "."}])
    if not clean.name:
        clean = Path(fallback_name)
    return clean.as_posix(), clean.name


def _extract_document_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            from io import BytesIO
            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        except Exception:
            return ""
    if suffix == ".docx":
        try:
            from docx import Document
            from io import BytesIO
            return "\n".join(paragraph.text for paragraph in Document(BytesIO(content)).paragraphs)
        except Exception:
            return ""
    return ""


def save_folder_asset(
    patient_id: str,
    asset_type: FolderAssetType,
    filename: str,
    content: bytes,
    relative_path: str | None = None,
    story_reference: str | None = None,
) -> FolderAsset:
    folder = get_folder(patient_id)
    relative, safe_name = _safe_relative_path(relative_path or filename, filename)
    asset_id = str(uuid.uuid4())
    destination = PATIENT_LIBRARY_ROOT / patient_id / asset_type.value / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    asset = FolderAsset(
        asset_id=asset_id,
        patient_id=patient_id,
        type=asset_type,
        name=safe_name,
        path=str(destination),
        relative_path=relative,
        story_reference=story_reference,
        created_at=_now(),
        url="/patient-library/" + destination.relative_to(PATIENT_LIBRARY_ROOT).as_posix(),
    )
    from .mongo_store import persist_asset
    persist_asset(asset, content)
    if asset_type == FolderAssetType.STORY_DOCUMENT:
        folder.documents = [existing for existing in folder.documents if existing.patient_id != patient_id or existing.type != FolderAssetType.STORY_DOCUMENT]
        folder.documents.append(asset)
        folder.document_text = {key: value for key, value in folder.document_text.items() if key not in {item.asset_id for item in folder.documents[:-1]}}
        folder.document_text[asset.asset_id] = _extract_document_text(safe_name, content)
    elif asset_type == FolderAssetType.IMAGE:
        folder.image_assets = [existing for existing in folder.image_assets if existing.patient_id != patient_id or existing.type != FolderAssetType.IMAGE]
        folder.image_assets.append(asset)
    elif asset_type == FolderAssetType.VOICE_STORY:
        if folder.voice_story is not None:
            try:
                Path(folder.voice_story.path).unlink(missing_ok=True)
            except Exception:
                pass
        folder.voice_story = asset
    _save_index()
    return asset


def build_story(patient_id: str) -> StoryBuild:
    folder = get_folder(patient_id)
    all_stories = get_all_stories()
    total_beats = sum(len(s.beats) for s in all_stories)
    now = _now()
    build = StoryBuild(
        build_id=str(uuid.uuid4()),
        patient_id=patient_id,
        status=BuildStatus.PROCESSING,
        documents_found=len(folder.documents),
        images_found=len(folder.image_assets),
        voice_found=int(folder.voice_story is not None),
        chapters_found=len(all_stories),
        image_groups_matched=min(len(all_stories), len(folder.image_assets)) if folder.image_assets else 0,
        narration_prepared=total_beats,
        created_at=now,
        updated_at=now,
    )
    build.status = BuildStatus.COMPLETED
    folder.story_status = "ready"
    folder.game_status = "ready"
    folder.build_id = build.build_id
    folder.build_summary = {
        "documents_found": build.documents_found,
        "images_found": build.images_found,
        "voice_found": build.voice_found,
        "chapters_found": build.chapters_found,
        "image_groups_matched": build.image_groups_matched,
        "narration_prepared": build.narration_prepared,
    }
    BUILDS[build.build_id] = build
    _save_index()
    return build


def uploaded_story_supports_prompt(folder: PatientFolder, prompt: str, story_id: str) -> bool:
    """Require the selected story/topic to appear in uploaded patient material."""
    import re

    source = " ".join([
        *folder.document_text.values(),
        *(asset.name for asset in folder.documents),
        *(asset.story_reference or "" for asset in folder.documents),
    ]).lower()
    if not source.strip():
        return False
    prompt_tokens = [
        token for token in re.sub(r"[^a-z0-9 ]", " ", prompt.lower()).split()
        if len(token) >= 4 and token not in {"show", "tell", "about", "lakshmi", "memory"}
    ]
    story_tokens = [token for token in story_id.replace("_", " ").split() if len(token) >= 4]
    return any(token in source for token in [*prompt_tokens, *story_tokens])


def create_video_job_for_beat(
    patient_id: str,
    story_id: str,
    beat_id: str,
    reference_images: list[str] | None = None,
) -> VideoJob:
    """Create a single VideoJob for one specific beat (used by the grounding pipeline)."""
    folder = get_folder(patient_id)
    if folder.story_status != "ready":
        raise ValueError("Build the patient story before generating videos")
    now = _now()
    job = VideoJob(
        job_id=str(uuid.uuid4()),
        patient_id=patient_id,
        story_id=story_id,
        scene_id=beat_id,
        status=VideoJobStatus.WAITING,
        created_at=now,
        updated_at=now,
    )
    VIDEO_JOBS[job.job_id] = job
    _save_index()
    return job


def create_video_jobs(patient_id: str) -> list[VideoJob]:
    folder = get_folder(patient_id)
    if folder.story_status != "ready":
        raise ValueError("Build the patient story before generating videos")

    jobs: list[VideoJob] = []
    now = _now()
    canonical = {(story.id, beat.id) for story in get_all_stories() for beat in story.beats}
    existing_by_scene: dict[tuple[str, str], VideoJob] = {}
    for job in VIDEO_JOBS.values():
        if job.patient_id != patient_id or (job.story_id, job.scene_id) not in canonical:
            continue
        key = (job.story_id, job.scene_id)
        previous = existing_by_scene.get(key)
        if previous is None or (job.output_path and not previous.output_path) or job.updated_at > previous.updated_at:
            existing_by_scene[key] = job

    for job_id, job in list(VIDEO_JOBS.items()):
        if job.patient_id == patient_id and job.story_id != "care_reminders":
            del VIDEO_JOBS[job_id]

    for story in get_all_stories():
        for beat in story.beats:
            existing = existing_by_scene.get((story.id, beat.id))
            if existing:
                VIDEO_JOBS[existing.job_id] = existing
                jobs.append(existing)
                continue
            job = VideoJob(
                job_id=str(uuid.uuid4()),
                patient_id=patient_id,
                story_id=story.id,
                scene_id=beat.id,
                status=VideoJobStatus.WAITING,
                created_at=now,
                updated_at=now,
            )
            VIDEO_JOBS[job.job_id] = job
            jobs.append(job)
    folder.generation_status = "queued"
    _save_index()
    return jobs


_load_index()
