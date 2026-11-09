from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path

import pytest

from basepack.memory.content import (
    detect_changes, numbered_text, read_member, read_source, reading_units,
)


def write_source(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def test_original_bytes_line_units_and_agent_selected_range(tmp_path):
    raw = "# 项目\r\n\r\n第一段。\r\n仍是同段。\r\n\r\n## 条件\r\n例外不可省略。".encode("utf-8")
    path = write_source(tmp_path, "资料 空格/决定.md", raw)
    source = read_source(tmp_path, "资料 空格/决定.md")
    assert source.path == "资料 空格/决定.md"
    assert source.revision == sha256(raw).hexdigest()
    assert source.size == len(raw)
    assert source.mtime_ns == path.stat().st_mtime_ns
    assert source.text.encode("utf-8") == raw
    assert [(unit.kind, unit.start_line, unit.end_line) for unit in reading_units(source)] == [
        ("heading", 1, 1), ("paragraph", 3, 4), ("heading", 6, 6), ("paragraph", 7, 7)]
    assert reading_units(source)[1].text == "第一段。\r\n仍是同段。\r\n"
    assert numbered_text(source).startswith("1: # 项目\r\n2: \r\n3: 第一段。\r\n")
    # The agent may choose a range crossing the mechanical preparation units.
    member = read_member(tmp_path, source.path, source.revision, "稳定块:决定", 4, 7)
    assert member.member_id == "稳定块:决定"
    assert (member.start_line, member.end_line) == (4, 7)
    assert member.text == "仍是同段。\r\n\r\n## 条件\r\n例外不可省略。"


def test_revision_mismatch_and_missing_original_are_not_hidden(tmp_path):
    path = write_source(tmp_path, "source.md", b"old\n")
    source = read_source(tmp_path, "source.md")
    path.write_bytes(b"new\n")
    with pytest.raises(ValueError, match="Source revision mismatch"):
        read_member(tmp_path, source.path, source.revision, "stable", 1, 1)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        read_member(tmp_path, source.path, source.revision, "stable", 1, 1)


@pytest.mark.parametrize("start,end", [(0, 1), (-1, 1), (2, 1), (1, 3)])
def test_invalid_agent_ranges_fail(tmp_path, start, end):
    write_source(tmp_path, "source.md", b"one\ntwo")
    source = read_source(tmp_path, "source.md")
    with pytest.raises(ValueError, match="Invalid line range"):
        read_member(tmp_path, source.path, source.revision, "stable", start, end)


def test_empty_and_invalid_utf8_sources(tmp_path):
    write_source(tmp_path, "empty", b"")
    source = read_source(tmp_path, "empty")
    assert source.revision == sha256(b"").hexdigest()
    assert reading_units(source) == []
    assert numbered_text(source) == ""
    with pytest.raises(ValueError, match="0 lines"):
        read_member(tmp_path, "empty", source.revision, "stable", 1, 1)
    write_source(tmp_path, "invalid", b"\xff")
    with pytest.raises(UnicodeDecodeError):
        read_source(tmp_path, "invalid")


def test_project_move_preserves_relative_identity_and_revision(tmp_path):
    original = tmp_path / "原 项目"
    write_source(original, "资料/来源.md", "第一行\n第二行".encode("utf-8"))
    source = read_source(original, "资料/来源.md")
    moved = tmp_path / "搬移 项目"
    original.rename(moved)
    member = read_member(moved, source.path, source.revision, "stable-id", 2, 2)
    assert (member.path, member.member_id, member.revision, member.text) == (
        "资料/来源.md", "stable-id", source.revision, "第二行")


def test_sources_and_scope_cannot_leave_project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    outside = write_source(tmp_path, "outside", b"outside")
    for path in ("../outside", str(outside)):
        with pytest.raises(ValueError):
            read_source(root, path)
        with pytest.raises(ValueError):
            detect_changes(root, [], [path])


def test_fast_detection_marks_added_modified_deleted_only_inside_scope(tmp_path, monkeypatch):
    write_source(tmp_path, "docs/changed", b"old")
    deleted = write_source(tmp_path, "docs/deleted", b"deleted")
    excluded = write_source(tmp_path, "other/deleted", b"excluded")
    sources = [asdict(read_source(tmp_path, path)) for path in
               ("docs/changed", "docs/deleted", "other/deleted")]
    write_source(tmp_path, "docs/changed", b"new longer")
    write_source(tmp_path, "docs/added", b"added")
    deleted.unlink()
    excluded.unlink()
    monkeypatch.setattr(Path, "read_bytes", lambda path: pytest.fail("Fast detection read content"))
    changes = detect_changes(tmp_path, sources, ["docs"])
    assert [(change.path, change.kind, change.revision) for change in changes] == [
        ("docs/added", "added", None), ("docs/changed", "modified", None),
        ("docs/deleted", "deleted", None)]
    assert changes[1].size == len(b"new longer")
    assert detect_changes(tmp_path, sources, []) == []


def test_deep_detection_finds_same_size_same_timestamp_edit(tmp_path):
    path = write_source(tmp_path, "docs/source", b"old")
    source = read_source(tmp_path, "docs/source")
    path.write_bytes(b"new")
    os.utime(path, ns=(path.stat().st_atime_ns, source.mtime_ns))
    assert detect_changes(tmp_path, [asdict(source)], ["docs/source"]) == []
    changes = detect_changes(tmp_path, [asdict(source)], ["docs/source"], deep=True)
    assert len(changes) == 1
    assert (changes[0].kind, changes[0].revision) == ("modified", sha256(b"new").hexdigest())


def test_metadata_only_change_exposes_same_revision_for_reuse(tmp_path):
    path = write_source(tmp_path, "source", b"unchanged")
    source = read_source(tmp_path, "source")
    os.utime(path, ns=(path.stat().st_atime_ns, source.mtime_ns + 1_000_000))
    change, = detect_changes(tmp_path, [asdict(source)], ["source"], deep=True)
    assert change.kind == "modified"
    assert change.revision == source.revision
    assert change.mtime_ns != source.mtime_ns


def test_deleted_directory_reports_its_known_sources(tmp_path):
    path = write_source(tmp_path, "docs/source", b"old")
    source = read_source(tmp_path, "docs/source")
    path.unlink()
    path.parent.rmdir()
    change, = detect_changes(tmp_path, [asdict(source)], ["docs"])
    assert (change.path, change.kind) == ("docs/source", "deleted")


def test_scan_errors_propagate_instead_of_becoming_deletions(tmp_path, monkeypatch):
    write_source(tmp_path, "docs/source", b"old")
    source = read_source(tmp_path, "docs/source")
    failure = PermissionError("source directory cannot be read")

    def denied(path):
        raise failure

    monkeypatch.setattr("basepack.memory.content.scandir", denied)
    with pytest.raises(PermissionError) as error:
        detect_changes(tmp_path, [asdict(source)], ["docs"])
    assert error.value is failure


def test_reading_a_concurrently_changed_source_fails(tmp_path, monkeypatch):
    path = write_source(tmp_path, "source", b"before")
    original_read = Path.read_bytes

    def read_then_change(target):
        data = original_read(target)
        target.write_bytes(b"after and longer")
        return data

    monkeypatch.setattr(Path, "read_bytes", read_then_change)
    with pytest.raises(RuntimeError, match="Source changed while reading"):
        read_source(tmp_path, path.name)


def test_project_discovery_skips_own_storage_and_git_but_explicit_job_scope_is_allowed(tmp_path):
    write_source(tmp_path, "docs/note.md", b"knowledge")
    write_source(tmp_path, ".basepack/memory/db/log", b"database state")
    write_source(tmp_path, ".basepack/jobs/result.txt", b"explicit job evidence")
    write_source(tmp_path, ".git/index", b"git state")
    assert [change.path for change in detect_changes(tmp_path, [], ["."])] == ["docs/note.md"]
    assert [change.path for change in detect_changes(tmp_path, [], [".basepack/jobs"])] == [".basepack/jobs/result.txt"]
    registered = read_source(tmp_path, ".basepack/jobs/result.txt")
    assert [change.path for change in detect_changes(tmp_path, [asdict(registered)], ["."])] == ["docs/note.md"]
