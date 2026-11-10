"""Published knowledge must retain the evidence it actually used."""

import argparse
import json

import pytest

from basepack.memory.cli import dispatch, register_commands
from test_memory_store import batch_for, memory


def test_read_published_snapshot_and_old_basis_after_member_reuse(memory):
    old = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(old)
    basis = memory.neighbors("node:local")["record"]["basis"][0]
    path = memory.config.root / "guide.md"
    path.write_bytes("# 数据库\n\n数据库离线运行。\n# 保留\n资料必须保留。\n".encode("utf-8"))
    assert memory.read("storage")["original"]["text"] == "本地数据库隔离项目。\n"
    new = batch_for(memory, path.read_text(encoding="utf-8"))
    new["members"][2]["start_line"] = 3
    new["members"][2]["end_line"] = 3
    new["members"][2]["text"] = "数据库离线运行。\n"
    memory.apply(new)
    assert memory.read("storage")["original"]["text"] == "数据库离线运行。\n"
    original = memory.read(basis["member"], source_version=basis["source_version"],
                           start_line=basis["start_line"], end_line=basis["end_line"])["original"]
    assert original["text"] == "本地数据库隔离项目。\n"
    assert original["source_version"] == basis["source_version"]
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["memory", "read", basis["member"], "--source-version", basis["source_version"],
                              "--start-line", str(basis["start_line"]), "--end-line", str(basis["end_line"])])
    assert dispatch(args, memory.config)[0]["original"] == original
    with pytest.raises(ValueError, match="requires start_line and end_line"):
        memory.read(basis["member"], source_version=basis["source_version"])
    other = memory.config.root / "other.md"
    other.write_text("unrelated\n", encoding="utf-8")
    prepared = memory.prepare(["other.md"])
    memory.apply({"sources": [{"path": "other.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "other", "kind": "chunk", "path": "other.md", "title": "other",
                       "start_line": 1, "end_line": 1}]})
    unrelated = memory.read("other")["original"]["source_version"]
    with pytest.raises(ValueError, match="does not belong to member"):
        memory.read(basis["member"], source_version=unrelated, start_line=1, end_line=1)
    memory._execute(f"DELETE {basis['source_version']};")
    with pytest.raises(ValueError, match="Source snapshot not found"):
        memory.read(basis["member"], source_version=basis["source_version"],
                    start_line=basis["start_line"], end_line=basis["end_line"])


def test_image_reads_retained_pixels_after_original_changes(memory):
    path = memory.config.root / "image.png"
    path.write_bytes(b"old pixels")
    prepared = memory.prepare(["image.png"])
    memory.apply({"sources": [{"path": "image.png", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "image", "kind": "image", "path": "image.png", "title": "image",
                       "text": "original", "locator": {"page": 1}}]})
    path.write_bytes(b"new pixels")
    original = memory.read("image")["original"]
    assert open(original["image_path"], "rb").read() == b"old pixels"
    prepared = memory.prepare(["image.png"])
    memory.apply({"sources": [{"path": "image.png", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "image", "kind": "image", "path": "image.png", "title": "image",
                       "text": "updated", "locator": {"page": 2}}]})
    old = memory.read("image", source_version=original["source_version"], locator={"page": 1})["original"]
    assert old["locator"] == {"page": 1}
    assert open(old["image_path"], "rb").read() == b"old pixels"
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["memory", "read", "image", "--source-version", original["source_version"],
                              "--locator", json.dumps({"page": 1})])
    assert dispatch(args, memory.config)[0]["original"] == old
    path.unlink()
    assert open(memory.read("image")["original"]["image_path"], "rb").read() == b"new pixels"


def test_retired_records_are_not_returned_even_without_stale_flag(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory._execute("UPDATE member:storage SET retired=true, stale=false; "
                    "UPDATE semantic:requires SET retired=true, stale=false;")
    assert "member:storage" not in {row["id"] for row in memory.search("数据库")}
    assert memory.neighbors("node:local")["edges"] == []
    assert memory.neighbors("node:local", include_stale=True)["edges"][0]["id"] == "semantic:requires"
