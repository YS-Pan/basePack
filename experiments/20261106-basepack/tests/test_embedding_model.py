"""Input budgets must fail before the model performs inference."""
import json
from unittest.mock import Mock

import pytest

from basepack.embedding.qwen3_vl import Qwen3VLEmbedder, resolve_device


@pytest.fixture
def options(tmp_path):
    (tmp_path / "model.lock.json").write_text(json.dumps({
        "model": "Qwen/Qwen3-VL-Embedding-2B", "hf_revision": "fixture", "files": [],
    }), encoding="utf-8")
    return {"model_root": str(tmp_path), "device": "auto", "cpu_threads": 2,
            "max_pixels": 1048576, "max_length": 2048, "batch_size": 4}


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


def test_oversized_token_batch_fails_before_torch_module_forward():
    import torch

    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.options = {"max_length": 4}

    class Inference(torch.nn.Module):
        calls = 0

        def forward(self, features):
            self.calls += 1
            return features

    inference = Inference()
    inference.register_forward_pre_hook(model._check_token_budget)
    inference({"attention_mask": torch.tensor([[1, 1, 1, 0]])})
    with pytest.raises(ValueError, match=r"actual tokens \[5\].*no forward performed"):
        inference({"attention_mask": torch.ones((1, 5), dtype=torch.long)})
    assert inference.calls == 1


def test_animated_image_is_rejected_before_encode(tmp_path):
    from PIL import Image

    image = tmp_path / "animated.gif"
    Image.new("RGB", (16, 16), "red").save(image, save_all=True,
        append_images=[Image.new("RGB", (16, 16), "blue")], duration=100, loop=0)
    model = Qwen3VLEmbedder.__new__(Qwen3VLEmbedder)
    model.Image = Image
    model.model = Mock()
    with pytest.raises(ValueError, match="static frame"):
        model.embed([{"image": str(image)}])
    model.model.encode.assert_not_called()
