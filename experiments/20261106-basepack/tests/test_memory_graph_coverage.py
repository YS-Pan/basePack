"""Exercise exact current endpoint pins and aggregate-only graph reports."""

from types import SimpleNamespace

from basepack.memory.graph_coverage import coverage
from basepack.memory.store import _sql
from test_memory_store import memory


def test_empty_graph_uses_one_metadata_query():
    queries = []

    def execute(query):
        queries.append(query)
        return [{"members": [], "nodes": [], "sources": [], "edges": []}]

    assert coverage(SimpleNamespace(_execute=execute)) == {
        "fresh_vertices": {"members": 0, "nodes": 0, "total": 0},
        "business_relationships": {"active": 0, "current_pinned": 0, "non_current_pins": 0,
                                   "missing_or_unreliable_pins": 0},
        "touched_vertices": {"members": 0, "nodes": 0, "total": 0, "fraction": None},
    }
    query, = queries
    assert not {"path", "text", "basis", "private"} & set(query.split())


def test_metadata_handles_alternate_record_spellings_and_invalid_pins():
    current = {"id": "graph_edge:one", "pinned_in_id": "knowledge_version:⟨a-b⟩",
               "pinned_out_id": "knowledge_version:b"}
    graph = {"members": [{"id": "member:a", "exact_id": "knowledge_version:`a-b`"}],
             "nodes": [{"id": "node:b", "exact_id": "knowledge_version:b"}], "sources": [],
             "edges": [current, {**current, "id": "graph_edge:two"},
                       {**current, "pinned_in_id": "knowledge_version:`unclosed"},
                       {**current, "pinned_in_id": "member:different"}, {**current, "pinned_out_id": None},
                       {**current, "pinned_out_id": "knowledge_version:b-previous"}]}
    assert coverage(SimpleNamespace(_execute=lambda _: [graph])) == {
        "fresh_vertices": {"members": 1, "nodes": 1, "total": 2},
        "business_relationships": {"active": 6, "current_pinned": 2, "non_current_pins": 1,
                                   "missing_or_unreliable_pins": 3},
        "touched_vertices": {"members": 1, "nodes": 1, "total": 2, "fraction": 1.0},
    }


def test_coverage_reads_only_fresh_heads_and_exact_current_endpoints(memory):
    def vertex(identity, revision, *, stale=False, retired=False):
        return (f"CREATE {identity} SET knowledge_revision={_sql(revision)}, stale={_sql(stale)}, "
                f"retired={_sql(retired)}, path='private/sample.md', text='private text'; ")

    memory._execute(
        vertex("member:a", "a0") + "UPDATE member:a SET knowledge_revision='a1'; "
        + vertex("member:isolated", "i1") + vertex("node:b", "b1")
        + vertex("node:stale", "s1", stale=True) + vertex("member:retired", "r1", retired=True)
    )
    exact, = memory._execute("RETURN {a:fn::knowledge_id(member:a,'a1'), old:fn::knowledge_id(member:a,'a0'), "
                             "b:fn::knowledge_id(node:b,'b1'), s:fn::knowledge_id(node:stale,'s1'), "
                             "r:fn::knowledge_id(member:retired,'r1')};")

    def edge(identity, start, end, status="current"):
        return (f"CREATE graph_state:{identity} SET status={_sql(status)}; "
                f"RELATE {start}->graph_edge:{identity}->{end} SET "
                f"logical_id=semantic:{identity}, knowledge_revision={_sql(identity)}, state=graph_state:{identity}, "
                "type='supports', private=true, scope_paths=['private/sample.md'], text='private relation'; ")

    memory._execute(
        edge("current", exact["a"], exact["b"]) + edge("also_current", exact["a"], exact["b"])
        + edge("old_version", exact["old"], exact["b"]) + edge("old_head", exact["a"], exact["s"])
        + edge("retired_endpoint", exact["a"], exact["r"])
        + edge("stale_edge", exact["a"], exact["b"], "needs_review")
        + edge("retired_edge", exact["a"], exact["b"], "retired")
    )
    assert coverage(memory) == {
        "fresh_vertices": {"members": 2, "nodes": 1, "total": 3},
        "business_relationships": {"active": 5, "current_pinned": 2, "non_current_pins": 3,
                                   "missing_or_unreliable_pins": 0},
        "touched_vertices": {"members": 1, "nodes": 1, "total": 2, "fraction": 2 / 3},
    }
