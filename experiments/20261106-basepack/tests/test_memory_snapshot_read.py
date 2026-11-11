"""Published knowledge must retain the evidence it actually used."""

import argparse
import json

import pytest

from basepack.memory.cli import dispatch, register_commands
from basepack.memory.store import _record, _sql
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
    path.unlink()
    assert memory.read(basis["member"], source_version=basis["source_version"],
                       start_line=basis["start_line"], end_line=basis["end_line"])["original"] == original
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


def test_codex_message_identity_and_text_survive_source_update_in_saved_snapshot(memory):
    from basepack.memory.codex import _render

    thread_id = "01a1c5dc-af1a-7fa2-87a6-654370d72307"
    path = memory.config.memory_dir / "codex" / f"{thread_id}.txt"
    path.parent.mkdir(parents=True)
    source_path = path.relative_to(memory.config.root).as_posix()

    def publish(text):
        rows = [{"turnId": "turn-1", "item": {"id": "item-1", "type": "userMessage",
                                                "content": [{"type": "text", "text": text}]}}]
        payload = _render("project", {"id": thread_id}, rows, memory.config.memory_dir, None)[0]
        path.write_bytes(payload)
        prepared = memory.prepare([source_path])
        source = prepared["sources"][0]
        memory.apply({"sources": [{"path": source_path, "revision": source["revision"]}],
                      "expected": prepared["expected"], "members": [
                          {"id": "chat-evidence", "kind": "chunk", "path": source_path,
                           "title": "用户要求", "start_line": 2, "end_line": 2}]})
        return memory.read("chat-evidence")["original"]

    old = publish("原要求：保留证据 🚀")
    updated = publish("修订要求：另外保留备份")
    assert updated["chat_locations"][0]["text"] == "修订要求：另外保留备份"
    assert updated["source_version"] != old["source_version"]
    path.unlink()
    original = memory.read("chat-evidence", source_version=old["source_version"],
                           start_line=old["start_line"], end_line=old["end_line"])["original"]
    assert original == old
    loc, = original["chat_locations"]
    assert (loc["chat_url"], loc["thread_id"], loc["turn_id"], loc["item_id"], loc["part"]) == (
        f"codex://threads/{thread_id}", thread_id, "turn-1", "item-1", 0)
    assert loc["role"] == "user"
    assert loc["text"] == "原要求：保留证据 🚀"
    assert loc["part_byte_start"] == 0
    assert loc["part_byte_end"] == len(loc["text"].encode("utf-8"))


@pytest.mark.parametrize("legacy_snapshot", [False, True])
@pytest.mark.parametrize("history_shape", ["direct", "nested"])
def test_old_basis_remains_readable_after_member_moves_to_another_source(memory, legacy_snapshot, history_shape, monkeypatch):
    text = "The original condition remains evidence.\n"
    old_path, new_path = "before.md", "after.md"
    (memory.config.root / old_path).write_text(text, encoding="utf-8")
    prepared = memory.prepare([old_path])
    memory.apply({"sources": [{"path": old_path, "revision": prepared["sources"][0]["revision"]}],
                  "members": [{"id": "moving", "kind": "chunk", "path": old_path,
                               "title": "Condition", "start_line": 1, "end_line": 1}],
                  "nodes": [{"id": "old_claim", "kind": "condition", "text": "The original condition",
                             "evidence": ["moving"]}]})
    basis = memory.neighbors("node:old_claim")["record"]["basis"][0]
    if legacy_snapshot:
        memory._execute(f"UPDATE {_sql(_record(basis['source_version']))} UNSET path;")
    original = memory.read("moving")["original"]
    snapshot = memory._execute(f"SELECT * FROM ONLY {_sql(_record(basis['source_version']))};")[0]
    before_vector = memory._execute("SELECT embedding,input_revision FROM ONLY member:moving;")[0]

    def unexpected_embedding(*args, **kwargs):
        pytest.fail("unchanged representation was encoded again")

    monkeypatch.setattr("basepack.memory.candidate_vectors.EmbeddingClient.embed", unexpected_embedding)

    (memory.config.root / new_path).write_text(text, encoding="utf-8")
    prepared = memory.prepare([old_path, new_path])
    source = next(item for item in prepared["sources"] if item["path"] == new_path)
    memory.apply({"sources": [{"path": new_path, "revision": source["revision"]}],
                  "expected": prepared["expected"],
                  "members": [{"id": "moving", "kind": "chunk", "path": new_path,
                               "title": "Condition", "start_line": 1, "end_line": 1}]})
    if history_shape == "nested":
        previous = (f"target=member:moving AND previous.source={_sql(_record(snapshot['source']))}")
        memory._execute("CREATE change:legacy_detected SET operation='detected_change', "
                        f"previous={{members:(SELECT VALUE previous FROM change WHERE {previous})}}; "
                        f"DELETE change WHERE {previous};")

    assert memory.read("moving")["original"]["path"] == new_path
    historical = memory.read(basis["member"], source_version=basis["source_version"],
                             start_line=basis["start_line"], end_line=basis["end_line"])["original"]
    assert historical == original
    assert memory._execute(f"SELECT * FROM ONLY {_sql(_record(basis['source_version']))};")[0] == snapshot
    assert memory._execute("SELECT embedding,input_revision FROM ONLY member:moving;")[0] == before_vector


