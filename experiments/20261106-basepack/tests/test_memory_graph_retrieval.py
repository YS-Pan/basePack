from collections import defaultdict
from types import SimpleNamespace

import pytest

from basepack.memory import graph_query_store
from basepack.memory.graph_retrieval import graph_query


@pytest.fixture
def network(monkeypatch):
    vertices, edges, calls, batches = {}, [], [], []

    def node(name, *, private=False, path="docs/guide.md"):
        record = f"knowledge_version:{name}"
        vertices[record] = {"id": f"node:{name}", "exact_id": record, "knowledge_revision": "v1",
                            "record_type": "node", "text": name, "private": private, "path": path}
        return record

    def edge(start, end, kind, *, private=False, **fields):
        value = {"id": f"graph_edge:{len(edges)}", "in": start, "out": end, "type": kind,
                 "private": private, "status": "current", **fields}
        edges.append(value)
        return value["id"]

    def get_vertex(memory, exact, *, scope, allow_private):
        row = vertices.get(exact)
        if row and (allow_private or not row["private"]) and row["path"].startswith(scope):
            return row
        return None

    def adjacent(memory, exact, *, direction, types, scope, allow_private, include_stale, limit, **options):
        calls.append((exact, direction, types, limit))
        start, end = {"IN": "out", "OUT": "in"}[direction], direction.lower()
        rows = [{**edge, "neighbor": edge[end]} for edge in edges
                if edge[start] == exact and edge["type"] in types and (allow_private or not edge["private"])
                and get_vertex(memory, edge[end], scope=scope, allow_private=allow_private)]
        return rows[:limit]

    def access_hints(rows):
        batches.append(rows)
        return [{**row, "access_model": "model-A", "access_compiled_j": 7, "access_fact_j": 9,
                 "access_interval": [0.0, 0.0] if row["id"] == "node:counterexample" else [1.0, 1.0]}
                for row in rows]

    monkeypatch.setattr(graph_query_store, "resolve_seed", lambda _memory, id, **kwargs: id)
    monkeypatch.setattr(graph_query_store, "get_vertex", get_vertex)
    monkeypatch.setattr(graph_query_store, "adjacent", adjacent)
    return SimpleNamespace(node=node, edge=edge, calls=calls, batches=batches, vertices=vertices,
                           memory=SimpleNamespace(access_hints=access_hints))


def test_default_two_hops_preserve_replacements_counterevidence_and_exact_provenance(network):
    old = network.node("old-rule")
    current = network.node("replacement")
    counter = network.node("counterexample")
    hidden = network.node("private-rebuttal", private=True)
    outside = network.node("out-of-scope", path="elsewhere/main.md")
    source = "source_version:old-source"
    network.vertices[source] = {
        "id": source, "exact_id": source, "record_type": "source_version", "path": "docs/old.md",
        "private": False, "revision": "raw-1", "source_version": source,
    }
    network.edge(hidden, old, "supersedes", private=True)
    network.edge(outside, old, "supersedes")
    network.edge(old, source, "has_basis", locator={"start_line": 3, "end_line": 5})
    network.edge(old, source, "has_basis", locator={"start_line": 8, "end_line": 8})
    replacement = network.edge(current, old, "supersedes", conditions="Mode X")
    contradiction = network.edge(counter, current, "contradicts", conditions="Mode X and temperature above 50")
    for index in range(40):
        network.edge(old, network.node(f"ordinary-{index}"), "uses")
        network.edge(current, network.node(f"new-ordinary-{index}"), "uses")

    result = graph_query(network.memory, seeds=[old], scope="docs/")
    assert result["limits"] == {"seeds": 4, "hops": 2, "adjacency": 12, "scanned": 96, "candidates": 12}
    candidates = {row["id"]: row for row in result["candidates"]}
    assert "node:replacement" in candidates
    counter_row = candidates["node:counterexample"]
    assert counter_row["initial_score"] == pytest.approx(counter_row["base_score"] - 0.05)
    assert [edge["id"] for edge in counter_row["paths"][0]["edges"]] == [replacement, contradiction]
    assert [edge["conditions"] for edge in counter_row["paths"][0]["edges"]] == [
        "Mode X", "Mode X and temperature above 50"]
    assert [(row["start_line"], row["end_line"]) for row in result["observations"]
            if row["exact_id"] == source] == [(3, 5), (8, 8)]
    assert not ({hidden, outside} & {row["exact_id"] for row in result["observations"]})
    assert len(network.batches) == 1
    assert result["access_snapshot"] == {"access_model": "model-A", "access_compiled_j": 7, "access_fact_j": 9}
    assert any(limit["direction"] == "out" and "uses" in limit["types"] for limit in result["truncation"])
    assert len(result["candidates"]) <= 12
    assert len(result["observations"]) > len(result["candidates"])
    assert all(len(row["paths"][0]["edges"]) <= 2 for row in result["candidates"])


