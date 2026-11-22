from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from basepack.memory.inventory import inventory

from test_memory_discovery import capture, git, put


def config(root, *, scopes=(), bound=True):
    return SimpleNamespace(root=root, memory_dir=root / ".basepack" / "memory", raw={"memory": {
        "project_id": "test-project", "source_scope": list(scopes), "private_scope": ["restricted"],
        "codex": {"project_id": "codex-project"} if bound else {},
    }})


def registered(path, data, *, deleted=False):
    return {"id": f"source:{path}", "path": path, "revision": sha256(data).hexdigest(),
            "kind": "text", "deleted": deleted, "private": True}


def test_inventory_observes_union_without_mutating_sources_or_memory(tmp_path):
    cfg = config(tmp_path, scopes=("ignored/pinned.md", "project.md", ".basepack"))
    git(tmp_path, "init", "-q")
    put(tmp_path, ".gitignore", b"/private/\n/ignored/\n/.basepack/\n")
    put(tmp_path, "project.md", b"first\r\nsecond\n")
    tracked_missing = put(tmp_path, "tracked-missing.md")
    git(tmp_path, "add", ".gitignore", "project.md", "tracked-missing.md")
    tracked_missing.unlink()
    put(tmp_path, "ignored/pinned.md")
    put(tmp_path, "ignored/unselected.md")
    put(tmp_path, "ignored/registered.md", b"edited")
    put(tmp_path, "restricted/notes.md")
    put(tmp_path, "nul.bin", b"text\0")
    put(tmp_path, "not-utf8.bin", b"\xff")
    (tmp_path / "private").mkdir()
    git(tmp_path / "private", "init", "-q")
    put(tmp_path, "private/note.md")

    thread_id = "e7295440-12da-44c9-9650-96540844a9bd"
    ours = {"project_id": "codex-project", "thread_id": thread_id}
    capture(cfg, "old.txt", [(ours, "history"),
                             ({**ours, "managed_attachment": "codex-attachments/image.png"}, ""),
                             ({**ours, "managed_attachment": "codex-attachments/missing.png"}, "")])
    capture(cfg, "other.txt", [({**ours, "project_id": "foreign-project"}, "foreign")])
    put(tmp_path, ".basepack/memory/codex-attachments/image.png", b"\x89PNG\0")
    put(tmp_path, ".basepack/memory/unrelated.txt", b"local state")

    entries = [registered("project.md", b"first\r\nsecond\n"), registered("ignored/registered.md", b"old"),
               registered("lost.md", b"old"), registered("deleted.md", b"older", deleted=True)]
    memory = SimpleNamespace(sources=lambda: entries)
    before = {item: item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}

    report = inventory(cfg, memory)
    assert report == inventory(cfg, memory)
    assert before == {item: item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}
    assert entries[0]["path"] == "project.md"

    rows = {row["path"]: row for row in report["sources"]}
    assert sorted(rows) == list(rows)
    assert set(rows) == {
        ".basepack/memory/codex-attachments/image.png", ".basepack/memory/codex-attachments/missing.png",
        ".basepack/memory/codex/old.txt", ".gitignore", "deleted.md", "ignored/pinned.md",
        "ignored/registered.md", "lost.md", "not-utf8.bin", "nul.bin", "private/note.md", "project.md",
        "restricted/notes.md", "tracked-missing.md",
    }
    project = rows["project.md"]
    assert project["origins"] == ["configured", "git", "registered"]
    assert project["kind"] == "text" and project["line_count"] == 2
    assert project["revision"] == sha256(b"first\r\nsecond\n").hexdigest()
    assert project["registration_status"] == "unchanged" and project["registered"]["private"] is True
    assert project["private"] is False
    assert rows["ignored/registered.md"]["registration_status"] == "changed"
    assert rows["lost.md"]["registration_status"] == "missing"
    assert rows["deleted.md"]["registration_status"] == "deleted"
    assert rows["tracked-missing.md"]["origins"] == ["git"]
    assert rows["tracked-missing.md"]["status"] == "missing"
    assert rows["tracked-missing.md"]["registration_status"] == "unregistered"
    assert rows["private/note.md"]["origins"] == ["private_git"]
    assert rows["private/note.md"]["private"] and rows["restricted/notes.md"]["private"]
    assert rows["private/note.md"]["registered"] is None
    assert rows["not-utf8.bin"]["revision"] == sha256(b"\xff").hexdigest()
    assert rows["not-utf8.bin"]["status"] == "unsupported"
    image = rows[".basepack/memory/codex-attachments/image.png"]
    assert image["kind"] == "image" and image["codex_threads"] == [thread_id]
    assert rows[".basepack/memory/codex/old.txt"]["codex_threads"] == [thread_id]
    assert rows[".basepack/memory/codex-attachments/missing.png"]["reason"] == "missing_attachment"
    assert report["capture"] == {"status": "retained", "project_id": "codex-project", "freshness": "unknown"}
    assert report["counts"]["paths"] == len(rows)
    assert report["counts"]["by_status"] == {"available": 8, "missing": 4, "unsupported": 2}


