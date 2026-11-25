from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from basepack.memory import codex_index, owner
from basepack.memory.dialogue_query import dialogue_locations, read_chunk
from basepack.memory.draft import freeze, freeze_file
from basepack.memory.graph_retrieval import graph_query
from basepack.memory.graph_query_store import read_source_version
from basepack.memory.stages import fixed_reference
from basepack.memory.store import _record, _sql
from test_memory_store import DeterministicEmbeddingClient, EMBEDDING_IDENTITY, batch_for, memory


def _snapshot(thread_id, texts, ancestors):
    return {"thread_id": thread_id, "parts": [
        {"text": text, "bookmark": {"thread_id": thread_id, "turn_id": "turn", "item_id": str(index),
                                    "part": 0, "role": "user", "part_sha256": sha256(text.encode()).hexdigest(),
                                    "byte_start": 0, "byte_end": len(text.encode())}}
        for index, text in enumerate(texts)], "complete": True, "gaps": [], "ancestor_thread_ids": ancestors}


def test_dialogue_queries_preserve_exact_message_and_authorization(memory, monkeypatch):
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    cfg = memory.config
    cfg = memory.config = replace(cfg, machine=replace(cfg.machine, raw={"embedding": {"endpoint": "http://127.0.0.1"}}))
    cfg.memory_dir.mkdir(parents=True)
    manifest = cfg.root / ".basepack/dialogues.json"
    cfg.raw["memory"]["chat_index"] = {"manifest": manifest.relative_to(cfg.root).as_posix()}
    public_id, private_id, ancestor_id = (str(uuid4()) for _ in range(3))
    authorization = {"schema_version": 1, "bindings": {"test": {"project_id": "test", "root": ".",
                                                                 "other_project_roots": []}},
                     "threads": [{"thread_id": thread_id, "binding": "test", "path": f"dialogues/{thread_id}",
                                  "private": private} for thread_id, private in
                                 [(public_id, False), (private_id, True), (ancestor_id, False)]]}
    manifest.write_text(json.dumps(authorization), encoding="utf-8")
    assert memory.vector_search("no file or dialogue has been indexed")["matches"] == []
    control = cfg.memory_dir / "maintenance" / "dialogue-test.control"
    assert owner.acquire(cfg.memory_dir, memory.connection["project_id"], "test", control)["acquired"]
    prompt = "校验这条限定 🧪"
    texts = [prompt, "数值阈值以附件为准。"]
    public, private = [codex_index.index_thread(memory, _snapshot(thread_id, texts, ancestors), control=control,
                                               path=f"dialogues/{thread_id}", private=is_private)
                       for thread_id, is_private, ancestors in [(public_id, False, [ancestor_id]),
                                                                (private_id, True, [])]]
    owner.stop_owned(cfg.memory_dir, control)
    owner.release(cfg.memory_dir, control)

    # Both ordinary modes can query a database with an index but no file members.
    for search in (memory.vector_search, memory.hybrid_search):
        result = search(prompt, allow_private=False)
        assert result["vector_coverage"]["total"] == 0
        assert result["dialogue_vector_coverage"]["compatible"] == 2
        assert [_record(row["id"]) for row in result["matches"]] == [_record(public["node"])] * 2
        assert all(row["bookmark"]["thread_id"] == public_id for row in result["matches"])
        assert prompt not in json.dumps(result, ensure_ascii=False)
        assert search(prompt, scope="unrelated/")["matches"] == []
    all_hits = memory.vector_search(prompt)["matches"]
    assert len(all_hits) == 4
    private_hit = next(row for row in all_hits if row["thread_id"] == private_id and row["bookmark"]["item_id"] == "0")
    hit = memory.vector_search(prompt, allow_private=False)["matches"][0]
    assert hit["bookmark"]["item_id"] == "0"
    graph = graph_query(memory, prompt)
    assert graph["seeds"][0]["dialogue_chunk"] == hit["dialogue_chunk"]
    assert graph["candidates"][0]["bookmark"] == hit["bookmark"]
    assert graph_query(memory, seeds=[private["node"]])["seeds"] == []

    locations = dialogue_locations(memory, public["node"], limit=1)
    assert locations["locations"][0]["dialogue_chunk"] == hit["dialogue_chunk"]
    assert locations["next_offset"] == 1
    assert dialogue_locations(memory, public["node"], offset=1)["locations"][0]["bookmark"]["item_id"] == "1"

    effects = []

    def host_read(bookmark, *, context):
        effects.append((bookmark, context))
        return {"bookmark": bookmark, "text": prompt, "context": [], "gaps": []}

    host = SimpleNamespace(read=host_read)
    assert read_chunk(memory, hit["dialogue_chunk"], host=host)["original"]["text"] == prompt
    assert len(effects) == 1
    with pytest.raises(ValueError, match="unavailable"):
        read_chunk(memory, hit["dialogue_chunk"], host=host, scope="unrelated/")
    with pytest.raises(ValueError, match="unavailable"):
        read_chunk(memory, private_hit["dialogue_chunk"], host=host)
    assert read_chunk(memory, private_hit["dialogue_chunk"], host=host, allow_private=True)["original"]["text"] == prompt
    assert len(effects) == 2
    with pytest.raises(ValueError, match="content revision"):
        read_chunk(memory, hit["dialogue_chunk"], host=SimpleNamespace(
            read=lambda bookmark, **kwargs: {"bookmark": bookmark, "text": "revised"}))

    # Publish a native version-pinned business edge, then traverse it in reverse.
    prepared = freeze([batch_for(memory, "# Data\nAccepted measurement.\n\n# Evidence\nOriginal data.\n")])
    memory.apply(prepared)
    artifact = prepared["members"][0]["id"]
    dialogue_revision = locations["record"]["knowledge_revision"]
    artifact_revision = memory.knowledge(artifact)["knowledge_revision"]
    edge = {"type": "supports", "in": public["node"], "out": artifact,
            "text": "This discussion supports the selected measurement.",
            "endpoint_versions": {"in": {"id": public["node"], "knowledge_revision": dialogue_revision},
                                  "out": {"id": artifact, "knowledge_revision": artifact_revision}},
            "basis": [{"id": artifact, "knowledge_revision": artifact_revision}]}
    basis_only = {"type": "supports", "in": prepared["members"][2]["id"], "out": artifact,
                  "text": "The selected measurement has independent support in the dialogue.",
                  "basis": [{"id": public["node"], "knowledge_revision": dialogue_revision}]}
    fixed = memory.prepare(["guide.md"], historical_versions=[{"id": public["node"],
                                                              "knowledge_revision": dialogue_revision}])
    prepare_path = cfg.root / "prepared.json"
    prepare_path.write_text(json.dumps(fixed, ensure_ascii=False), encoding="utf-8")
    batch = freeze_file([{"prepare": fixed_reference(prepare_path), "edges": [edge, basis_only]}],
                        cfg.root / "frozen.json", config=cfg)
    memory.apply(batch)
    reverse = graph_query(memory, seeds=[artifact], branches=["in:supports"])
    assert any(_record(row["id"]) == _record(public["node"]) and row["codex_thread_id"] == public_id
               for row in reverse["candidates"])
    forward = graph_query(memory, seeds=[public["node"]], branches=["out:supports"])
    assert any(_record(row["id"]) == _record(artifact) for row in forward["candidates"])
    exact = locations["record"]["exact_id"]
    edge_id = batch["edges"][0]["id"]
    edge_exact = memory.knowledge(edge_id)["exact_id"]
    basis_edge_id = batch["edges"][1]["id"]
    assert memory.knowledge(basis_edge_id)["direct_basis"]
    artifact_basis = [{"id": artifact, "knowledge_revision": artifact_revision,
                       "source_version": memory.knowledge(artifact)["source_version"]}]
    assert any(_record(row["record"]["id"]) == _record(edge_id)
               for row in memory.basis_dependents(artifact_basis))

    for drift in ({"excluded_thread_ids": [ancestor_id]},
                  {"threads": [dict(row, private=True) if row["thread_id"] == ancestor_id else row
                               for row in authorization["threads"]]},
                  {"threads": [row for row in authorization["threads"] if row["thread_id"] != ancestor_id]}):
        manifest.write_text(json.dumps({**authorization, **drift}), encoding="utf-8")
        assert memory.vector_search(prompt, scope=f"dialogues/{public_id}", allow_private=True)["matches"] == []
        assert graph_query(memory, seeds=[public["node"], exact], allow_private=True)["seeds"] == []
        with pytest.raises(ValueError, match="unavailable"):
            read_chunk(memory, hit["dialogue_chunk"], host=host, allow_private=True)
        assert not any(_record(row["record"]["id"]) == _record(edge_id)
                       for row in memory.basis_dependents(artifact_basis))

    # A known record ID and stored vectors confer no access after authorization is removed.
    manifest.write_text(json.dumps({**authorization, "excluded_thread_ids": [public_id]}), encoding="utf-8")
    assert memory.vector_search(prompt, allow_private=False)["matches"]
    assert not any("dialogue_chunk" in row for row in memory.vector_search(prompt, allow_private=False)["matches"])
    with pytest.raises(ValueError, match="unavailable"):
        read_chunk(memory, hit["dialogue_chunk"], host=host, allow_private=True)
    cfg.raw["memory"].pop("chat_index")
    assert not any("dialogue_chunk" in row for row in memory.vector_search(prompt)["matches"])
    for record_id in (public["node"], exact, edge_id, edge_exact, basis_edge_id):
        with pytest.raises(ValueError, match="unavailable"):
            memory.knowledge(record_id)
        assert graph_query(memory, seeds=[record_id])["seeds"] == []
    assert not any(_record(row["id"]) == _record(public["node"])
                   for row in graph_query(memory, seeds=[artifact])["candidates"])
    assert not any(_record(row["record"]["id"]) == _record(edge_id)
                   for row in memory.basis_dependents(artifact_basis))
    with pytest.raises(ValueError, match="unavailable"):
        memory.history(public["node"])
    with pytest.raises(ValueError, match="unavailable"):
        read_chunk(memory, hit["dialogue_chunk"], host=host)
    assert len(effects) == 2
    assert public_id not in json.dumps(memory.brief(), ensure_ascii=False)
    assert public_id not in json.dumps(memory.prepare(["guide.md"]), ensure_ascii=False)


