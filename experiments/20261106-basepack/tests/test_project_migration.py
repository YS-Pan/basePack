"""Explicit schema migration preserves project ownership and recoverable evidence."""

import json
import os
from pathlib import Path

import pytest

from basepack.project.config import load_project_config
from basepack.project.migrate import migrate_project


def legacy_project(tmp_path, *, source_name="basepack.toml", memory=".basepack/memory",
                   jobs=".basepack/jobs", schema=1):
    root = tmp_path / "项目 甲"
    source = root / source_name
    source.parent.mkdir(parents=True)
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    python = tmp_path / "chosen runtime" / "python.exe"
    text = (
        f"schema_version = {schema}\n\n[runtime]\n"
        f"python = {json.dumps(str(python))}\n"
        f"machine_config = {json.dumps(str(machine))}\n\n[project]\n"
        f"root = {json.dumps(Path(os.path.relpath(root, source.parent)).as_posix())}\n"
        f"\n[memory]\ndata_dir = {json.dumps(memory)}\n"
        f"\n[resources]\njobs_dir = {json.dumps(jobs)}\n"
        "\n[experiment]\nlabel = 'keep business setting'\nsteps = [1, 2]\nenabled = true\n"
    )
    source.write_text(text, encoding="utf-8")
    return root, source, python, machine


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


def backup_contains(backup, content):
    return any(path.is_file() and path.read_bytes() == content for path in backup.rglob("*"))


@pytest.mark.parametrize("source_name,target_name", [
    ("basepack.toml", ".basepack/config.toml"),
    ("config/深层 old.toml", ".basepack/local/深层 config.toml"),
])
def test_migrate_preserves_root_bindings_data_and_business_entry(tmp_path, monkeypatch, source_name, target_name):
    root, source, python, machine = legacy_project(tmp_path, source_name=source_name)
    memory = root / ".basepack/memory"
    jobs = root / ".basepack/jobs"
    memory.mkdir(parents=True)
    jobs.mkdir()
    data = memory / "project-index.bin"
    data.write_bytes(b"project-owned bytes")
    receipt = jobs / "submission.json"
    receipt.write_text('{"job_id": "12.0"}', encoding="utf-8")
    original_receipt = receipt.read_bytes()
    business = ("# Business\nKeep the business rules.\n<!-- basepack:start -->\n"
                "Old generated instructions.\n<!-- basepack:end -->\nKeep later rules.\n")
    (root / "AGENTS.md").write_text(business, encoding="utf-8")
    original_agents = (root / "AGENTS.md").read_bytes()
    (root / ".gitignore").write_text("/business-cache/\n", encoding="utf-8")
    original_config = source.read_bytes()
    monkeypatch.chdir(tmp_path.parent)

    result = migrate_project(source, target_name)

    target = root / target_name
    config = load_project_config(target)
    assert Path(result["project_config"]) == target
    assert Path(result["project_root"]) == root
    assert config.root == root
    assert config.python == python
    assert config.machine_config == machine
    assert config.raw["schema_version"] == 2
    assert "resources" not in config.raw
    assert config.raw["experiment"] == {"label": "keep business setting", "steps": [1, 2], "enabled": True}
    assert config.memory_dir == memory
    assert config.jobs_dir == jobs
    assert data.read_bytes() == b"project-owned bytes"
    assert receipt.read_bytes() == original_receipt
    assert not source.exists()
    entry = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert entry.startswith("# Business\nKeep the business rules.\n")
    assert entry.endswith("Keep later rules.\n")
    assert "Old generated instructions." not in entry
    assert ".basepack/instructions.md" in entry
    instructions = (root / ".basepack/instructions.md").read_text(encoding="utf-8")
    assert target_name in instructions
    assert str(python) in instructions
    assert (root / ".gitignore").read_text(encoding="utf-8").startswith("/business-cache/\n")
    assert "/.basepack/" in (root / ".gitignore").read_text(encoding="utf-8")
    backup = Path(result["backup_dir"])
    assert backup.is_relative_to(root / ".basepack/migration")
    assert backup_contains(backup, original_config)
    assert backup_contains(backup, original_agents)


def test_custom_local_data_and_generated_receipts_move_with_evidence(tmp_path):
    root, source, _, _ = legacy_project(tmp_path, memory="local memory", jobs="runtime/jobs old")
    old_memory = root / "local memory"
    old_jobs = root / "runtime/jobs old"
    job = old_jobs / "submission-one"
    old_memory.mkdir()
    job.mkdir(parents=True)
    (old_memory / "index.bin").write_bytes(b"owned index")
    payload = {
        "submission_id": "submission-one",
        "spec": {"executable": "C:/runtime/python.exe", "cwd": str(job / "work"),
                 "arguments": [str(old_jobs), "keep business argv"], "transfer_outputs": []},
        "worker_receipt": str(job / "worker.json"),
    }
    submission = {"job_id": "12.0", "job_dir": str(job), "payload": str(job / "basepack-job.json")}
    worker = {"pid": 123, "child_pid": 124, "cwd": str(job / "work"), "exit_code": 0}
    originals = {}
    for name, value in (("basepack-job.json", payload), ("submission.json", submission), ("worker.json", worker)):
        path = job / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        originals[name] = path.read_bytes()

    result = migrate_project(source)

    config = load_project_config(result["project_config"])
    new_job = root / ".basepack/jobs/submission-one"
    assert config.memory_dir == root / ".basepack/memory"
    assert config.jobs_dir == root / ".basepack/jobs"
    assert not old_memory.exists() and not old_jobs.exists()
    assert (config.memory_dir / "index.bin").read_bytes() == b"owned index"
    changed_payload = json.loads((new_job / "basepack-job.json").read_text(encoding="utf-8"))
    assert changed_payload["worker_receipt"] == str(new_job / "worker.json")
    assert changed_payload["spec"]["arguments"] == payload["spec"]["arguments"]
    assert changed_payload["spec"]["cwd"] == str(new_job / "work")
    changed_submission = json.loads((new_job / "submission.json").read_text(encoding="utf-8"))
    assert changed_submission["job_dir"] == str(new_job)
    assert changed_submission["payload"] == str(new_job / "basepack-job.json")
    assert json.loads((new_job / "worker.json").read_text(encoding="utf-8")) == worker | {"cwd": str(new_job / "work")}
    assert len(result["data_moves"]) == 2
    backup = Path(result["backup_dir"])
    assert backup_contains(backup, originals["basepack-job.json"])
    assert backup_contains(backup, originals["submission.json"])