def test_inventory_uses_only_selected_verified_collection(tmp_path):
    cfg = config(tmp_path)
    thread_id = "e7295440-12da-44c9-9650-96540844a9bd"
    header = {"project_id": "codex-project", "thread_id": thread_id}
    image_bytes = b"\x89PNG\0"
    image_revision = sha256(image_bytes).hexdigest()
    managed = f"codex-attachments/{image_revision}.png"
    attachment = put(tmp_path, cfg.memory_dir.relative_to(tmp_path) / managed, image_bytes)
    location = {**header, "part": 1, "part_type": "localImage", "managed_attachment": managed}
    capture(cfg, "included.txt", [(header, "kept"), (location, "")])
    capture(cfg, "other.txt", [(header, "otherwise retained")])
    relative = ".basepack/memory/codex/included.txt"
    target = tmp_path / relative
    attachment_relative = attachment.relative_to(tmp_path).as_posix()
    unavailable = {**header, "turn_id": "turn", "item_id": "item", "part": 2, "part_type": "image",
                   "unavailable_part": {"type": "image", "url": "not inventoried"}}
    receipt = {"root": str(tmp_path), "status": "captured", "project_id": "codex-project",
               "paths": [relative, attachment_relative],
               "snapshots": [{"path": relative, "sha256": sha256(target.read_bytes()).hexdigest()},
                             {"path": attachment_relative, "sha256": image_revision}],
               "capture": {"threads": [{"thread_id": thread_id, "path": str(target),
                                        "attachments": [str(attachment)], "locations": [location]}],
                           "gaps": [unavailable]}}
    receipt_path = put(tmp_path, ".basepack/memory/collection.json", json.dumps(receipt).encode())
    memory = SimpleNamespace(sources=lambda: [])
    report = inventory(cfg, memory, collection=receipt_path)
    assert {row["path"] for row in report["sources"]} == {relative, attachment_relative}
    assert all(row["codex_threads"] == [thread_id] for row in report["sources"])
    assert report["capture"]["freshness"] == "receipt_cutoff"
    assert report["capture_gaps"] == [{key: value for key, value in unavailable.items() if key != "unavailable_part"}]

    target.write_bytes(b"another generation")
    with pytest.raises(ValueError, match="Collection snapshot changed"):
        inventory(cfg, memory, collection=receipt_path)


def test_inventory_reports_observation_failure_without_reusing_registered_digest(tmp_path, monkeypatch):
    cfg = config(tmp_path, bound=False)
    item = registered("note.md", b"before")
    memory = SimpleNamespace(sources=lambda: [item])

    def source_changed(path):
        raise RuntimeError(f"Source changed while reading: {path}")

    monkeypatch.setattr("basepack.memory.inventory._read_bytes", source_changed)
    report = inventory(cfg, memory)
    assert report["sources"][0]["status"] == "unreadable"
    assert report["sources"][0]["revision"] is None
    assert report["sources"][0]["registration_status"] == "unknown"
    assert report["gaps"][0]["reason"] == "changed_during_read"
