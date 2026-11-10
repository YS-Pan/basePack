from types import SimpleNamespace

import pytest

from basepack.memory import vectors
from basepack.memory.store import Memory
from test_memory_store import memory


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


def test_vector_search_exposes_partial_compatible_coverage_without_changing_python_list(monkeypatch):
    monkeypatch.setattr(vectors, "EmbeddingClient", FakeClient)
    memory = FakeMemory(["member:a"])
    assert vectors.vector_search(memory, "task") == [{"id": "member:a", "path": "a.md"}]
    result = vectors.vector_search(memory, "task", include_coverage=True)
    assert result["vector_coverage"] == {"identity": "same-model", "total": 2, "compatible": 1,
                                         "pending": 1, "pending_members": [{"id": "member:b", "path": "b.md"}]}
    assert "ORDER BY distance ASC, id ASC" in memory.queries[-1]


def test_vector_search_reports_missing_identity_instead_of_silent_text_fallback(monkeypatch):
    monkeypatch.setattr(vectors, "EmbeddingClient", FakeClient)
    with pytest.raises(ValueError, match="No compatible memory vectors.*pending: 2"):
        vectors.vector_search(FakeMemory([]), "task", include_coverage=True)


def test_brief_uses_configured_vector_related_and_does_not_scan(monkeypatch):
    config = SimpleNamespace(memory_search_mode="vector", raw={"memory": {"source_scope": ["docs"]}})
    memory = Memory(config)
    memory.sources = lambda: []
    memory._execute = lambda sql: [[], [], [], [], [], []]
    memory._check_changes = lambda *args, **kwargs: pytest.fail("brief scanned sources")
    coverage = {"identity": "same-model", "total": 2, "compatible": 1, "pending": 1,
                "pending_members": [{"id": "member:b", "path": "b.md"}]}
    memory.vector_search = lambda task, **kwargs: {"matches": [{"id": "member:a", "title": "related"}],
                                                  "vector_coverage": coverage}
    memory.search = lambda *args, **kwargs: pytest.fail("brief fell back to text")
    result = memory.brief("semantic task", limit=6)
    assert result["clues"][0]["id"] == "member:a"
    assert result["vector_coverage"] == coverage
    assert result["vector_pending_count"] == 1
    assert result["changes"] == []


def test_text_library_rebuild_reports_coverage_and_reuses_published_input(memory, monkeypatch):
    from test_memory_store import batch_for

    memory.config.raw["memory"]["search_mode"] = "text"
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    (memory.config.root / "guide.md").write_text("原件已有新变化，已发布知识仍可补建。\n", encoding="utf-8")
    monkeypatch.setattr(vectors, "status", lambda _: {"model": {"embedding_identity": "same-model"}})
    monkeypatch.setattr(vectors, "EmbeddingClient", FakeClient)
    first = memory.embed_members(["storage"])
    assert first["embedded"] == ["member:storage"]
    assert len(first["pending"]) == 3
    memory.config.raw["memory"]["search_mode"] = "vector"
    partial = memory.vector_search("数据库", include_coverage=True)
    assert partial["vector_coverage"]["total"] == 4
    assert partial["vector_coverage"]["compatible"] == 1
    assert partial["vector_coverage"]["pending"] == 3
    assert memory.brief("数据库")["vector_pending_count"] == 3
    assert len(memory.embed_members()["embedded"]) == 3
    assert memory.vector_search("数据库", include_coverage=True)["vector_coverage"]["pending"] == 0
    assert memory.embed_members()["pending"] == []
    memory._execute("UPDATE member:storage SET embedding_identity='different-model';")
    coverage = memory.vector_search("数据库", include_coverage=True)["vector_coverage"]
    assert (coverage["compatible"], coverage["pending"]) == (3, 1)
    monkeypatch.setattr("basepack.embedding.admin.status", lambda _: {"model": {"embedding_identity": "same-model"}})
    assert memory.brief()["vector_pending_count"] == 1
    assert memory.embed_members()["embedded"] == ["member:storage"]
    memory._execute("UPDATE member:storage SET embedding=NONE;")
    assert memory.embed_members()["embedded"] == ["member:storage"]
