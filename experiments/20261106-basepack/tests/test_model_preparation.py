"""Model preparation records actual bytes only after official verification."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def preparation():
    path = Path(__file__).resolve().parents[1] / "examples" / "prepare_embedding_model.py"
    spec = importlib.util.spec_from_file_location("prepare_embedding_model", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_verification_precedes_lock_with_relative_paths(preparation, monkeypatch, tmp_path):
    model = tmp_path / "模型目录" / "model"
    (model / "1_Pooling").mkdir(parents=True)
    (model / "1_Pooling" / "config.json").write_bytes(b"abc")
    (model / ".cache").mkdir()
    (model / ".cache" / "metadata").write_bytes(b"local download state")
    (model / ".gitattributes").write_bytes(b"Hub metadata")
    calls = []

    def official_cli(command, *, check):
        assert check
        calls.append(command)
        assert not (model.parent / "model.lock.json").exists()

    monkeypatch.setattr(preparation.subprocess, "run", official_cli)
    lock = preparation.prepare(model.parent, "official-hf.exe")
    assert [command[1:3] for command in calls] == [["download", preparation.MODEL], ["cache", "verify"]]
    assert calls[1][-2:] == ["--fail-on-missing-files", "--fail-on-extra-files"]
    assert json.loads(lock.read_text(encoding="utf-8")) == {
        "model": preparation.MODEL, "hf_revision": preparation.REVISION,
        "files": [{"path": "model/1_Pooling/config.json", "bytes": 3,
                   "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}],
    }


def test_failed_official_verification_preserves_existing_lock(preparation, monkeypatch, tmp_path):
    lock = tmp_path / "model.lock.json"
    lock.write_text("previous lock", encoding="utf-8")

    def official_cli(command, *, check):
        if command[1:3] == ["cache", "verify"]:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(preparation.subprocess, "run", official_cli)
    with pytest.raises(subprocess.CalledProcessError):
        preparation.prepare(tmp_path)
    assert lock.read_text(encoding="utf-8") == "previous lock"
