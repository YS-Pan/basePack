"""Vector semantics, independent of service deployment and request limits."""

import hashlib
import json
from pathlib import Path


DTYPE = "float16"
INSTRUCTION = "Represent the user's input."
MIN_PIXELS = 4096
PREPROCESSING_VERSION = "basepack-v1"
POOLING_VERSION = "last-attended-token-l2-v1"


def embedding_identity(embedding_settings: dict) -> str:
    root = Path(embedding_settings["model_root"])
    manifest = json.loads((root / "model.lock.json").read_text(encoding="utf-8"))
    semantics = {
        "model": manifest["model"],
        "revision": manifest["hf_revision"],
        "files": sorted(manifest["files"], key=lambda item: item["path"]),
        "dtype": DTYPE,
        "instruction": INSTRUCTION,
        "preprocessing": PREPROCESSING_VERSION,
        "min_pixels": MIN_PIXELS,
        "max_pixels": embedding_settings["max_pixels"],
        "pooling": POOLING_VERSION,
    }
    return "Qwen3-VL:" + hashlib.sha256(json.dumps(semantics, sort_keys=True).encode()).hexdigest()
