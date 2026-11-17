from types import SimpleNamespace

import pytest

from basepack.memory import vectors
from basepack.memory.draft import freeze
from basepack.memory.store import Memory, _record, _sql
from test_memory_store import deterministic_vector, memory


class FakeMemory:
    def __init__(self, compatible):
        self.config = SimpleNamespace(machine=object())
        self.compatible = compatible
        self.queries = []

    def _execute(self, sql):
        self.queries.append(sql)
        if "LIMIT 1" in sql and "distance" not in sql:
            return [["member:a"]]
        if "SELECT id,path FROM member" in sql:
            return [[{"id": "member:a", "path": "a.md"}, {"id": "member:b", "path": "b.md"}],
                    self.compatible]
        return [[{"id": "member:a", "path": "a.md"}]]


class FakeClient:
    def __init__(self, machine):
        pass

    def embed(self, inputs, timeout):
        return {"embedding_identity": "same-model", "vectors": [[1.0, 0.0] for _ in inputs]}


def test_vector_search_exposes_partial_compatible_coverage(monkeypatch):
    monkeypatch.setattr(vectors, "EmbeddingClient", FakeClient)
    memory = FakeMemory(["member:a"])
    result = vectors.vector_search(memory, "task")
    assert result["matches"] == [{"id": "member:a", "path": "a.md"}]
    assert result["vector_coverage"] == {"identity": "same-model", "total": 2, "compatible": 1,
                                         "pending": 1, "pending_members": [{"id": "member:b", "path": "b.md"}]}
    assert "ORDER BY distance ASC, id ASC" in memory.queries[-1]


def test_vector_search_reports_missing_identity_instead_of_silent_text_fallback(monkeypatch):
    monkeypatch.setattr(vectors, "EmbeddingClient", FakeClient)
    with pytest.raises(ValueError, match="No compatible memory vectors.*pending: 2"):
        vectors.vector_search(FakeMemory([]), "task")


@pytest.mark.parametrize("mode", ["vector", "hybrid"])
@pytest.mark.parametrize("limit", [0, 1, 6])
@pytest.mark.parametrize("projected", [False, True])
def test_brief_reads_published_overview_without_search_or_model(mode, limit, projected, tmp_path, monkeypatch):
    password_file = tmp_path / "password.txt"
    password_file.write_text("test-password", encoding="utf-8")
    root = tmp_path / "project"
    config = SimpleNamespace(memory_search_mode=mode, memory_password_file=password_file,
                             root=root, memory_dir=root / ".basepack" / "memory",
                             raw={"memory": {"username": "root", "source_scope": ["docs"]}})
    memory = Memory(config)
    memory.sources = lambda: []
    mandatory = {"id": "member:mandatory", "source": "source:must", "path": "docs/must.md",
                 "source_revision": "accepted", "stale": False, "text": "Always deliver this."}
    overview = {"id": "member:map", "knowledge_revision": "member-revision", "path": "docs/map.md",
                "kind": "file", "title": "overview"}
    node = {"id": "node:map", "knowledge_revision": "node-revision", "kind": "decision",
            "title": "n" * 200, "text": "x" * 1000,
            "internal_detail": "Do not copy into startup context."}
    memory._execute = lambda sql: [[mandatory], [], [], [], [], [overview], [node]]
    projection_reads = []
    access = {"access_interval": [0.05, 0.2] if projected else [0.0, 1.0],
              "access_status": "ready" if projected else "cold_start",
              "access_model": "model:observed" if projected else None,
              "access_compiled_j": 7 if projected else None, "access_fact_j": 7,
              "access_support": 2 if projected else None, "access_prior": False if projected else None}
    def read_projection(items):
        projection_reads.append(items)
        return [{**item, **access} for item in items]
    memory.access_hints = read_projection
    memory._check_changes = lambda *args, **kwargs: pytest.fail("brief scanned sources")
    for name in ("vector_search", "hybrid_search"):
        setattr(memory, name, lambda *args, **kwargs: pytest.fail("brief searched"))
    memory.search = lambda *args, **kwargs: pytest.fail("brief searched")
    monkeypatch.setattr("basepack.embedding.admin.status", lambda *args, **kwargs: pytest.fail("brief inspected the model"))
    result = memory.brief("semantic task", limit=limit)
    assert [item["id"] for item in result["mandatory"]] == ["member:mandatory"]
    assert result["mandatory"][0]["text"] == "Always deliver this."
    assert len(result["clues"]) == min(limit, 2)
    assert all(item["clue_role"] == "map" for item in result["clues"])
    assert result["overview_count"] == 2
    assert result["clues_omitted_count"] == 2 - len(result["clues"])
    assert result["overview_groups"] == {"graph_nodes": 1, "project_summaries": 1,
                                          "managed_chat_summaries": 0}
    assert all(all(item[key] == value for key, value in access.items()) for item in result["clues"])
    assert result["overview_sampling"]["candidates"] == (2 if limit else 0)
    if limit:
        assert len(projection_reads) == 1
        assert {item["id"] for item in projection_reads[0]} == {"member:map", "node:map"}
        clue = next(item for item in result["clues"] if item["id"] == "node:map")
        assert len(clue["text"]) == 800 and len(clue["title"]) == 160
        assert clue["text_truncated"] and "internal_detail" not in clue
    else:
        assert projection_reads == []
    assert result["vector_coverage"] == {"status": "not_checked"}
    assert "vector_pending_count" not in result
    assert "changes" not in result