def test_existing_legacy_managed_config_is_migrated_in_place(tmp_path):
    root, source, _, _ = legacy_project(tmp_path, source_name=".basepack/config.toml")
    original = source.read_bytes()

    result = migrate_project(source)

    assert Path(result["project_config"]) == source
    assert load_project_config(source).root == root
    assert backup_contains(Path(result["backup_dir"]), original)


def test_embedding_only_legacy_config_does_not_enable_other_features(tmp_path):
    root, source, _, _ = legacy_project(tmp_path)
    source.write_text(source.read_text(encoding="utf-8").split("[memory]", 1)[0], encoding="utf-8")

    result = migrate_project(source)

    config = load_project_config(result["project_config"])
    assert config.root == root
    assert "memory" not in config.raw and "jobs" not in config.raw
    assert not (root / ".basepack/memory").exists()
    assert not (root / ".basepack/jobs").exists()


@pytest.mark.parametrize("schema", [2, 99])
def test_migration_only_accepts_explicit_legacy_schema_before_writing(tmp_path, schema):
    root, source, _, _ = legacy_project(tmp_path, schema=schema)
    before = snapshot(root)
    with pytest.raises(ValueError, match="schema"):
        migrate_project(source)
    assert snapshot(root) == before


def test_existing_target_is_preserved_and_source_is_not_touched(tmp_path):
    root, source, _, _ = legacy_project(tmp_path)
    target = root / ".basepack/config.toml"
    target.parent.mkdir()
    target.write_bytes(b"existing valid instance belongs to user")
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        migrate_project(source)
    assert snapshot(root) == before


@pytest.mark.parametrize("target", ["config.toml", ".basepack/../escape.toml", "../other/config.toml"])
def test_target_config_cannot_escape_managed_directory(tmp_path, target):
    root, source, _, _ = legacy_project(tmp_path)
    before = snapshot(root)
    with pytest.raises(ValueError, match=".basepack"):
        migrate_project(source, target)
    assert snapshot(root) == before


@pytest.mark.parametrize("data", [".", "../outside"])
def test_migration_rejects_project_root_and_external_data_before_moving(tmp_path, data):
    root, source, _, _ = legacy_project(tmp_path, jobs=data)
    before = snapshot(root)
    with pytest.raises(ValueError):
        migrate_project(source)
    assert snapshot(root) == before


def test_custom_data_target_conflict_leaves_source_tree_unchanged(tmp_path):
    root, source, _, _ = legacy_project(tmp_path, jobs="custom-jobs")
    (root / "custom-jobs").mkdir()
    (root / "custom-jobs/original.txt").write_text("original", encoding="utf-8")
    (root / ".basepack/jobs").mkdir(parents=True)
    (root / ".basepack/jobs/existing.txt").write_text("existing", encoding="utf-8")
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        migrate_project(source)
    assert snapshot(root) == before


@pytest.mark.parametrize("memory,jobs", [("local", "local/jobs"), ("local/memory", "local")])
def test_overlapping_legacy_data_is_rejected_before_any_move(tmp_path, memory, jobs):
    root, source, _, _ = legacy_project(tmp_path, memory=memory, jobs=jobs)
    (root / memory).mkdir(parents=True)
    (root / jobs).mkdir(parents=True, exist_ok=True)
    before = snapshot(root)
    with pytest.raises(ValueError):
        migrate_project(source)
    assert snapshot(root) == before


def test_source_config_inside_moving_data_is_rejected_before_any_move(tmp_path):
    root, source, _, _ = legacy_project(tmp_path, source_name="custom-jobs/old.toml", jobs="custom-jobs")
    before = snapshot(root)
    with pytest.raises(ValueError):
        migrate_project(source)
    assert snapshot(root) == before


def test_target_config_does_not_overwrite_file_arriving_with_data(tmp_path):
    root, source, _, _ = legacy_project(tmp_path, jobs="custom-jobs")
    (root / "custom-jobs").mkdir()
    (root / "custom-jobs/config.toml").write_text("business data", encoding="utf-8")
    before = snapshot(root)
    with pytest.raises(FileExistsError):
        migrate_project(source, ".basepack/jobs/config.toml")
    assert snapshot(root) == before
