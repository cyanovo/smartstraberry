"""Download a pinned public BGE model; the mirror does not receive user documents."""

from pathlib import Path
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[2]
snapshot_download(
    "BAAI/bge-small-zh-v1.5",
    revision="7999e1d3359715c523056ef9478215996d62a620",
    endpoint="https://hf-mirror.com",
    local_dir=ROOT / ".runtime/models/bge-small-zh-v1.5",
    allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"],
    max_workers=3,
)
