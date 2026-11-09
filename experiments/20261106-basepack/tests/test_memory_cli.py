import pytest

from basepack.memory.cli import _activate
from basepack.project.config import load_project_config
from basepack.project.init import init_project


def test_memory_activation_preserves_business_text_and_updates_one_local_entry(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    original = instructions.read_text(encoding="utf-8")
    _activate(config)
    instructions.write_text(instructions.read_text(encoding="utf-8") + "\n业务尾注：需保留。\n", encoding="utf-8")
    _activate(config)
    updated = instructions.read_text(encoding="utf-8")
    assert updated.startswith(original.rstrip())
    assert updated.endswith("\n业务尾注：需保留。\n")
    assert updated.count("<!-- basepack-memory:start -->") == 1
    assert "--config '.basepack/config.toml' memory brief" in updated
    assert "[记忆流程](<" in updated
    assert str(project) not in updated


def test_broken_generated_boundary_fails_before_overwriting_instructions(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    text = "用户正文\n<!-- basepack-memory:start -->\n用户仍需的尾注\n"
    instructions.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        _activate(config)
    assert instructions.read_text(encoding="utf-8") == text
