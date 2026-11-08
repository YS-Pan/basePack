"""The old VL runtime reduced to fixed local text/image inference.

Model wrapper, conversation template and pooling derive from Qwen's Apache-2.0
qwen3_vl_embedding.py, revision 393e2978d27852b0d0230d6994f37f9c15bed73c.
Strict preprocessing/batching derive from the project's earlier VL runtime.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
from pathlib import Path
import time

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
        import torch.nn.functional as functional
        from PIL import Image
        from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLPreTrainedModel, Qwen3VLModel
        from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor
        from qwen_vl_utils.vision_process import process_vision_info

        self.torch, self.functional, self.Image = torch, functional, Image
        self.vision_process = process_vision_info
        self.options = options
        self.device = torch.device(self.options["device"])
        if self.device.type != "cuda" or not torch.cuda.is_available():
            raise RuntimeError("embedding requires the configured CUDA device")
        torch.set_num_threads(self.options["cpu_threads"])
        torch.cuda.set_device(self.device)
        self.before = self.snapshot()
        budget = self.options["gpu_memory_mib"] * 1024 * 1024
        torch.cuda.set_per_process_memory_fraction(budget / self.before["cuda_total_bytes"], self.device)
        torch.cuda.reset_peak_memory_stats(self.device)
        root = Path(self.options["model_root"])
        manifest = json.loads((root / "model.lock.json").read_text(encoding="utf-8"))
        if manifest["model"] != "Qwen/Qwen3-VL-Embedding-2B":
            raise ValueError("this runtime supports Qwen/Qwen3-VL-Embedding-2B")
        for item in manifest["files"]:
            path = root / item["path"]
            if path.stat().st_size != item["bytes"]:
                raise ValueError(f"model file size differs: {path}")

        class Qwen3VLForEmbedding(Qwen3VLPreTrainedModel):
            _checkpoint_conversion_mapping = {}
            accepts_loss_kwargs = False

            def __init__(self, config):
                super().__init__(config)
                self.model = Qwen3VLModel(config)
                self.post_init()

            def get_input_embeddings(self):
                return self.model.get_input_embeddings()

            def forward(self, **inputs):
                return self.model(**inputs)

        started = time.perf_counter()
        self.processor = Qwen3VLProcessor.from_pretrained(root / "model", padding_side="right",
            local_files_only=True, trust_remote_code=False)
        self.model = Qwen3VLForEmbedding.from_pretrained(root / "model", local_files_only=True,
            trust_remote_code=False, use_safetensors=True, dtype=getattr(torch, DTYPE),
            device_map={"": str(self.device)}, low_cpu_mem_usage=True, attn_implementation="sdpa")
        self.model.eval()
        self.model.config.use_cache = False
        torch.cuda.synchronize(self.device)
        self.identity = embedding_identity(self.options)
        self.loaded = {"pid": os.getpid(), "embedding_identity": self.identity,
            "model_load_seconds": time.perf_counter() - started, "load_count": 1,
            "actual_devices": sorted({str(p.device) for p in self.model.parameters()}),
            "actual_dtypes": sorted({str(p.dtype) for p in self.model.parameters() if p.is_floating_point()}),
            "gpu_before": self.before, "gpu_after_load": self.snapshot()}

    def snapshot(self):
        torch = self.torch
        free, total = torch.cuda.mem_get_info(self.device)
        return {"allocated_bytes": torch.cuda.memory_allocated(self.device),
            "reserved_bytes": torch.cuda.memory_reserved(self.device),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(self.device),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(self.device),
            "cuda_free_bytes": free, "cuda_total_bytes": total,
            "cuda_memory_scope": "torch.cuda.mem_get_info; WDDM can expose a process-local view"}

    def prepare(self, value):
        content, receipt = [], None
        if "image" in value:
            path = Path(value["image"])
            if path.stat().st_size > MAX_IMAGE_BYTES:
                raise ValueError("image exceeds 32 MiB")
            with self.Image.open(path) as original:
                if original.width * original.height > MAX_SOURCE_PIXELS or getattr(original, "n_frames", 1) != 1:
                    raise ValueError("image must be a static frame with at most 40 million source pixels")
                original.load()
                image = original.copy()
            content.append({"type": "image", "image": image,
                            "min_pixels": MIN_PIXELS, "max_pixels": self.options["max_pixels"]})
            receipt = {"decoded": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "source_size": [image.width, image.height], "bytes": path.stat().st_size}
        if value.get("text"):
            content.append({"type": "text", "text": value["text"]})
        conversation = [{"role": "system", "content": [{"type": "text", "text": INSTRUCTION}]},
                        {"role": "user", "content": content}]
        return conversation, receipt

    def encode_batch(self, values, *, tokens_only=False):
        prepared = [self.prepare(value) for value in values]
        conversations = [item[0] for item in prepared]
        try:
            text = self.processor.apply_chat_template(conversations, add_generation_prompt=True, tokenize=False)
            images, videos, kwargs = self.vision_process(conversations, image_patch_size=16,
                return_video_metadata=True, return_video_kwargs=True)
            expected_images = sum("image" in value for value in values)
            if videos is not None or expected_images and (images is None or len(images) != expected_images):
                raise ValueError("all original images must reach the processor; video unsupported")
            inputs = self.processor(text=text, images=images, videos=None, truncation=False,
                padding=True, do_resize=False, return_tensors="pt", **kwargs)
            counts = inputs["attention_mask"].sum(dim=1).tolist()
            if any(count > self.options["max_length"] for count in counts):
                raise ValueError(f"actual tokens {counts} exceed max_length={self.options['max_length']}; no forward performed")
            grid = inputs.get("image_grid_thw")
            visual_tokens = 0 if grid is None else int(grid.prod(dim=1).sum().item()) // 4
            if expected_images and (visual_tokens == 0 or "pixel_values" not in inputs):
                raise ValueError("image produced no visual pixels/tokens")
            started = time.time()
            vectors = [None] * len(values)
            if not tokens_only:
                with self.torch.inference_mode():
                    inputs = {key: value.to(self.device) for key, value in inputs.items()}
                    output = self.model(**inputs).last_hidden_state
                    mask = inputs["attention_mask"]
                    columns = mask.shape[1] - mask.flip(dims=[1]).argmax(dim=1) - 1
                    rows = self.torch.arange(output.shape[0], device=output.device)
                    pooled = output[rows, columns]
                    normalized = self.functional.normalize(pooled.float(), p=2, dim=-1)
                    vectors = normalized.cpu().tolist()
                    self.torch.cuda.synchronize(self.device)
                    del output, pooled, normalized
            ended = time.time()
            receipts = []
            for index, ((_, image_receipt), count) in enumerate(zip(prepared, counts)):
                receipt = {"raw_tokens": count, "used_tokens": count, "truncated": False,
                    "actual_batch_size": len(values), "batch_index": index,
                    "batch_padded_tokens": max(counts), "forward_performed": not tokens_only,
                    "started_at": started, "finished_at": ended, "gpu": self.snapshot()}
                if image_receipt:
                    receipt["image"] = {**image_receipt, "visual_tokens": visual_tokens,
                        "resized_sizes": [[image.width, image.height] for image in images]}
                receipts.append(receipt)
            return vectors, receipts
        finally:
            for conversation in conversations:
                for item in conversation[1]["content"]:
                    if item["type"] == "image":
                        item["image"].close()

    def embed(self, values, *, tokens_only=False, cancelled=None):
        if not 1 <= len(values) <= MAX_REQUEST_INPUTS:
            raise ValueError("embedding request must contain 1 to 8 inputs")
        values = [normalize_input(value) for value in values]
        batch_size = self.options["batch_size"] if all("image" not in value for value in values) else 1
        vectors, receipts = [], []
        for start in range(0, len(values), batch_size):
            if cancelled is not None and cancelled():
                return None
            batch_vectors, batch_receipts = self.encode_batch(values[start:start + batch_size], tokens_only=tokens_only)
            vectors.extend(batch_vectors)
            receipts.extend(batch_receipts)
        return {"pid": os.getpid(), "embedding_identity": self.identity, "inputs": receipts,
                "vectors": vectors, "loaded": self.loaded}

    def close(self):
        self.model = None
        self.processor = None
        gc.collect()
        self.torch.cuda.empty_cache()