def test_default_two_hops_from_named_seed_through_a_base_seed(network):
    diagnosis = network.node("diagnosis")
    evidence = network.node("evidence")
    network.vertices[evidence]["record_type"] = "member"
    source = "source_version:smoke"
    network.vertices[source] = {
        "id": source, "exact_id": source, "record_type": "source_version", "path": "docs/guide.md",
        "private": False, "revision": "raw-1", "source_version": source,
    }
    relation = network.edge(evidence, diagnosis, "contradicts", logical_id="semantic:rebuttal")
    network.vertices[relation] = {
        "id": "semantic:rebuttal", "exact_id": relation, "record_type": "graph_edge", "path": "docs/guide.md",
        "private": False, "knowledge_revision": "v1",
    }
    locator = {"start_line": 19, "end_line": 22}
    basis = network.edge(relation, source, "has_basis", locator=locator)
    provenance = network.edge(evidence, source, "from_snapshot", locator=locator)
    base = {"matches": [{"id": evidence, "knowledge_revision": "v1"}], "vector_coverage": {}}

    result = graph_query(network.memory, text="embedded record", seeds=[diagnosis], base=base, scope="docs/")

    assert [(row["exact_id"], row["origin"]) for row in result["seeds"]] == [
        (diagnosis, "named"), (evidence, "base"),
    ]
    source_row = next(row for row in result["candidates"] if row["exact_id"] == source)
    paths = {(path["seed"], tuple(edge["id"] for edge in path["edges"])) for path in source_row["paths"]}
    assert (diagnosis, (relation, provenance)) in paths
    assert (diagnosis, (relation, basis)) in paths
    assert len(paths) == 3
    assert result["scanned"] == 4
    assert len(network.calls) == len(set(network.calls))


def test_typed_adjacent_round_stops_at_the_actual_scan_limit(network):
    seeds = [network.node(f"seed-{index}") for index in range(5)]
    for index, seed in enumerate(seeds):
        for first in range(20):
            middle = network.node(f"middle-{index}-{first}")
            network.edge(seed, middle, "uses")
            for second in range(12):
                network.edge(middle, network.node(f"leaf-{index}-{first}-{second}"), "uses")
    options = {"seeds": seeds, "branches": ("out:uses",)}
    result = graph_query(network.memory, **options)
    assert result["scanned"] == 96
    assert len(result["seeds"]) == 4
    assert len(result["candidates"]) == 12
    assert len(result["observations"]) == 4 + 96
    by_vertex = defaultdict(int)
    for exact, direction, types, limit in network.calls:
        assert direction == "OUT" and types == ("uses",)
        by_vertex[exact] += limit
    assert max(by_vertex.values()) == 12
    assert sum(by_vertex.values()) == 96
    assert any(entry["limit"] == "scanned" and entry["types"] == ["uses"] and entry["seeds"]
               for entry in result["truncation"])
    assert graph_query(network.memory, **options) == result


def test_named_historical_versions_are_available_and_review_requires_explicit_inspection(network):
    old = network.node("old")
    review = network.node("review")
    retired = network.node("retired")
    network.vertices[old]["status"] = "historical"
    network.vertices[review]["status"] = "needs_review"
    network.vertices[retired]["status"] = "retired"
    network.edge(old, review, "uses")
    seeds = [old, review, retired]
    default = graph_query(network.memory, seeds=seeds)
    assert [row["exact_id"] for row in default["seeds"]] == [old]
    assert [row["exact_id"] for row in default["observations"]] == [old]
    history = graph_query(network.memory, seeds=seeds, include_stale=True)
    assert {row["status"] for row in history["observations"] if "status" in row} == {
        "historical", "needs_review", "retired"}


def test_explicit_protected_branches_share_the_adjacency_budget(network):
    old = network.node("old")
    current = network.node("replacement")
    for index in range(25):
        network.edge(network.node(f"counterexample-{index}"), old, "contradicts")
    replacement = network.edge(current, old, "supersedes")
    result = graph_query(network.memory, seeds=[old], branches=("in:contradicts", "in:supersedes"))
    current_row = next(row for row in result["candidates"] if row["exact_id"] == current)
    assert current_row["paths"][0]["edges"][0]["id"] == replacement
    assert sum(limit for exact, _, _, limit in network.calls if exact == old) == 12
