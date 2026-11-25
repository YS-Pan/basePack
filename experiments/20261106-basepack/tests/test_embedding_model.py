"""Input budgets must fail before the model performs inference."""
import json
from unittest.mock import Mock
from contextlib import contextmanager

import pytest

from basepack.embedding.qwen3_vl import (
    SUPPORTED_CONTEXT_TOKENS, EmbeddingInputError, EmbeddingTokenLimitError,
    Qwen3VLEmbedder, normalize_input, resolve_device,
)


@pytest.fixture
def options(tmp_path):
    (tmp_path / "model.lock.json").write_text(json.dumps({
        "model": "Qwen/Qwen3-VL-Embedding-2B", "hf_revision": "fixture", "files": [],
    }), encoding="utf-8")
    return {"model_root": str(tmp_path), "device": "auto", "cpu_threads": 2,
            "max_pixels": 1048576, "batch_size": 4}


def test_auto_cpu_loads_same_precision_without_cuda_budget(options, monkeypatch):
    import torch
    import sentence_transformers

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    cuda = Mock(side_effect=AssertionError("CPU must not initialize CUDA"))
    monkeypatch.setattr(torch.cuda, "set_device", cuda)
    transformer = Mock()
    factory = Mock(return_value=[transformer])
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", factory)
    encoder = Qwen3VLEmbedder(options)
    assert encoder.device == "cpu"
    assert factory.call_args.kwargs["device"] == "cpu"
    assert factory.call_args.kwargs["model_kwargs"]["dtype"] == torch.float16
    transformer.register_forward_pre_hook.assert_called_once()
    cuda.assert_not_called()


def test_auto_prefers_available_cuda_and_respects_explicit_cpu(monkeypatch):
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert str(resolve_device("auto")) == "cuda:0"
    assert str(resolve_device("cpu")) == "cpu"


def test_explicit_cuda_keeps_native_initialization_error(options, monkeypatch):
    import torch

    def unavailable(device):
        raise RuntimeError("native CUDA initialization failed")

    monkeypatch.setattr(torch.cuda, "set_device", unavailable)
    with pytest.raises(RuntimeError, match="native CUDA initialization failed"):
        Qwen3VLEmbedder(options | {"device": "cuda:0", "gpu_memory_mib": 9216})


def test_cuda_loads_without_a_positive_hard_budget(options, monkeypatch):
    import torch
    import sentence_transformers

    monkeypatch.setattr(torch.cuda, "set_device", Mock())
    hard_limit = Mock(side_effect=AssertionError("soft target must not cap the allocator"))
    monkeypatch.setattr(torch.cuda, "set_per_process_memory_fraction", hard_limit)
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", Mock(return_value=[Mock()]))
    encoder = Qwen3VLEmbedder(options | {"device": "cuda:0", "gpu_memory_mib": 0})
    assert encoder.device == "cuda:0"
    hard_limit.assert_not_called()


def test_auto_cpu_litserve_startup_needs_no_nvidia_smi(options, monkeypatch):
    from types import SimpleNamespace

    import torch
    import litserve.connector
    from basepack.embedding import service

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(litserve.connector, "check_cuda_with_nvidia_smi",
                        Mock(side_effect=AssertionError("CPU must not probe nvidia-smi")))
    runs = []
    monkeypatch.setattr(service.LitServer, "run", lambda self, **kwargs: runs.append((self, kwargs)))
    machine = SimpleNamespace(raw={"embedding": options | {"endpoint": "http://127.0.0.1:8765", "queue_timeout": 60}},
                              path_value=lambda section, key: options["model_root"])
    service.serve(machine)
    server, run = runs[0]
    assert server._connector.accelerator == "cpu"
    assert server._connector.devices == 1
    assert run["port"] == 8765
    metadata = server.model_metadata
    assert metadata["attention_backend"] == "sdpa_default"
    assert metadata["supported_context_tokens"] == SUPPORTED_CONTEXT_TOKENS
    assert metadata["gpu_memory_semantics"] == "soft_target"


