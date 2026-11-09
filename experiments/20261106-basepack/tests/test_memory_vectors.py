"""Actual shared-model text/image integration; no model is started by tests."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import os
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib
from urllib.error import HTTPError

import pytest

from basepack.project.config import load_machine_config
from basepack.memory.store import Memory
from test_memory_store import batch_for, memory


def visual_fixture(path: Path):
    # This exact fixture was opened and visually read during implementation:
    # white background, red triangle left, blue square right, no text.
    width, height = 384, 240
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if 50 <= y <= 200 and 105 - (y - 50) * 65 / 150 <= x <= 105 + (y - 50) * 65 / 150:
                rgb = (220, 30, 30)
            elif 220 <= x <= 345 and 70 <= y <= 190:
                rgb = (30, 80, 220)
            else:
                rgb = (255, 255, 255)
            row.extend(rgb)
        rows.append(b"\0" + row)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def test_real_shared_multilevel_vectors_image_and_identity(memory, tmp_path):
    if "BASEPACK_MEMORY_TEST_MACHINE" not in os.environ:
        pytest.skip("requires explicit existing shared embedding machine config")
    memory.config = replace(memory.config, machine=load_machine_config(os.environ["BASEPACK_MEMORY_TEST_MACHINE"]))
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    assert memory.vector_search("数据库", scope="missing/") == []
    with pytest.raises(ValueError, match="No compatible memory vectors"):
        memory.hybrid_search("数据库")
    encoded = memory.embed_members()
    assert set(encoded["embedded"]) == {"member:guide", "member:storage_section", "member:storage", "member:retention"}
    hits = memory.vector_search("How does the local database separate projects?", limit=4)
    assert {row["kind"] for row in hits} == {"file", "section", "chunk"}
    assert all(row["embedded_revision"] == row["input_revision"] for row in hits)
    assert all("embedding" not in row for row in hits)
    assert len(memory.embed_members()["reused"]) == 4
    memory._execute("UPDATE member SET embedding_identity='different-model';")
    with pytest.raises(ValueError, match="No compatible memory vectors"):
        memory.vector_search("数据库")
    memory._execute(f"UPDATE member SET embedding_identity='{encoded['embedding_identity']}', embedded_revision='old-input';")
    with pytest.raises(ValueError, match="No compatible memory vectors"):
        memory.vector_search("数据库")
    assert len(memory.embed_members()["embedded"]) == 4
    changed = deepcopy(batch)
    changed["expected"] = memory.prepare(["guide.md"])["expected"]
    changed["members"] = changed["members"][:1]
    changed["members"][0]["text"] = "项目数据库必须支持离线隔离，资料必须保留。"
    memory.apply(changed)
    assert "member:guide" not in {row["id"] for row in memory.vector_search("数据库", limit=10)}
    assert memory.embed_members(["guide"])["embedded"] == ["member:guide"]
    memory._execute("UPDATE member:storage SET embedding_identity='another-model-same-dimensions';")
    assert "member:storage" not in {row["id"] for row in memory.vector_search("数据库", limit=10)}
    memory.embed_members(["storage"])
    image_path = tmp_path / "shapes.png"
    visual_fixture(image_path)
    source = memory.prepare(["shapes.png"])["sources"][0]
    assert source["kind"] == "image"
    description = "白色背景，左侧红色三角形，右侧蓝色正方形，无文字。"
    image_batch = {"sources": [{"path": "shapes.png", "revision": source["revision"], "kind": "image"}],
                   "members": [{"id": "shapes", "kind": "image", "path": "shapes.png", "parent": None,
                                "title": "形状图", "text": description,
                                "locator": {"page": None, "region": None}}]}
    memory.apply(image_batch)
    image_encoded = memory.embed_members(["shapes"])
    assert image_encoded["embedded"] == ["member:shapes"]
    visual_hits = memory.vector_search("A red triangle beside a blue square on white background", limit=5)
    assert visual_hits[0]["id"] == "member:shapes"
    assert visual_hits[0]["embedding_kind"] == "image"
    original = memory.read("shapes")["original"]
    assert sha256(Path(original["image_path"]).read_bytes()).hexdigest() == source["revision"]
    assert len(list((memory.config.memory_dir / "assets").iterdir())) == 1
    image_batch["members"][0]["text"] = "左红三角，右蓝方块；图中没有文字。"
    image_batch["expected"] = memory.prepare(["shapes.png"])["expected"]
    memory.apply(image_batch)
    assert memory.embed_members(["shapes"])["reused"] == ["member:shapes"]
    hybrid = memory.hybrid_search("资料", limit=5)
    assert all("rrf_score" in row and "embedding" not in row for row in hybrid)
    assert "member:retention" in {row["id"] for row in hybrid}


def test_real_native_restore_and_rebuild_from_retained_text_and_pixels(memory, tmp_path):
    if not {"BASEPACK_MEMORY_TEST_MACHINE", "BASEPACK_MEMORY_TEST_SURREAL"} <= os.environ.keys():
        pytest.skip("requires an existing shared model and native SurrealDB executable")
    memory.config = replace(memory.config, machine=load_machine_config(os.environ["BASEPACK_MEMORY_TEST_MACHINE"]))
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    visual_fixture(tmp_path / "shapes.png")
    prepared = memory.prepare(["shapes.png"])
    memory.apply({"sources": [{"path": "shapes.png", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "shapes", "kind": "image", "path": "shapes.png", "title": "形状示意图",
                       "text": "白底，左侧红三角，右侧蓝方块。", "locator": {"page": 1}}],
                  "edges": [{"id": "visual", "in": "member:shapes", "out": "node:local",
                             "kind": "illustrates", "text": "测试图与项目决定在同库共存", "evidence": ["shapes"]}]})
    memory.embed_members()
    before = {table: memory._execute(f"SELECT * FROM {table} ORDER BY id;")[0]
              for table in ["member", "node", "semantic", "source", "source_version", "change"]}
    export = tmp_path.parent / (tmp_path.name + "_backup.surql")
    arguments = ["--endpoint", memory.connection["endpoint"], "--username", memory.connection["username"],
                 "--password", os.environ[memory.connection["password_env"]], "--namespace", "memsys"]
    executable = os.environ["BASEPACK_MEMORY_TEST_SURREAL"]
    subprocess.run([executable, "export", *arguments, "--database", "product_tests", str(export)],
                   check=True, capture_output=True, text=True)
    moved = tmp_path.parent / (tmp_path.name + "_restored")
    shutil.copytree(tmp_path, moved)
    restored_raw = deepcopy(memory.config.raw)
    restored_raw["memory"]["database"] = "product_vectors_tests"
    restored = Memory(replace(memory.config, root=moved, raw=restored_raw))
    memory._execute("REMOVE DATABASE IF EXISTS product_vectors_tests; DEFINE DATABASE product_vectors_tests;")
    subprocess.run([executable, "import", *arguments, "--database", "product_vectors_tests", str(export)],
                   check=True, capture_output=True, text=True)
    after = {table: restored._execute(f"SELECT * FROM {table} ORDER BY id;")[0] for table in before}
    assert before == after
    assert restored.read("shapes")["original"]["image_path"].startswith(str(moved))
    assert restored.read("storage")["original"]["text"] == "本地数据库隔离项目。\n"
    # Drop only rebuildable vector data, preserving accepted prose, boundaries,
    # relations, original pixels and correction history from the native backup.
    restored._execute("UPDATE member SET embedding=NONE, embedding_identity=NONE, embedded_revision=NONE RETURN NONE;")
    with pytest.raises(ValueError, match="No compatible memory vectors"):
        restored.vector_search("数据库")
    assert len(restored.embed_members()["embedded"]) == 5
    assert restored.vector_search("A red triangle next to a blue square", limit=1)[0]["id"] == "member:shapes"
    assert len(restored.neighbors("shapes")["edges"]) == 1


def test_real_file_and_section_token_overflow_keeps_accepted_knowledge(memory, tmp_path):
    if "BASEPACK_MEMORY_TEST_MACHINE" not in os.environ:
        pytest.skip("requires an explicit existing shared model")
    memory.config = replace(memory.config, machine=load_machine_config(os.environ["BASEPACK_MEMORY_TEST_MACHINE"]))
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    long_summary = "维护条件必须保留。" * 500
    batch["members"][0]["text"] = long_summary
    batch["members"][1]["text"] = long_summary
    memory.apply(batch)
    with pytest.raises(HTTPError) as failure:
        memory.embed_members(["guide", "storage_section"])
    error = failure.value
    assert error.code == 500
    members = memory._execute("SELECT id,text,embedding FROM member WHERE id IN [member:guide,member:storage_section];")[0]
    assert all(row["text"] == long_summary and row.get("embedding") is None for row in members)
    (tmp_path / "overflow-evidence.json").write_text(json.dumps({
        "summary_bytes_each": len(long_summary.encode("utf-8")), "http_status": error.code,
        "original_error": str(error), "notes": error.__notes__, "accepted_summary_preserved": True,
        "partial_vectors_written": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
