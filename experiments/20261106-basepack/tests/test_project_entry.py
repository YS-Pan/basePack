"""Managed entry refresh preserves project instructions across enable/upgrade."""

from pathlib import Path
import re
import shutil

import pytest

from basepack.project.config import load_project_config
from basepack.project.init import init_project, refresh_project_entry, template


def project_config(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    return load_project_config(init_project(tmp_path / "中文 user's project-🚀", machine,
                                            ".basepack/deep/user's-config.toml", max_concurrent_subagents=12, concurrency_source="test fixture"))


def refresh(config, enabled=True):
    refresh_project_entry(config.root, config.path, config.python,
                          memory_enabled=enabled, memory_dir=config.memory_dir)


def assert_detail_links(config):
    agents = (config.root / "AGENTS.md").read_text(encoding="utf-8")
    details = (config.root / ".basepack/instructions.md").read_text(encoding="utf-8")
    anchors = re.findall(r"\]\(\.basepack/instructions\.md#([\w-]+)\)", agents)
    assert anchors
    assert all(f'<a id="{anchor}"></a>' in details for anchor in anchors)


def test_disabled_enabled_refresh_is_idempotent_and_links_are_reachable(tmp_path):
    config = project_config(tmp_path)
    assert_detail_links(config)
    agents = config.root / "AGENTS.md"
    assert "记忆尚未启用" in agents.read_text(encoding="utf-8")
    assert "memory brief" not in agents.read_text(encoding="utf-8")
    assert not config.memory_dir.exists()
    refresh(config)
    assert_detail_links(config)
    expected = [path.read_bytes() for path in (agents, config.root / ".basepack/instructions.md")]
    for _ in range(2):
        refresh(config)
        assert [path.read_bytes() for path in (agents, config.root / ".basepack/instructions.md")] == expected
    assert "needs_semantic=true" in agents.read_text(encoding="utf-8")
    assert "memory brief" in agents.read_text(encoding="utf-8")


def test_refresh_preserves_all_bytes_outside_each_managed_block(tmp_path):
    config = project_config(tmp_path)
    surrounding = b"\xef\xbb\xbf\r\n\r\n" + "业务前言 \t".encode() + b"\r\n\n", "业务尾注 \t".encode() + b"\r\n\r\n "
    for relative, name in (("AGENTS.md", "basepack"), (".basepack/instructions.md", "basepack-memory")):
        path = config.root / relative
        start, end = f"<!-- {name}:start -->".encode(), f"<!-- {name}:end -->".encode()
        path.write_bytes(surrounding[0] + start + b"\r\nold\n" + end + surrounding[1])
    refresh(config)
    for relative, name in (("AGENTS.md", "basepack"), (".basepack/instructions.md", "basepack-memory")):
        content = (config.root / relative).read_bytes()
        start, end = f"<!-- {name}:start -->".encode(), f"<!-- {name}:end -->".encode()
        assert content[:content.index(start)] == surrounding[0]
        assert content[content.index(end) + len(end):] == surrounding[1]
    assert_detail_links(config)


@pytest.mark.parametrize("relative,name", [("AGENTS.md", "basepack"), (".basepack/instructions.md", "basepack-memory")])
@pytest.mark.parametrize("layout", ["start", "end", "end start", "start start end", "start end end"])
def test_bad_boundaries_leave_both_files_unchanged(tmp_path, relative, name, layout):
    config = project_config(tmp_path)
    path = config.root / relative
    path.write_bytes(("\r\nBusiness\r\n" + "\r\n".join(
        f"<!-- {name}:{part} -->" for part in layout.split()) + "\r\n").encode())
    paths = [config.root / "AGENTS.md", config.root / ".basepack/instructions.md"]
    original = [item.read_bytes() for item in paths]
    with pytest.raises(ValueError, match="entry markers"):
        refresh(config)
    assert [item.read_bytes() for item in paths] == original


def test_old_entry_without_memory_block_upgrades_and_remains_location_safe(tmp_path):
    config = project_config(tmp_path)
    old = b"\xef\xbb\xbf# Previous instructions\r\nKeep this trailing whitespace.  \r\n\r\n"
    (config.root / ".basepack/instructions.md").write_bytes(old)
    refresh(config)
    assert (config.root / ".basepack/instructions.md").read_bytes().startswith(old)
    assert_detail_links(config)
    moved = tmp_path / "新位置 with spaces"
    shutil.move(str(config.root), str(moved))
    moved_config = load_project_config(moved / config.path.relative_to(config.root))
    refresh(moved_config)
    assert_detail_links(moved_config)
    details = (moved / ".basepack/instructions.md").read_text(encoding="utf-8")
    assert str(moved_config.path).replace("'", "''") in details
    assert moved_config.memory_dir.as_posix() in details
    assert str(config.root) not in details


def test_distribution_templates_have_no_author_machine_paths():
    for name in ("agents-snippet.md", "agents-enabled.md", "agents-disabled.md", "memory-enabled.md",
                 "memory-disabled.md", "instructions.md", "tools.md"):
        assert not re.search(r"\b[A-Za-z]:[\\/]", template(name))


def test_shipped_detail_links_resolve_skill_headings():
    from basepack.memory import __file__ as memory_module

    skill = Path(memory_module).with_name("SKILL.md").read_text(encoding="utf-8")
    anchors = {heading.lower().replace(" ", "-") for heading in re.findall(r"^## (.+)$", skill, re.M)}
    for name in ("memory-enabled.md", "memory-disabled.md", "tools.md"):
        for anchor in re.findall(r"\$skill#([\w-]+)", template(name)):
            assert anchor in anchors


@pytest.mark.parametrize("failure", [False, True])
def test_memory_init_refreshes_both_entries_only_after_schema_identity_check(tmp_path, monkeypatch, failure):
    import argparse
    from basepack.memory.cli import dispatch

    config = project_config(tmp_path)
    paths = [config.root / "AGENTS.md", config.root / ".basepack/instructions.md"]
    before = [path.read_bytes() for path in paths]

    class Memory:
        def __init__(self, current):
            assert current is config

        def install_schema(self):
            assert [path.read_bytes() for path in paths] == before
            if failure:
                raise RuntimeError("schema identity mismatch")
            return {"schema": "checked"}

    monkeypatch.setattr("basepack.memory.store.Memory", Memory)
    args = argparse.Namespace(memory_action="init", output=None)
    if failure:
        with pytest.raises(RuntimeError, match="schema identity mismatch"):
            dispatch(args, config)
        assert [path.read_bytes() for path in paths] == before
    else:
        assert dispatch(args, config) == ({"schema": "checked"}, 0)
        assert "memory brief" in paths[0].read_text(encoding="utf-8")
        assert_detail_links(config)