def test_cuda_info_reports_backend_context_and_soft_target(options, monkeypatch):
    from types import SimpleNamespace
    from basepack.embedding import service

    configured = options | {"device": "cuda:0", "endpoint": "http://127.0.0.1:8765",
                            "queue_timeout": 60, "gpu_memory_mib": 9216}
    factory = Mock()
    monkeypatch.setattr(service, "EmbeddingServer", factory)
    service.serve(SimpleNamespace(raw={"embedding": configured},
                                  path_value=lambda section, key: options["model_root"]))
    metadata = factory.call_args.kwargs["model_metadata"]
    assert metadata["attention_backend"] == "CUDNN_ATTENTION"
    assert metadata["supported_context_tokens"] == SUPPORTED_CONTEXT_TOKENS
    assert metadata["gpu_memory_mib"] == 9216
    assert metadata["gpu_memory_semantics"] == "soft_target"


def test_oversized_token_batch_fails_before_torch_module_forward():
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)

    class Inference(torch.nn.Module):
        calls = 0

        def forward(self, features):
            self.calls += 1
            return features

    inference = Inference()
    inference.register_forward_pre_hook(model._check_token_budget)
    mask = torch.ones((2, SUPPORTED_CONTEXT_TOKENS + 1), dtype=torch.long)
    mask[0, 3:] = 0
    mask[1, -1] = 0
    inference({"attention_mask": mask})
    mask[1, -1] = 1
    with pytest.raises(ValueError, match=r"actual tokens \[3, 32769\].*no forward performed"):
        inference({"attention_mask": mask})
    assert inference.calls == 1


@pytest.mark.parametrize("suffix", ["gif", "tiff"])
def test_multiframe_image_is_rejected_before_encode(tmp_path, suffix):
    from PIL import Image

    image = tmp_path / f"multiframe.{suffix}"
    Image.new("RGB", (16, 16), "red").save(image, save_all=True,
        append_images=[Image.new("RGB", (16, 16), "blue")])
    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.Image = Image
    model.model = Mock()
    with pytest.raises(ValueError, match="static frame"):
        model.embed([{"image": str(image)}])
    model.model.encode.assert_not_called()


def test_single_frame_tiff_reaches_encode_as_png_equivalent_rgb(tmp_path):
    import torch
    from PIL import Image
    from transformers.image_utils import load_image_as_tensor

    tiff, png = tmp_path / "original.tif", tmp_path / "control.png"
    gray = Image.new("L", (2, 2))
    gray.putdata([0, 21, 140, 255])
    gray.save(tiff)
    gray.convert("RGB").save(png)
    original = tiff.read_bytes()
    source = {"text": "caption", "image": str(tiff)}
    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.Image = Image
    model.device = "cpu"
    model.identity = "same-identity"
    model.model = Mock()
    model.model.encode.return_value = torch.tensor([[1.0]])

    assert model.embed([source])["embedding_identity"] == "same-identity"

    (prepared,) = model.model.encode.call_args.args[0]
    assert source == {"text": "caption", "image": str(tiff)} and tiff.read_bytes() == original
    assert prepared["text"] == "caption" and prepared["image"].mode == "RGB"
    assert torch.equal(load_image_as_tensor(prepared["image"]), load_image_as_tensor(str(png)))


def test_token_error_identifies_original_request_indices_without_retry():
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.options = {"batch_size": 4}
    model.device = "cpu"
    model.model = Mock()
    original = EmbeddingTokenLimitError("actual tokens [32769, 3] exceed supported context; no forward performed")
    model.model.encode.side_effect = original
    model.model.preprocess.side_effect = [
        {"attention_mask": torch.ones((1, count), dtype=torch.long)} for count in (3, 32769)]
    with pytest.raises(EmbeddingInputError, match=r"indices.*\[1\].*counts: \[3, 32769\]") as failure:
        model.embed(["short", "long"])
    assert failure.value.__cause__ is original
    model.model.encode.assert_called_once()


def test_service_reports_known_input_errors_and_preserves_internal_errors():
    from fastapi import HTTPException
    from basepack.embedding.service import EmbeddingAPI

    api = EmbeddingAPI({})
    api.model = Mock()
    invalid = EmbeddingInputError("actual tokens [32769] exceed supported_context_tokens=32768")
    api.model.embed.side_effect = invalid
    with pytest.raises(HTTPException) as failure:
        api.predict(["oversized input"])
    assert failure.value.status_code == 422
    assert failure.value.detail == str(invalid)
    assert failure.value.__cause__ is invalid
    internal = ValueError("unexpected model failure")
    api.model.embed.side_effect = internal
    with pytest.raises(ValueError) as failure:
        api.predict(["valid input"])
    assert failure.value is internal


