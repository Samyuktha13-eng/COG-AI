import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env", override=True)

PIXAZO_API_KEY = os.getenv("PIXAZO_API_KEY", "")
PIXAZO_IMAGE_TO_VIDEO_ENDPOINT = os.getenv(
    "PIXAZO_IMAGE_TO_VIDEO_ENDPOINT",
    "https://gateway.pixazo.ai/ltx-video/v1/image-to-video",
)

GENERATED_DIR = BASE_DIR / "content" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
