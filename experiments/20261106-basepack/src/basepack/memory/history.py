"""Address retained knowledge versions without substituting a current record."""

from .store import _record, _sql


def _identity(row):
    return _record(row["id"]), row["knowledge_revision"]


def _effective_privacy(record, version):
    """Use the exact version's visibility while retaining its original payload."""
    effective = dict(record)
    if type(version.get("private")) is bool:
        effective["private"] = version["private"]
    if version.get("privacy_unknown"):
        effective["privacy_unknown"] = True
    return effective


def _semantic_versions(memory, edges):
    if not edges:
        return []
    exact_ids = _sql([_record(edge["id"]) for edge in edges])
    facts = memory._execute(
        "SELECT in, out, locator, out.target AS target, out.knowledge_revision AS knowledge_revision, "
        "out.record.source_version AS source_version, out.record.start_line AS start_line, "
        "out.record.end_line AS end_line, out.record.locator AS member_locator, "
        "out.record.input_revision AS input_revision, out.record.description_revision AS description_revision "
        f"FROM graph_edge WHERE in IN {exact_ids} AND type='has_basis';")[0]
    citations = {}
    for fact in facts:
        citations.setdefault(fact["in"], []).append(fact)
    rows = []
    for edge in edges:
        row = {key: edge[key] for key in ("text", "conditions", "private", "scope_paths", "knowledge_revision", "type")}
        row.update(id=edge["logical_id"], exact_id=edge["id"], kind=edge["type"], basis=[], direct_basis=[],
                   stale=edge["status"] in {"needs_review", "retired"}, retired=edge["status"] == "retired")
        if "label" in edge:
            row["label"] = edge["label"]
        endpoints = row["endpoint_versions"] = {}
        for direction in ("in", "out"):
            logical = edge.get(direction + "_logical")
            revision = edge.get(direction + "_revision")
            row[direction] = logical or edge[direction]
            if logical and revision:
                endpoints[direction] = {"id": logical, "knowledge_revision": revision}
        for fact in citations.get(edge["id"], []):
            if fact.get("target") and _record(fact["target"]).table == "member":
                entry = {key: fact.get(key) for key in ("knowledge_revision", "source_version",
                                                       "start_line", "end_line", "input_revision",
                                                       "description_revision")}
                entry.update(member=fact["target"], locator=fact.get("member_locator"))
                row["basis"].append(entry)
            elif fact.get("target"):
                row["direct_basis"].append({"id": fact["target"], "knowledge_revision": fact["knowledge_revision"]})
            else:
                row["direct_basis"].append({"source_version": fact["out"], **fact.get("locator", {})})
        rows.append(row)
    return rows


_BUSINESS_FIELDS = ("*, state.status AS status, (in.target ?? in.logical_id) AS in_logical, "
                    "(out.target ?? out.logical_id) AS out_logical, in.knowledge_revision AS in_revision, "
                    "out.knowledge_revision AS out_revision")


def semantic_rows(memory, logical_ids=None, *, members=None):
    """Read current logical relation heads through the native graph versions."""
    where = "" if logical_ids is None else f" WHERE id IN {_sql([_record(value) for value in logical_ids])}"
    filter_scope = ""
    if members is not None:
        refs = _sql([_record(value) for value in members])
        filter_scope = (f" AND (in.target IN {refs} OR out.target IN {refs} OR "
                        f"id IN (SELECT VALUE in FROM graph_edge WHERE type='has_basis' AND out.target IN {refs}))")
    rows = memory._execute(
        f"SELECT {_BUSINESS_FIELDS} FROM graph_edge WHERE "
        f"id IN (SELECT VALUE head FROM semantic{where}){filter_scope};")[0]
    return _semantic_versions(memory, rows)


def _legacy_semantic_query(target, revision=None):
    match = f" AND knowledge_revision={_sql(revision)}" if revision is not None else ""
    return ("SELECT record, legacy_reason, private, privacy_unknown FROM knowledge_version "
            f"WHERE target={_sql(target)} AND legacy_history_only=true{match}; ")


def _legacy_semantic(row):
    original = row["record"]
    privacy = {} if type(original.get("private")) is bool else {"private": True, "privacy_unknown": True}
    effective = _effective_privacy({**original, **privacy}, row)
    return {**effective, "legacy_history_only": True, "legacy_reason": row["legacy_reason"]}


def _semantic_knowledge(memory, target, revision):
    if revision is None:
        rows = semantic_rows(memory, [target])
        if rows:
            return rows[0]
        head = memory._execute(f"SELECT * FROM ONLY {_sql(target)};")[0]
        if head and head.get("legacy_history_only") and not head.get("head"):
            archive = memory._execute(_legacy_semantic_query(target, head["knowledge_revision"]))[0]
            if archive:
                return {**_legacy_semantic(archive[0]), "stale": head["stale"], "retired": head["retired"]}
    else:
        edges = memory._execute(
            f"SELECT {_BUSINESS_FIELDS} FROM graph_edge WHERE logical_id={_sql(target)} "
            f"AND knowledge_revision={_sql(revision)};")[0]
        if edges:
            return _semantic_versions(memory, edges)[0]
        archive = memory._execute(_legacy_semantic_query(target, revision))[0]
        if archive:
            return _legacy_semantic(archive[0])
    raise ValueError(f"Relationship version not found: {target.table}:{target.key}@{revision}")