def test_source_path_only_change_has_a_distinct_immutable_snapshot(memory):
    old_path, new_path = "old-name.md", "new-name.md"
    text = "Identical bytes retain the old source location.\n"
    (memory.config.root / old_path).write_text(text, encoding="utf-8")
    prepared = memory.prepare([old_path])
    memory.apply({"sources": [{"path": old_path, "revision": prepared["sources"][0]["revision"]}],
                  "members": [{"id": "renamed", "kind": "chunk", "path": old_path,
                               "title": "Condition", "start_line": 1, "end_line": 1}]})
    original = memory.read("renamed")["original"]
    old_member = memory.read("renamed")["member"]
    old_snapshot = memory._execute(f"SELECT * FROM ONLY {_sql(_record(original['source_version']))};")[0]
    (memory.config.root / old_path).rename(memory.config.root / new_path)
    prepared = memory.prepare([old_path, new_path])
    source = next(item for item in prepared["sources"] if item["path"] == new_path)
    memory.apply({"sources": [{"id": old_member["source"], "path": new_path,
                               "revision": source["revision"]}],
                  "expected": prepared["expected"],
                  "members": [{"id": "renamed", "kind": "chunk", "path": new_path,
                               "title": "Condition", "start_line": 1, "end_line": 1}]})
    current = memory.read("renamed")["original"]
    assert current["path"] == new_path
    assert current["source_version"] != original["source_version"]
    assert len(memory._rows("source_version")) == 2
    assert old_snapshot["path"] == old_path
    assert memory._execute(f"SELECT * FROM ONLY {_sql(_record(original['source_version']))};")[0] == old_snapshot
    assert memory.read("renamed", source_version=original["source_version"],
                       start_line=1, end_line=1)["original"] == original


def test_concurrent_same_bytes_source_move_rejects_the_old_publication(memory, monkeypatch):
    old_path, new_path = "before.md", "after.md"
    data = b"Unchanged original bytes.\n"
    for path in (old_path, new_path):
        (memory.config.root / path).write_bytes(data)
    source = memory.prepare([old_path])["sources"][0]
    memory.apply({"sources": [{"path": old_path, "revision": source["revision"]}]})
    source_id = memory.sources()[0]["id"]
    publish = memory._publish
    moved = False

    def interleaved(statements, **kwargs):
        nonlocal moved
        # A competing transaction has accepted the same bytes at a new path.
        # Inject it after the old publication prepared, before its transaction.
        snapshot = {"source": _record(source_id), "revision": source["revision"],
                    "path": new_path, "kind": "text", "text": data.decode("utf-8")}
        memory._execute(f"BEGIN; CREATE source_version:concurrent_move CONTENT {_sql(snapshot)}; "
                        f"UPDATE {_sql(_record(source_id))} "
                        f"SET path={_sql(new_path)}, version=source_version:concurrent_move; COMMIT;")
        moved = True
        return publish(statements, **kwargs)

    monkeypatch.setattr(memory, "_publish", interleaved)
    with pytest.raises(RuntimeError, match="Concurrent source version changed"):
        memory.apply({"sources": [{"id": source_id, "path": old_path, "revision": source["revision"]}]})
    assert moved
    assert memory.sources()[0]["path"] == new_path


@pytest.mark.parametrize("move_source", [False, True])
def test_legacy_rebound_member_keeps_its_old_basis_readable(memory, move_source):
    path = "legacy.md"
    data = b"Unchanged original evidence.\n"
    (memory.config.root / path).write_bytes(data)
    source = memory.prepare([path])["sources"][0]
    memory.apply({"sources": [{"path": path, "revision": source["revision"]}],
                  "members": [{"id": "rebound", "kind": "chunk", "path": path,
                               "title": "Condition", "start_line": 1, "end_line": 1}],
                  "nodes": [{"id": "old_claim", "kind": "condition", "text": "Unchanged condition",
                             "evidence": ["rebound"]}]})
    basis = memory.neighbors("node:old_claim")["record"]["basis"][0]
    memory._execute(f"UPDATE {_sql(_record(basis['source_version']))} UNSET path;")
    original = memory.read("rebound")["original"]
    (memory.config.root / path).write_bytes(data + b"New unrelated material.\n")
    source = memory.prepare([path])["sources"][0]
    memory.apply({"sources": [{"path": path, "revision": source["revision"]}]})
    # Old clients rebound unchanged siblings without recording a member accept.
    memory._execute("UPDATE member:rebound SET source_version=(SELECT VALUE version FROM ONLY "
                    f"{_sql(_record(memory.sources()[0]['id']))}), source_revision={_sql(source['revision'])};")
    if move_source:
        new_path = "moved.md"
        (memory.config.root / new_path).write_bytes(data)
        prepared = memory.prepare([path, new_path])
        source = next(item for item in prepared["sources"] if item["path"] == new_path)
        memory.apply({"sources": [{"path": new_path, "revision": source["revision"]}],
                      "expected": prepared["expected"],
                      "members": [{"id": "rebound", "kind": "chunk", "path": new_path,
                                   "title": "Condition", "start_line": 1, "end_line": 1}]})
    assert memory.read(basis["member"], source_version=basis["source_version"],
                       start_line=basis["start_line"], end_line=basis["end_line"])["original"] == original
