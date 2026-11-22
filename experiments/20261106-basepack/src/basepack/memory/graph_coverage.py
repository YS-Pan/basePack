"""Aggregate current business relationships without returning graph records."""

from .relation_contract import EXACT_ENDPOINT_TABLES
from .store import _record


_GRAPH_METADATA = """
RETURN {
    members: (SELECT id, fn::knowledge_id(id,knowledge_revision) AS exact_id FROM member
        WHERE stale=false AND retired!=true AND knowledge_revision != NONE),
    nodes: (SELECT id, fn::knowledge_id(id,knowledge_revision) AS exact_id FROM node
        WHERE stale=false AND retired!=true AND knowledge_revision != NONE),
    sources: (SELECT version FROM source WHERE deleted!=true AND version != NONE),
    edges: (SELECT id, in.id AS pinned_in_id, out.id AS pinned_out_id
        FROM graph_edge WHERE logical_id != NONE AND state.status = 'current')
};
"""


def _endpoint(pin_id):
    if not isinstance(pin_id, str) or ":" not in pin_id:
        return None
    try:
        pin = _record(pin_id)
    except (KeyError, ValueError, OverflowError):
        return None
    return pin if pin.table in EXACT_ENDPOINT_TABLES else None


def _vertex_counts(records):
    members = sum(record.table == "member" for record in records)
    return {"members": members, "nodes": len(records) - members, "total": len(records)}


def coverage(memory) -> dict:
    """Count fresh knowledge vertices touched by current business relationships."""
    graph, = memory._execute(_GRAPH_METADATA)
    fresh = {_record(row["exact_id"]): _record(row["id"])
             for rows in (graph["members"], graph["nodes"]) for row in rows}
    current = fresh.keys() | {_record(row["id"]) for row in graph["edges"]} | {
        _record(row["version"]) for row in graph["sources"]}
    edges = {"active": len(graph["edges"]), "current_pinned": 0, "non_current_pins": 0,
             "missing_or_unreliable_pins": 0}
    touched = set()
    for row in graph["edges"]:
        endpoints = {_endpoint(row.get(f"pinned_{side}_id")) for side in ("in", "out")}
        if None in endpoints:
            edges["missing_or_unreliable_pins"] += 1
        elif endpoints <= current:
            edges["current_pinned"] += 1
            touched.update(fresh[endpoint] for endpoint in endpoints if endpoint in fresh)
        else:
            edges["non_current_pins"] += 1

    return {"fresh_vertices": _vertex_counts(fresh.values()), "business_relationships": edges,
            "touched_vertices": {**_vertex_counts(touched), "fraction": len(touched) / len(fresh) if fresh else None}}
