import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.game import router as game_router
from .api.generation import router as generation_router
from .api.grounding import router as grounding_router
from .api.health import router as health_router
from .api.phase1 import router as phase1_router
from .api.stories import router as stories_router
from .api.system import router as system_router
from .api.voice import router as voice_router
from .services.assets import STORY_IMAGE_ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_dir(*names: str) -> list[Path]:
    paths: list[Path] = []
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            paths.append(Path(value))
    return paths


def _resolved_output_dir(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    for candidate in candidates:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate.resolve()
    fallback = (PROJECT_ROOT / "outputs").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


OUTPUT_ROOT_CANDIDATES = [
    *_env_dir("GENERATED_VIDEOS_DIR", "OUTPUTS_DIR"),
    PROJECT_ROOT / "cogniv-ai" / "outputs",
    PROJECT_ROOT / "outputs",
]

PATIENT_LIBRARY_ROOT = _resolved_output_dir(
    *_env_dir("PATIENT_LIBRARY_DIR"),
    PROJECT_ROOT / "outputs" / "patient_library",
    PROJECT_ROOT / "cogniv-ai" / "outputs" / "patient_library",
)
GENERATED_VIDEOS_ROOT = _resolved_output_dir(*OUTPUT_ROOT_CANDIDATES)
PATIENT_LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
GENERATED_VIDEOS_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Cogniv AI",
    version="0.1.0",
)

configured_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()]
cors_origins = sorted({*configured_origins, "http://127.0.0.1:5173", "http://localhost:5173"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins and cors_origins != ["*"] else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STORY_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

app.mount(
    "/story-images",
    StaticFiles(directory=str(STORY_IMAGE_ROOT)),
    name="story-images",
)

app.mount(
    "/patient-library",
    StaticFiles(directory=str(PATIENT_LIBRARY_ROOT)),
    name="patient-library",
)

app.mount(
    "/generated-videos",
    StaticFiles(directory=str(GENERATED_VIDEOS_ROOT)),
    name="generated-videos",
)

app.include_router(health_router)
app.include_router(stories_router)
app.include_router(generation_router)
app.include_router(grounding_router)
app.include_router(game_router)
app.include_router(voice_router)
app.include_router(system_router)
app.include_router(phase1_router)


@app.get("/")
def root():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")
