"""Vector semantics, independent of service deployment and request limits."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path


DTYPE = "float16"
INSTRUCTION = "Represent the user's input."
MIN_PIXELS = 4096
PREPROCESSING_VERSION = "sentence-transformers-chat-template-v2"
POOLING_VERSION = "sentence-transformers-lasttoken-fp16-l2-v2"


def embedding_identity(embedding_settings: dict) -> str:
    root = Path(embedding_settings["model_root"])
    manifest = json.loads((root / "model.lock.json").read_text(encoding="utf-8"))
    semantics = {
        "model": manifest["model"],
        "revision": manifest["hf_revision"],
        "files": sorted(manifest["files"], key=lambda item: item["path"]),
        "dtype": DTYPE,
        "sentence_transformers": version("sentence-transformers"),
        "instruction": INSTRUCTION,
        "preprocessing": PREPROCESSING_VERSION,
        "min_pixels": MIN_PIXELS,
        "max_pixels": embedding_settings["max_pixels"],
        "pooling": POOLING_VERSION,
    }
    return "Qwen3-VL:" + hashlib.sha256(json.dumps(semantics, sort_keys=True).encode()).hexdigest()
