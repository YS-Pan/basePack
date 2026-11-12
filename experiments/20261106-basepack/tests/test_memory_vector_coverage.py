from types import SimpleNamespace

import pytest

from basepack.memory import vectors
from basepack.memory.store import Memory, _sql
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
def test_brief_reads_published_overview_without_search_or_model(mode, tmp_path, monkeypatch):
    password_file = tmp_path / "password.txt"
    password_file.write_text("test-password", encoding="utf-8")
    config = SimpleNamespace(memory_search_mode=mode, memory_password_file=password_file,
                             raw={"memory": {"username": "root", "source_scope": ["docs"]}})
    memory = Memory(config)
    memory.sources = lambda: []
    memory._execute = lambda sql: [[], [], [], [], [], [{"id": "member:map", "title": "overview"}]]
    memory._check_changes = lambda *args, **kwargs: pytest.fail("brief scanned sources")
    for name in ("vector_search", "hybrid_search"):
        setattr(memory, name, lambda *args, **kwargs: pytest.fail("brief searched"))
    memory.search = lambda *args, **kwargs: pytest.fail("brief searched")
    monkeypatch.setattr("basepack.embedding.admin.status", lambda *args, **kwargs: pytest.fail("brief inspected the model"))
    result = memory.brief("semantic task", limit=6)
    assert result["clues"][0]["id"] == "member:map"
    assert result["clues"][0]["clue_role"] == "map"
    assert result["vector_coverage"] == {"status": "not_checked"}
    assert "vector_pending_count" not in result
    assert "changes" not in result


def test_vector_rebuild_reports_coverage_and_reuses_published_input(memory):
    from test_memory_store import batch_for

    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    assert len(memory.embed_members()["reused"]) == 4
    memory._execute("UPDATE member SET embedding=NONE, embedding_identity=NONE, embedded_revision=NONE;")
    (memory.config.root / "guide.md").write_text("原件已有新变化，已发布知识仍可补建。\n", encoding="utf-8")
    first = memory.embed_members(["storage"])
    assert first["embedded"] == ["member:storage"]
    assert len(first["pending"]) == 3
    partial = memory.vector_search("数据库")
    assert partial["vector_coverage"]["total"] == 4
    assert partial["vector_coverage"]["compatible"] == 1
    assert partial["vector_coverage"]["pending"] == 3
    assert memory.brief("数据库")["vector_coverage"] == {"status": "not_checked"}
    assert len(memory.embed_members()["embedded"]) == 3
    assert memory.vector_search("数据库")["vector_coverage"]["pending"] == 0
    assert memory.embed_members()["pending"] == []
    memory._execute("UPDATE member:storage SET embedding_identity='different-model';")
    coverage = memory.vector_search("数据库")["vector_coverage"]
    assert (coverage["compatible"], coverage["pending"]) == (3, 1)
    assert memory.brief()["vector_coverage"] == {"status": "not_checked"}
    assert memory.embed_members()["embedded"] == ["member:storage"]
    memory._execute("UPDATE member:storage SET embedding=NONE;")
    assert memory.embed_members()["embedded"] == ["member:storage"]


@pytest.mark.parametrize("query", ["docs/ADR-0042.md", "ADR-0042.md", "0042"])
def test_hybrid_literal_prioritizes_path_filename_and_identifier_matches(memory, query):
    from test_memory_store import batch_for

    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    path = memory.config.root / "docs" / "ADR-0042.md"
    path.parent.mkdir()
    path.write_text("归档决定的原文依据。\n", encoding="utf-8")
    prepared = memory.prepare(["docs/ADR-0042.md"])
    memory.apply({"sources": [{"path": "docs/ADR-0042.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "zz_archive", "kind": "chunk", "path": "docs/ADR-0042.md", "title": "归档条目",
                       "start_line": 1, "end_line": 1}]})
    # The literal match falls outside the vector limit. Its RRF score ties the
    # first semantic-only hit, whose ID would sort earlier without literal priority.
    vector = deterministic_vector(query)
    memory._execute(f"UPDATE member SET embedding={_sql(vector)}; "
                    f"UPDATE member:zz_archive SET embedding={_sql([-value for value in vector])};")
    hits = memory.hybrid_search(query, literal=True, limit=3)["matches"]
    assert hits[0]["id"] == "member:zz_archive"
    assert hits[0]["lexical_rank"] == 1
    assert "vector_rank" not in hits[0]
    supplements = hits[1:]
    assert supplements
    assert hits[0]["rrf_score"] == supplements[0]["rrf_score"]
    assert all("vector_rank" in row and "lexical_rank" not in row for row in supplements)
