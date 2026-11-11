import subprocess
from types import SimpleNamespace

import pytest

from basepack.memory.discovery import discover_sources


def config(root, scopes=()):
    return SimpleNamespace(root=root, raw={"memory": {"source_scope": list(scopes)}})


def put(root, path, data=b"text"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)


def test_git_inventory_and_explicit_additions(tmp_path):
    git(tmp_path, "init", "-q")
    put(tmp_path, ".gitignore", b"ignored/\n__pycache__/\n.basepack/\n")
    put(tmp_path, "tracked.md")
    git(tmp_path, "add", ".gitignore", "tracked.md")
    put(tmp_path, "new.md")
    put(tmp_path, "ignored/not-selected.md")
    put(tmp_path, "ignored/selected.md")
    put(tmp_path, "__pycache__/generated.pyc", b"\0")
    put(tmp_path, ".basepack/secrets.txt")
    result = discover_sources(config(tmp_path, ["ignored/selected.md", ".basepack", "__pycache__"]))
    assert result == {"paths": [".gitignore", "ignored/selected.md", "new.md", "tracked.md"],
                      "gaps": [], "mode": "git"}


def test_explicit_scope_overrides_inventory_and_config(tmp_path):
    git(tmp_path, "init", "-q")
    put(tmp_path, "whole.md")
    put(tmp_path, "configured.md")
    put(tmp_path, "selected/yes.md")
    put(tmp_path, "selected/.basepack/no.md")
    put(tmp_path, "selected/.git/no.md")
    put(tmp_path, "selected/__pycache__/no.pyc")
    put(tmp_path, "selected/generated.pyc")
    result = discover_sources(config(tmp_path, ["configured.md"]), ["selected"])
    assert result == {"paths": ["selected/yes.md"], "gaps": [], "mode": "explicit"}


def test_non_git_scopes_and_unsupported_files(tmp_path, monkeypatch):
    monkeypatch.setattr("basepack.memory.discovery._git_repository", lambda root: False)
    put(tmp_path, "docs/plain", "你好".encode())
    put(tmp_path, "docs/image.PNG", b"\x89PNG\x00")
    put(tmp_path, "docs/nul.bin", b"some\0bytes")
    put(tmp_path, "docs/nonutf8.bin", b"\xff")
    put(tmp_path, "outside.md")
    result = discover_sources(config(tmp_path, ["docs"]))
    assert result["paths"] == ["docs/image.PNG", "docs/plain"]
    assert result["mode"] == "configured"
    assert result["gaps"][0]["path"] == "docs/nonutf8.bin"
    assert result["gaps"][0]["reason"] == "non_utf8"
    assert "codec" in result["gaps"][0]["error"]
    assert result["gaps"][1] == {"path": "docs/nul.bin", "reason": "binary"}


def test_git_repository_parent_respects_project_root(tmp_path):
    git(tmp_path, "init", "-q")
    put(tmp_path, "other.md")
    root = tmp_path / "project"
    put(root, "own.md")
    assert discover_sources(config(root))["paths"] == ["own.md"]


def test_scope_outside_root_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="leaves project"):
        discover_sources(config(tmp_path, ["../outside"]))


def test_git_failure_is_not_treated_as_non_git(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git")
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        discover_sources(config(tmp_path))


def codex_config(root):
    return SimpleNamespace(root=root, memory_dir=root / ".basepack" / "memory")


def capture(config, filename, entries):
    import json
    chunks = []
    for header, body in entries:
        data = body.encode("utf-8")
        chunks.extend([json.dumps({**header, "byte_length": len(data)}, ensure_ascii=False).encode("utf-8"),
                       b"\n", data, b"\n"])
    relative = config.memory_dir.relative_to(config.root) / "codex" / filename
    put(config.root, relative, b"".join(chunks))


def test_retained_codex_owned_captures_and_attachments(tmp_path):
    from basepack.memory.discovery import retained_codex_paths
    cfg = codex_config(tmp_path)
    ours = {"project_id": "project", "thread_id": "old-thread"}
    capture(cfg, "old.txt", [(ours, '中文🙂\n{"project_id":"other"}'),
                             ({**ours, "managed_attachment": "codex-attachments/image.png"}, "")])
    capture(cfg, "other.txt", [({"project_id": "other", "thread_id": "other-thread"}, "ignored")])
    put(tmp_path, ".basepack/memory/codex-attachments/image.png", b"image")
    put(tmp_path, ".basepack/memory/unrelated.txt", b"secret")
    assert retained_codex_paths(cfg, "project") == {
        "paths": [".basepack/memory/codex-attachments/image.png", ".basepack/memory/codex/old.txt"],
        "gaps": []}
    assert retained_codex_paths(cfg, None) == {"paths": [], "gaps": []}


def test_retained_codex_missing_attachment_is_a_gap(tmp_path):
    from basepack.memory.discovery import retained_codex_paths
    cfg = codex_config(tmp_path)
    capture(cfg, "old.txt", [({"project_id": "project", "thread_id": "thread",
                                "managed_attachment": "codex-attachments/gone.png"}, "")])
    assert retained_codex_paths(cfg, "project") == {
        "paths": [".basepack/memory/codex/old.txt"],
        "gaps": [{"path": ".basepack/memory/codex-attachments/gone.png", "reason": "missing_attachment"}]}


def test_retained_codex_rejects_escaping_attachment(tmp_path):
    from basepack.memory.discovery import retained_codex_paths
    cfg = codex_config(tmp_path)
    capture(cfg, "old.txt", [({"project_id": "project", "thread_id": "thread",
                                "managed_attachment": "codex-attachments/../../secret"}, "")])
    with pytest.raises(ValueError, match="leaves attachment directory"):
        retained_codex_paths(cfg, "project")


def test_retained_codex_malformed_owned_capture_fails(tmp_path):
    from basepack.memory.discovery import retained_codex_paths
    cfg = codex_config(tmp_path)
    capture(cfg, "old.txt", [({"project_id": "project", "thread_id": "thread"}, "text")])
    target = cfg.memory_dir / "codex" / "old.txt"
    target.write_bytes(target.read_bytes()[:-2])
    with pytest.raises(ValueError, match="Truncated Codex capture body"):
        retained_codex_paths(cfg, "project")
