import argparse
import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_ID = "bodhan-ai/indic-transcribe-core"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "models" / "indic-conformer-600m-int8"
DEFAULT_CACHE_DIR = Path(
    os.getenv(
        "HF_CACHE_DIR",
        "D:\\cogniv-huggingface" if Path("D:\\").exists() else Path.home() / ".cache" / "huggingface" / "hub",
    )
)

parser = argparse.ArgumentParser(description="Download a local Cogniv ASR model")
parser.add_argument("--repo-id", default=DEFAULT_MODEL_ID)
parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
args = parser.parse_args()

hf_token = os.getenv("HF_TOKEN")

if not hf_token:
    raise RuntimeError(
        "HF_TOKEN was not found in the .env file."
    )

args.output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("HUGGING FACE MODEL DOWNLOAD")
print("=" * 60)
print("Model:", args.repo_id)
print("Destination:", args.output_dir)
print("Cache:", args.cache_dir)
print("Workers: 8")
print()
print("Download starting...")
print("Progress will be shown below.")
print("=" * 60)

model_dir = snapshot_download(
    repo_id=args.repo_id,
    token=hf_token,
    cache_dir=str(args.cache_dir),
    max_workers=8,
    force_download=False
)

# Keep one copy in the Hugging Face cache and expose it at the path used by the app.
args.output_dir.parent.mkdir(parents=True, exist_ok=True)
if args.output_dir.exists() or args.output_dir.is_symlink():
    print("Model link already exists:", args.output_dir)
else:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(args.output_dir), str(model_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Model downloaded to the Hugging Face cache, but the application junction could not be created: "
            + (result.stderr or result.stdout).strip()
        )
    print("Application model path:", args.output_dir)

print()
print("=" * 60)
print("DOWNLOAD COMPLETE")
print("=" * 60)
print("Model directory:")
print(model_dir)
print("=" * 60)
