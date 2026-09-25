import os
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_story_image_root() -> Path:
    candidates = [
        PROJECT_ROOT / "Patient story image",
        PROJECT_ROOT / "story-images",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    fallback = PROJECT_ROOT / "Patient story image"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


STORY_IMAGE_ROOT = _resolve_story_image_root()
load_dotenv(PROJECT_ROOT / ".env", override=True)


class AssetPublishError(RuntimeError):
    """Raised when a story asset cannot be exposed to the provider."""


class UnsupportedAssetError(AssetPublishError):
    pass


class StoryAssetService:
    supported_extensions = {".jpg", ".jpeg", ".png"}

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("COGNIV_ASSET_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or os.getenv("APP_BASE_URL") or "http://localhost:8000").rstrip("/")

    def publish_image(self, local_path: Path) -> str:
        """Return a deployable public URL for the story image."""
        try:
            resolved_path = local_path.resolve()
            relative_path = resolved_path.relative_to(STORY_IMAGE_ROOT.resolve())
        except ValueError as error:
            raise AssetPublishError("Source image is outside the story asset directory.") from error

        if not resolved_path.is_file():
            raise AssetPublishError("Source image file not found.")
        if resolved_path.suffix.lower() not in self.supported_extensions:
            raise UnsupportedAssetError("Source image must be a JPEG or PNG file.")

        base_url = self.base_url.rstrip("/")
        parsed_url = urlparse(base_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise AssetPublishError(
                "COGNIV_ASSET_BASE_URL/PUBLIC_BASE_URL must include a valid host such as https://yourdomain.com or http://localhost:8000."
            )

        host_root = base_url.rstrip("/")
        if "/story-images" not in host_root:
            host_root = f"{host_root}/story-images"

        encoded_path = "/".join(quote(part) for part in relative_path.parts)
        return f"{host_root}/{encoded_path}"

    def validate_public_image_url(self, image_url: str) -> None:
        try:
            response = requests.get(
                image_url,
                headers={"User-Agent": "CognivAI-AssetValidator/1.0"},
                stream=True,
                timeout=15,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if not content_type.startswith("image/"):
                raise AssetPublishError("Public asset URL does not serve an image.")
        except requests.RequestException as error:
            status = getattr(error.response, "status_code", "timeout")
            raise AssetPublishError(
                f"Public asset URL could not be reached ({status}): {image_url}. "
                "Configure COGNIV_ASSET_BASE_URL/PUBLIC_BASE_URL with a stable public host where /story-images is served."
            ) from error
        finally:
            if "response" in locals():
                response.close()