def test_indexed_mode_blocks_only_retained_codex_captures(memory):
    text = "prior snapshot\n"
    capture = "source_version:legacychat"
    project_file = "source_version:legitimatesource"
    frame = json.dumps({"byte_length": len(text.encode()), "chat_url": "test", "thread_id": "test",
                        "turn_id": "turn", "item_id": "item", "part": 0, "role": "user", "part_type": "text"})
    for position, path, body in [(capture, ".basepack/memory/codex/thread.md", f"{frame}\n{text}\n"),
                                 (project_file, ".basepack/project-notes.md", text)]:
        fields = {"kind": "text", "text": body, "revision": sha256(body.encode()).hexdigest(),
                  "private": False, "path": path}
        memory._execute(f"CREATE {_sql(_record(position))} CONTENT {_sql(fields)};")
    options = {"start_line": 1, "end_line": 1}
    assert read_source_version(memory, capture, start_line=2, end_line=2)["original"]["text"] == text
    memory.config.raw["memory"]["chat_index"] = {"manifest": ".basepack/dialogues.json"}
    (memory.config.root / ".basepack").mkdir(parents=True, exist_ok=True)
    (memory.config.root / ".basepack/dialogues.json").write_text(
        json.dumps({"schema_version": 1, "bindings": {}, "threads": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Readable source snapshot not found"):
        read_source_version(memory, capture, **options)
    assert read_source_version(memory, project_file, **options)["original"]["text"] == text
    with pytest.raises(ValueError, match="Original unavailable"):
        memory.prepare(["./.basepack/memory/codex/thread.md"])