def history(memory, record_id):
    target = _record(record_id)
    if target.table not in {"member", "node", "semantic"}:
        raise ValueError("Knowledge requires a member, node, or semantic ID")
    ref = _sql(target)
    archive_query = (_legacy_semantic_query(target) if target.table == "semantic" else
                     f"SELECT record,private,privacy_unknown FROM knowledge_version WHERE target={ref}; ")
    current, retained, changes, deliveries, legacy_deliveries, delivery_count = memory._execute(
        f"SELECT * OMIT embedding FROM ONLY {ref}; " + archive_query +
        f"SELECT previous FROM change WHERE target={ref} OR "
        f"previous.members.*.id CONTAINS {ref} OR previous.nodes.*.id CONTAINS {ref} OR previous.edges.*.id CONTAINS {ref}; "
        f"SELECT delivery_id,j,context,items FROM delivery WHERE j >= 1 AND items.*.id CONTAINS <string>{ref} "
        "ORDER BY j DESC LIMIT 20; "
        f"SELECT delivery_id,legacy_event,legacy_context,items FROM delivery WHERE legacy=true AND items.*.id CONTAINS <string>{ref} "
        "ORDER BY legacy_event DESC LIMIT 20; "
        f"SELECT count() AS count FROM delivery WHERE items.*.id CONTAINS <string>{ref} GROUP ALL;")
    if target.table == "semantic":
        graph = memory._execute(
            f"SELECT {_BUSINESS_FIELDS} FROM graph_edge WHERE logical_id={ref};")[0]
        native = _semantic_versions(memory, graph)
        archived = [_legacy_semantic(row) for row in retained]
        retained = [*native, *archived]
        if current and current.get("legacy_history_only") and not current.get("head"):
            head = current
            current = next((row for row in archived if row["knowledge_revision"] == head["knowledge_revision"]), None)
            if current:
                current = {**current, "stale": head["stale"], "retired": head["retired"]}
        elif current:
            head = current.get("head")
            current = next((row for row in native if row["exact_id"] == head), None)
        changes = []
    else:
        current_version = next((row for row in retained if current and _identity(row["record"]) == _identity(current)),
                               None)
        if current_version:
            current = _effective_privacy(current, current_version)
        retained = [_effective_privacy(row["record"], row) for row in retained]
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
            "deliveries": (deliveries + legacy_deliveries)[:20], "legacy_order": "event_only_ties_unknown",
            "delivery_count": delivery_count[0]["count"] if delivery_count else 0,
            "delivery_limit": 20,
            "coverage": {"complete": False,
                         "note": "Retained versions only; pre-installation gaps may remain."}}


def knowledge(memory, record_id, *, knowledge_revision=None):
    target = _record(record_id)
    if target.table == "semantic":
        return _semantic_knowledge(memory, target, knowledge_revision)
    if target.table in {"knowledge_version", "graph_edge", "source_version"}:
        row = memory._execute(f"SELECT * FROM ONLY {_sql(target)};")[0]
        if row is None or knowledge_revision is not None and row.get("knowledge_revision") != knowledge_revision:
            raise ValueError(f"Exact graph record not found: {target.table}:{target.key}")
        if target.table == "knowledge_version":
            logical = _record(row["target"])
            if logical.table == "semantic":
                if row.get("legacy_history_only"):
                    return _legacy_semantic(row)
                return _semantic_knowledge(memory, logical, row["knowledge_revision"])
            return {**_effective_privacy(row["record"], row), "exact_id": row["id"]}
        return row
    if target.table not in {"member", "node"}:
        raise ValueError("Knowledge requires a logical knowledge ID or an exact graph record ID")
    if knowledge_revision is None:
        row = memory._execute(f"SELECT * OMIT embedding FROM ONLY {_sql(target)};")[0]
        if row is None:
            raise ValueError(f"Knowledge record not found: {record_id}")
        return row
    current, retained = memory._execute(
        f"SELECT * OMIT embedding FROM ONLY {_sql(target)}; "
        f"SELECT record,private,privacy_unknown FROM knowledge_version WHERE target={_sql(target)} "
        f"AND knowledge_revision={_sql(knowledge_revision)} LIMIT 1;")
    if current and current["knowledge_revision"] == knowledge_revision:
        return _effective_privacy(current, retained[0]) if retained else current
    if retained:
        return _effective_privacy(retained[0]["record"], retained[0])
    rows = history(memory, record_id)["versions"]
    for row in rows:
        if row["knowledge_revision"] == knowledge_revision:
            return row
    raise ValueError(f"Knowledge version not found: {record_id}@{knowledge_revision}")
