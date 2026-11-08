import pytest

from basepack.config import load_config
from basepack.setup import init_project, template


def test_two_projects_and_subdirectory_config(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state/basepack'\n", encoding="utf-8")
    projects = [tmp_path / "项目 A", tmp_path / "项目 B"]
    configs = [init_project(root, machine, "config/basepack.toml") for root in projects]
    monkeypatch.chdir(tmp_path.parent)
    loaded = [load_config(path) for path in configs]
    assert [config.root for config in loaded] == projects
    assert loaded[0].machine_config == loaded[1].machine_config
    assert loaded[0].memory_dir != loaded[1].memory_dir
    assert loaded[0].jobs_dir != loaded[1].jobs_dir
    assert loaded[0].machine.state_dir == tmp_path / "state/basepack"
    assert "config/basepack.toml" in (projects[0] / "AGENTS.md").read_text(encoding="utf-8")
    assert "/config/basepack.toml" in (projects[0] / ".gitignore").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        init_project(projects[0], machine, "config/basepack.toml")


def test_init_preserves_existing_project_instructions(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    root = tmp_path / "project"
    root.mkdir()
    (root / "AGENTS.md").write_text("# Business\nKeep original instructions.\n", encoding="utf-8")
    (root / ".gitignore").write_text("/original/\n", encoding="utf-8")
    init_project(root, machine)
    assert (root / "AGENTS.md").read_text(encoding="utf-8").startswith("# Business\nKeep original instructions.")
    assert (root / ".gitignore").read_text(encoding="utf-8").startswith("/original/\n")
    assert "[embedding]" in template("machine.toml")


def test_project_data_cannot_escape_project(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    path = init_project(tmp_path / "project", machine)
    path.write_text(path.read_text(encoding="utf-8").replace(".basepack/memory", "../other"), encoding="utf-8")
    with pytest.raises(ValueError, match="inside"):
        load_config(path)