def test_vector_rebuild_reports_coverage_and_reuses_published_input(memory):
    from test_memory_store import batch_for

    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    storage = batch['members'][2]['id']
    memory.apply(batch)
    assert len(memory.embed_members()["reused"]) == 4
    memory._execute("UPDATE member SET embedding=NONE, embedding_identity=NONE, embedded_revision=NONE;")
    (memory.config.root / "guide.md").write_text("原件已有新变化，已发布知识仍可补建。\n", encoding="utf-8")
    first = memory.embed_members([storage])
    assert first["embedded"] == [storage]
    assert len(first["pending"]) == 3
    partial = memory.vector_search("数据库")
    assert partial["vector_coverage"]["total"] == 4
    assert partial["vector_coverage"]["compatible"] == 1
    assert partial["vector_coverage"]["pending"] == 3
    assert memory.brief("数据库")["vector_coverage"] == {"status": "not_checked"}
    assert len(memory.embed_members()["embedded"]) == 3
    assert memory.vector_search("数据库")["vector_coverage"]["pending"] == 0
    assert memory.embed_members()["pending"] == []
    memory._execute(f"UPDATE {_sql(_record(storage))} SET embedding_identity='different-model';")
    coverage = memory.vector_search("数据库")["vector_coverage"]
    assert (coverage["compatible"], coverage["pending"]) == (3, 1)
    assert memory.brief()["vector_coverage"] == {"status": "not_checked"}
    assert memory.embed_members()["embedded"] == [storage]
    memory._execute(f"UPDATE {_sql(_record(storage))} SET embedding=NONE;")
    assert memory.embed_members()["embedded"] == [storage]


@pytest.mark.parametrize("query", ["docs/ADR-0042.md", "ADR-0042.md", "0042"])
def test_hybrid_literal_prioritizes_path_filename_and_identifier_matches(memory, query):
    from test_memory_store import batch_for

    memory.apply(freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")]))
    path = memory.config.root / "docs" / "ADR-0042.md"
    path.parent.mkdir()
    path.write_text("归档决定的原文依据。\n", encoding="utf-8")
    prepared = memory.prepare(["docs/ADR-0042.md"])
    batch = freeze([{"sources": [{"path": "docs/ADR-0042.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"kind": "chunk", "path": "docs/ADR-0042.md", "title": "归档条目",
                       "start_line": 1, "end_line": 1}]}])
    archive = batch['members'][0]['id']
    memory.apply(batch)
    # The literal match falls outside the vector limit and ties the first
    # semantic-only hit on RRF score.
    vector = deterministic_vector(query)
    memory._execute(f"UPDATE member SET embedding={_sql(vector)}; "
                    f"UPDATE {_sql(_record(archive))} SET embedding={_sql([-value for value in vector])};")
    hits = memory.hybrid_search(query, literal=True, limit=3)["matches"]
    assert hits[0]["id"] == archive
    assert hits[0]["lexical_rank"] == 1
    assert "vector_rank" not in hits[0]
    supplements = hits[1:]
    assert supplements
    assert hits[0]["rrf_score"] == supplements[0]["rrf_score"]
    assert all("vector_rank" in row and "lexical_rank" not in row for row in supplements)
