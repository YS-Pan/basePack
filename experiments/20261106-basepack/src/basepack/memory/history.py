"""Address retained knowledge versions without substituting a current record."""

from .store import _record, _sql


def _identity(row):
    return _record(row["id"]), row["knowledge_revision"]


def history(memory, record_id):
    target = _record(record_id)
    if target.table not in {"member", "node", "semantic"}:
        raise ValueError("Knowledge requires a member, node, or semantic ID")
    ref = _sql(target)
    current, retained, changes, deliveries, delivery_count = memory._execute(
        f"SELECT * OMIT embedding FROM ONLY {ref}; "
        f"SELECT VALUE record FROM knowledge_version WHERE target={ref}; "
        f"SELECT previous FROM change WHERE target={ref} OR "
        f"previous.members.*.id CONTAINS {ref} OR previous.nodes.*.id CONTAINS {ref} OR previous.edges.*.id CONTAINS {ref}; "
        f"SELECT delivery_id,event,context,items FROM delivery WHERE items.*.id CONTAINS <string>{ref} "
        "ORDER BY event DESC, delivery_id ASC LIMIT 20; "
        f"SELECT count() AS count FROM delivery WHERE items.*.id CONTAINS <string>{ref} GROUP ALL;")
    records = []
    for change in changes:
        previous = change.get("previous")
        if not previous:
            continue
        records.extend([previous] if "id" in previous else
                       [row for key in ("members", "nodes", "edges") for row in previous.get(key, [])])
    # The archive wins over old audit payloads, and current published metadata
    # wins for its own revision. Embeddings are derived and never historical knowledge.
    versions = {}
    for row in [*records, *retained, *([current] if current else [])]:
        if "knowledge_revision" in row and _record(row["id"]) == target:
            versions[_identity(row)] = {key: value for key, value in row.items() if key != "embedding"}
    return {"id": current["id"] if current else record_id,
            "current_knowledge_revision": current["knowledge_revision"] if current else None,
            "versions": list(versions.values()),
            "deliveries": deliveries, "delivery_count": delivery_count[0]["count"] if delivery_count else 0,
            "delivery_limit": 20,
            "coverage": {"complete": False,
                         "note": "Retained versions only; pre-installation gaps may remain."}}


def knowledge(memory, record_id, *, knowledge_revision=None):
    target = _record(record_id)
    if target.table not in {"member", "node", "semantic"}:
        raise ValueError("Knowledge requires a member, node, or semantic ID")
    if knowledge_revision is None:
        row = memory._execute(f"SELECT * OMIT embedding FROM ONLY {_sql(target)};")[0]
        if row is None:
            raise ValueError(f"Knowledge record not found: {record_id}")
        return row
    current, retained = memory._execute(
        f"SELECT * OMIT embedding FROM ONLY {_sql(target)}; "
        f"SELECT VALUE record FROM knowledge_version WHERE target={_sql(target)} "
        f"AND knowledge_revision={_sql(knowledge_revision)} LIMIT 1;")
    if current and current["knowledge_revision"] == knowledge_revision:
        return current
    if retained:
        return retained[0]
    rows = history(memory, record_id)["versions"]
    for row in rows:
        if row["knowledge_revision"] == knowledge_revision:
            return row
    raise ValueError(f"Knowledge version not found: {record_id}@{knowledge_revision}")


def historical_neighbors(memory, current, *, include_stale=False):
    target = _record(current["id"])
    revision = current["knowledge_revision"]
    ref = _sql(target)
    children, retained, current_children, current_edges = memory._execute(
        f"SELECT VALUE record FROM knowledge_version WHERE record.parent={ref}; "
        f"SELECT VALUE record FROM knowledge_version WHERE record.in={ref} OR record.out={ref}; "
        f"SELECT * OMIT embedding FROM member WHERE parent={ref}; "
        f"SELECT * FROM semantic WHERE in={ref} OR out={ref};")
    children = list({_identity(row): row for row in [*children, *current_children]}.values())
    retained = list({_identity(row): row for row in [*retained, *current_edges]}.values())
    unpinned_children = [row for row in children if not row.get("parent_version")]
    unpinned_edges = [row for row in retained if not row.get("endpoint_versions")]
    children = [row for row in children if row.get("parent_version", {}).get("knowledge_revision") == revision]
    edges = [row for row in retained if any(
        _record(endpoint["id"]) == target and endpoint["knowledge_revision"] == revision
        for endpoint in row.get("endpoint_versions", {}).values())]
    if not include_stale:
        children = [row for row in children if not row["stale"] and not row.get("retired")]
        edges = [row for row in edges if not row["stale"] and not row.get("retired")]
    parent = None
    if current.get("parent_version"):
        pinned = current["parent_version"]
        parent = knowledge(memory, pinned["id"], knowledge_revision=pinned["knowledge_revision"])
        if not include_stale and (parent["stale"] or parent.get("retired")):
            parent = None
    return {"record": current, "parent": parent, "children": children, "edges": edges,
            "unpinned_children": unpinned_children, "unpinned_edges": unpinned_edges,
            "coverage": {"complete": False, "note": "Only retained, version-pinned neighbors are returned."}}