def test_long_text_has_no_byte_limit():
    text = "长" * 22000
    assert len(text.encode("utf-8")) > 64 * 1024
    assert normalize_input(text) == {"text": text}


@pytest.mark.parametrize("has_image,expected_batch", [(False, 4), (True, 1)])
def test_cuda_selects_only_cudnn_and_keeps_request_batching(tmp_path, monkeypatch, has_image, expected_batch):
    import torch
    from PIL import Image

    selected = []

    @contextmanager
    def backend_context(backend):
        selected.append(backend)
        yield
        selected.pop()

    monkeypatch.setattr(torch.nn.attention, "sdpa_kernel", backend_context)
    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.Image = Image
    model.options = {"batch_size": 4, "gpu_memory_mib": 0}
    model.device = "cuda:0"
    model.identity = "same-identity"
    model.model = Mock()

    def encode(values, **kwargs):
        assert selected == [torch.nn.attention.SDPBackend.CUDNN_ATTENTION]
        assert values == [value]
        assert kwargs["batch_size"] == expected_batch
        return torch.tensor([[1.0]])

    model.model.encode.side_effect = encode
    value = {"text": "caption"}
    if has_image:
        path = tmp_path / "image.png"
        Image.new("RGB", (16, 16), "blue").save(path)
        value["image"] = str(path)
    assert model.embed([value])["embedding_identity"] == "same-identity"
    assert selected == []


@pytest.mark.parametrize("reserved,allocated,target,expected", [
    (10, 4, 9, 1), (9, 4, 9, 0), (10, 10, 9, 0), (10, 4, 0, 0),
])
def test_cuda_releases_only_unused_cache_above_soft_target(monkeypatch, reserved, allocated, target, expected):
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.device = "cuda:0"
    model.options = {"gpu_memory_mib": target}
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: reserved * 1024**2)
    monkeypatch.setattr(torch.cuda, "memory_allocated", lambda device: allocated * 1024**2)
    empty = Mock()
    monkeypatch.setattr(torch.cuda, "empty_cache", empty)
    model.release_unused_cache()
    assert empty.call_count == expected


@pytest.mark.parametrize("target", [0, 9216])
def test_idle_cuda_releases_cache_below_or_without_soft_target(monkeypatch, target):
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.device = "cuda:0"
    model.options = {"gpu_memory_mib": target}
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: 10 * 1024**2)
    monkeypatch.setattr(torch.cuda, "memory_allocated", lambda device: 4 * 1024**2)
    empty = Mock()
    monkeypatch.setattr(torch.cuda, "empty_cache", empty)
    model.release_unused_cache(idle=True)
    empty.assert_called_once_with()


def test_cpu_encode_preserves_model_error_without_cuda_access(monkeypatch):
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.device = "cpu"
    model.options = {"batch_size": 4}
    model.model = Mock()
    original = RuntimeError("native model failure")
    model.model.encode.side_effect = original
    monkeypatch.setattr(torch.nn.attention, "sdpa_kernel", Mock(side_effect=AssertionError("CPU backend unchanged")))
    monkeypatch.setattr(torch.cuda, "memory_reserved", Mock(side_effect=AssertionError("CPU must not access CUDA")))
    with pytest.raises(RuntimeError) as failure:
        model.embed(["input"])
    assert failure.value is original
    model.model.encode.assert_called_once()


def test_cuda_unsupported_backend_preserves_original_error_without_retry(monkeypatch):
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.device = "cuda:0"
    model.options = {"batch_size": 4, "gpu_memory_mib": 0}
    model.model = Mock()
    original = RuntimeError("No available kernel. Aborting execution.")
    model.model.encode.side_effect = original
    with pytest.raises(RuntimeError) as failure:
        model.embed(["input"])
    assert failure.value is original
    model.model.encode.assert_called_once()
