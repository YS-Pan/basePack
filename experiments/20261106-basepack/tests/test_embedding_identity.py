"""Semantic identity must survive deployment-only changes."""

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from basepack.embedding import identity


@pytest.fixture
def options(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.lock.json").write_text(json.dumps({
        "model": "Qwen/Qwen3-VL-Embedding-2B", "hf_revision": "fixture",
        "files": [{"path": "weights.safetensors", "bytes": 10, "sha256": "fixture"}],
    }), encoding="utf-8")
    return {"model_root": str(model), "device": "cuda:0", "max_length": 2048,
            "batch_size": 4, "max_pixels": 1048576, "idle_seconds": 30,
            "cpu_threads": 2, "gpu_memory_mib": 9216}


def test_runtime_settings_and_model_location_preserve_embedding_identity(options, tmp_path):
    expected = identity.embedding_identity(options)
    moved = tmp_path / "移动后 model"
    shutil.copytree(options["model_root"], moved)
    changed = options | {"model_root": str(moved), "device": "cuda:1", "max_length": 1024,
                         "batch_size": 1, "idle_seconds": 10, "cpu_threads": 1,
                         "gpu_memory_mib": 8000}
    assert identity.embedding_identity(changed) == expected


@pytest.mark.parametrize("setting", ["DTYPE", "INSTRUCTION", "MIN_PIXELS",
                                     "PREPROCESSING_VERSION", "POOLING_VERSION"])
def test_semantic_contract_changes_embedding_identity(options, monkeypatch, setting):
    expected = identity.embedding_identity(options)
    monkeypatch.setattr(identity, setting, "changed")
    assert identity.embedding_identity(options) != expected


def test_image_resize_and_model_revision_change_embedding_identity(options):
    expected = identity.embedding_identity(options)
    assert identity.embedding_identity(options | {"max_pixels": 262144}) != expected
    manifest_path = Path(options["model_root"]) / "model.lock.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["hf_revision"] = "different"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert identity.embedding_identity(options) != expected
    manifest["hf_revision"] = "fixture"
    manifest["files"][0]["sha256"] = "different"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert identity.embedding_identity(options) != expected


def test_sentence_transformers_version_changes_embedding_identity(options, monkeypatch):
    expected = identity.embedding_identity(options)
    monkeypatch.setattr(identity, "version", lambda _: "different")
    assert identity.embedding_identity(options) != expected


def test_model_module_import_has_no_transport_registry_or_model_dependency():
    model_path = Path(identity.__file__).with_name("qwen3_vl.py")
    imports = {node.module for node in ast.walk(ast.parse(model_path.read_text(encoding="utf-8")))
               if isinstance(node, ast.ImportFrom)}
    assert not {"transport", "registry"} & imports
    package_source = str(Path(identity.__file__).resolve().parents[2])
    result = subprocess.run([sys.executable, "-c",
        "import sys; from basepack.embedding.qwen3_vl import Qwen3VLEmbedder; "
        "assert not {'torch', 'transformers', 'sentence_transformers'} & sys.modules.keys()"],
        env=os.environ | {"PYTHONPATH": package_source}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
