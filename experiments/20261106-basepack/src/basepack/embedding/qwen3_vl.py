"""Local Qwen3-VL encoding through Sentence Transformers."""
from __future__ import annotations

import os
from pathlib import Path

from .identity import DTYPE, INSTRUCTION, MIN_PIXELS, embedding_identity

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_TEXT_BYTES = 64 * 1024
MAX_REQUEST_INPUTS = 8


def normalize_input(value):
    if isinstance(value, str):
        value = {"text": value}
    if not isinstance(value, dict) or not set(value) <= {"text", "image"}:
        raise ValueError("input must be text or {text, image}; one local image per input")
    if not value.get("text", "").strip() and not value.get("image"):
        raise ValueError("empty embedding input")
    if len(value.get("text", "").encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("text exceeds 64 KiB")
    if "image" in value and not Path(value["image"]).is_absolute():
        raise ValueError("image must be an absolute local path")
    return value


class Qwen3VLEmbedder:
    def __init__(self, options: dict):
        import torch
        from PIL import Image
        from sentence_transformers import SentenceTransformer

        self.Image = Image
        self.options = options
        device = torch.device(options["device"])
        if device.type != "cuda" or not torch.cuda.is_available():
            raise RuntimeError("embedding requires the configured CUDA device")
        torch.set_num_threads(options["cpu_threads"])
        torch.cuda.set_device(device)
        total = torch.cuda.get_device_properties(device).total_memory
        torch.cuda.set_per_process_memory_fraction(options["gpu_memory_mib"] * 1024**2 / total, device)
        self.model = SentenceTransformer(
            str(Path(options["model_root"]) / "model"),
            device=str(device), local_files_only=True, trust_remote_code=False,
            model_kwargs={"dtype": getattr(torch, DTYPE), "attn_implementation": "sdpa"},
            processor_kwargs={"padding_side": "right"},
            config_kwargs={"use_cache": False},
        )
        self.model[0].processing_kwargs.update({
            "text": {"truncation": False},
            "image": {"size": {"shortest_edge": MIN_PIXELS, "longest_edge": options["max_pixels"]}},
        })
        self.model[0].register_forward_pre_hook(self._check_token_budget)
        self.identity = embedding_identity(options)

    def _check_token_budget(self, module, args):
        counts = args[0]["attention_mask"].sum(dim=1).tolist()
        if any(count > self.options["max_length"] for count in counts):
            raise ValueError(f"actual tokens {counts} exceed max_length={self.options['max_length']}; no forward performed")

    def embed(self, values):
        if not 1 <= len(values) <= MAX_REQUEST_INPUTS:
            raise ValueError("embedding request must contain 1 to 8 inputs")
        values = [normalize_input(value) for value in values]
        for value in values:
            if "image" in value:
                path = Path(value["image"])
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise ValueError("image exceeds 32 MiB")
                with self.Image.open(path) as image:
                    if image.width * image.height > MAX_SOURCE_PIXELS or getattr(image, "n_frames", 1) != 1:
                        raise ValueError("image must be a static frame with at most 40 million source pixels")
                    image.verify()
        batch_size = 1 if any("image" in value for value in values) else self.options["batch_size"]
        vectors = self.model.encode(values, batch_size=batch_size,
                                    prompt=INSTRUCTION, show_progress_bar=False)
        return {"pid": os.getpid(), "embedding_identity": self.identity, "vectors": vectors.tolist()}
