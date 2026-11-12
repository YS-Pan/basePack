"""Local Qwen3-VL encoding through Sentence Transformers."""
from __future__ import annotations

import os
from pathlib import Path

from .identity import DTYPE, INSTRUCTION, MIN_PIXELS, embedding_identity

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_TEXT_BYTES = 64 * 1024
MAX_REQUEST_INPUTS = 8


class EmbeddingInputError(ValueError):
    """An input exceeds the encoder's published contract."""


class EmbeddingTokenLimitError(EmbeddingInputError):
    """The actual preprocessed input exceeds the configured token budget."""


def resolve_device(configured: str):
    import torch

    if configured == "auto":
        configured = "cuda:0" if torch.cuda.is_available() else "cpu"
    return torch.device(configured)


def normalize_input(value):
    if isinstance(value, str):
        value = {"text": value}
    if not isinstance(value, dict) or not set(value) <= {"text", "image"}:
        raise EmbeddingInputError("input must be text or {text, image}; one local image per input")
    if not value.get("text", "").strip() and not value.get("image"):
        raise EmbeddingInputError("empty embedding input")
    if len(value.get("text", "").encode("utf-8")) > MAX_TEXT_BYTES:
        raise EmbeddingInputError("text exceeds 64 KiB")
    if "image" in value and not Path(value["image"]).is_absolute():
        raise EmbeddingInputError("image must be an absolute local path")
    return value


class Qwen3VLEmbedder:
    def __init__(self, options: dict):
        import torch
        from PIL import Image
        from sentence_transformers import SentenceTransformer

        self.Image = Image
        self.options = options
        device = resolve_device(options["device"])
        self.device = str(device)
        torch.set_num_threads(options["cpu_threads"])
        if device.type == "cuda":
            budget = options["gpu_memory_mib"]
            if budget <= 0:
                raise ValueError("CUDA embedding requires a measured positive gpu_memory_mib budget")
            torch.cuda.set_device(device)
            total = torch.cuda.get_device_properties(device).total_memory
            torch.cuda.set_per_process_memory_fraction(budget * 1024**2 / total, device)
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
            raise EmbeddingTokenLimitError(
                f"actual tokens {counts} exceed max_length={self.options['max_length']}; "
                "no forward performed. Shorten summaries or split source chunks at semantic boundaries; "
                "inputs are never truncated.")

    def embed(self, values):
        if not 1 <= len(values) <= MAX_REQUEST_INPUTS:
            raise EmbeddingInputError("embedding request must contain 1 to 8 inputs")
        values = [normalize_input(value) for value in values]
        for value in values:
            if "image" in value:
                path = Path(value["image"])
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise EmbeddingInputError("image exceeds 32 MiB")
                with self.Image.open(path) as image:
                    if image.width * image.height > MAX_SOURCE_PIXELS or getattr(image, "n_frames", 1) != 1:
                        raise EmbeddingInputError("image must be a static frame with at most 40 million source pixels")
                    image.verify()
        batch_size = 1 if any("image" in value for value in values) else self.options["batch_size"]
        try:
            vectors = self.model.encode(values, batch_size=batch_size,
                                        prompt=INSTRUCTION, show_progress_bar=False)
        except EmbeddingTokenLimitError as error:
            # Encode sorts its inference batches. On failure only, resolve the
            # original request indices with the same preprocessing and prompt.
            counts = [int(self.model.preprocess([value], prompt=INSTRUCTION)
                          ["attention_mask"].sum().item()) for value in values]
            oversized = [index for index, count in enumerate(counts)
                         if count > self.options["max_length"]]
            raise EmbeddingInputError(
                f"{error} Request input indices exceeding the limit (0-based): {oversized}; "
                f"request token counts: {counts}.") from error
        return {"pid": os.getpid(), "embedding_identity": self.identity, "vectors": vectors.tolist()}
