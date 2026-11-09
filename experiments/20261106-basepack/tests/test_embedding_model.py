"""Input budgets must fail before the model performs inference."""
from unittest.mock import Mock

import pytest

from basepack.embedding.qwen3_vl import Qwen3VLEmbedder


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
