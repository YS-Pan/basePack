import json
from pathlib import Path
import sys

import pytest

import basepack
from basepack.project.config import describe, installation, load_machine_config, load_project_config
from basepack.project.doctor import doctor
from basepack.project.init import init_project, template


def test_two_projects_and_subdirectory_config(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state/basepack'\n", encoding="utf-8")
    projects = [tmp_path / "项目 A", tmp_path / "项目 B"]
    configs = [init_project(root, machine, ".basepack/config/deep/basepack.toml") for root in projects]
    monkeypatch.chdir(tmp_path.parent)
    loaded = [load_project_config(path) for path in configs]
    assert [config.root for config in loaded] == projects
    assert loaded[0].machine_config == loaded[1].machine_config
    assert loaded[0].memory_dir != loaded[1].memory_dir
    assert loaded[0].jobs_dir != loaded[1].jobs_dir
    assert loaded[0].machine.state_dir == tmp_path / "state/basepack"
    assert ".basepack/instructions.md" in (projects[0] / "AGENTS.md").read_text(encoding="utf-8")
    instructions = (projects[0] / ".basepack/instructions.md").read_text(encoding="utf-8")
    assert ".basepack/config/deep/basepack.toml" in instructions
    assert sys.executable in instructions
    assert (projects[0] / ".gitignore").read_text(encoding="utf-8") == "/.basepack/\n"
    assert not (projects[0] / ".basepack/memory").exists()
    assert not (projects[0] / ".basepack/jobs").exists()
    with pytest.raises(FileExistsError):
        init_project(projects[0], machine, ".basepack/config/deep/basepack.toml")
    with pytest.raises(FileExistsError):
        init_project(projects[0], machine, ".basepack/second.toml")


def test_init_preserves_existing_project_instructions(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    root.mkdir()
    (root / "AGENTS.md").write_text("# Business\nKeep original instructions.\n"
                                  "<!-- basepack:start -->\nOld generated entry.\n<!-- basepack:end -->\n"
                                  "Keep following instructions.\n", encoding="utf-8")
    (root / ".gitignore").write_text("/original/\n", encoding="utf-8")
    path = init_project(root, machine)
    assert path == root / ".basepack/config.toml"
    assert load_project_config(path).root == root
    assert (root / "AGENTS.md").read_text(encoding="utf-8").startswith("# Business\nKeep original instructions.")
    assert (root / "AGENTS.md").read_text(encoding="utf-8").endswith("Keep following instructions.\n")
    assert "Old generated entry." not in (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (root / ".gitignore").read_text(encoding="utf-8").startswith("/original/\n")
    assert "[embedding]" in template("machine.toml")
    assert "gpu_memory_mib" in template("machine.toml")
    assert "[budget]" not in template("machine.toml")


@pytest.mark.parametrize("target", ["../other", "other"])
def test_project_data_stays_in_managed_directory(tmp_path, target):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    path = init_project(tmp_path / "project", machine)
    path.write_text(path.read_text(encoding="utf-8").replace(".basepack/memory", target), encoding="utf-8")
    config = load_project_config(path)
    with pytest.raises(ValueError, match="inside"):
        config.memory_dir


@pytest.mark.parametrize("name", ["basepack.toml", "config/basepack.toml", ".basepack/../outside.toml"])
def test_init_requires_config_under_basepack(tmp_path, name):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match=".basepack"):
        init_project(tmp_path / "project", machine, name)


def test_embedding_only_configuration_has_no_other_facility_dependencies(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[embedding]\nmodel_root='model'\n", encoding="utf-8")
    project = tmp_path / "project.toml"
    project.write_text("schema_version=1\n[runtime]\npython=" + json.dumps(sys.executable)
                       + "\nmachine_config=" + json.dumps(str(machine))
                       + "\n[project]\nroot='.'\n", encoding="utf-8")
    config = load_project_config(project)
    assert config.machine_config == load_machine_config(machine).path
    result = describe(config)
    assert result["machine_paths"] == {"embedding": {"model_root": str(tmp_path / "model")}}
    assert "memory_dir" not in result
    assert "jobs_dir" not in result
    with pytest.raises(KeyError, match="memory"):
        config.memory_dir
    with pytest.raises(KeyError, match="resources"):
        config.jobs_dir


def test_package_root_and_installed_template_anchor(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    package = Path(basepack.__file__).resolve().parent
    monkeypatch.setattr("basepack.project.doctor.subprocess.check_output", lambda *args, **kwargs: str(package / "__init__.py"))
    result = doctor(config, "core")
    assert Path(installation()["package_dir"]) == package
    assert Path(result["checks"]["package"]) == package
    assert Path(result["checks"]["templates"]) == package / "project/templates"
    for name in ("project.toml", "machine.toml", "agents-snippet.md", "instructions.md"):
        assert template(name)


def test_project_and_machine_schema_are_checked_separately(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_machine_config(machine)
    machine.write_text("schema_version=1\n", encoding="utf-8")
    path = init_project(tmp_path / "project", machine)
    path.write_text(path.read_text(encoding="utf-8").replace("schema_version = 1", "schema_version = 2"), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_project_config(path)
