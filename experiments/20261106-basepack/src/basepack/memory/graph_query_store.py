"""Read exact vertices and the single published graph."""

from .dialogue_query import graph_dialogue_test, legacy_path_tests, require_original_path
from .relation_contract import SYSTEM_EDGE_TYPES
from .store import _read_original, _record, _sql


_LOGICAL_TABLES = {"member", "node", "semantic", "source"}
_EXACT_TABLES = {"knowledge_version", "source_version", "graph_edge"}
_EDGE_FIELDS = ("id, in, out, type, private, logical_id, knowledge_revision, "
                "conditions, text, label, locator, state.status AS status")
_KNOWLEDGE_FIELDS = ("kind", "title", "text", "path", "source_version", "start_line", "end_line",
                     "locator", "claim_type", "conditions", "stale", "retired", "codex_thread_id")
_HISTORICAL_EVIDENCE = "['part_of','from_snapshot','has_basis']"
_SYSTEM_EDGES = _sql(sorted(SYSTEM_EDGE_TYPES))


def resolve_seed(memory, identifier, knowledge_revision=None):
    """Resolve a logical seed to an observed exact version, or verify an exact seed."""
    target = _record(identifier)
    ref = _sql(target)
    if target.table in {"member", "node"}:
        if knowledge_revision is None:
            ref = ("(SELECT VALUE fn::knowledge_id(id, knowledge_revision) "
                   f"FROM ONLY {ref} WHERE knowledge_revision != NONE)")
        else:
            ref = f"(fn::knowledge_id({ref}, {_sql(knowledge_revision)}))"
    elif target.table == "semantic":
        if knowledge_revision is None:
            return memory._execute(f"SELECT VALUE head FROM ONLY {ref};")[0]
        rows = memory._execute("SELECT VALUE id FROM graph_edge "
                               f"WHERE logical_id={ref} AND knowledge_revision={_sql(knowledge_revision)} LIMIT 1;")[0]
        return rows[0] if rows else None
    elif target.table == "source":
        if knowledge_revision is None:
            return memory._execute(f"SELECT VALUE version FROM ONLY {ref};")[0]
        rows = memory._execute("SELECT VALUE id FROM source_version "
                               f"WHERE source={ref} AND revision={_sql(knowledge_revision)} LIMIT 2;")[0]
        if len(rows) > 1:
            raise ValueError(f"Source revision has multiple snapshots, specify a source_version ID: {identifier}")
        return rows[0] if rows else None
    elif target.table not in _EXACT_TABLES:
        return None
    revision = ""
    if target.table in _EXACT_TABLES and knowledge_revision is not None:
        field = "revision" if target.table == "source_version" else "knowledge_revision"
        revision = f" WHERE {field}={_sql(knowledge_revision)}"
    return memory._execute(f"SELECT VALUE id FROM ONLY {ref}{revision};")[0]


def _scope_test(paths, scope):
    return f"array::len({paths}[WHERE string::starts_with($this, {_sql(scope)})])>0"


def _within_scope(prefix, scope):
    path = f"({prefix}path ?? {prefix}record.path)"
    direct = f"string::starts_with(({path} ?? ''), {_sql(scope)})"
    provenance = _scope_test(f"{prefix}scope_paths", scope)
    return f"({direct} OR ({path}=NONE AND {provenance}))"


def _visibility(memory, prefix, scope, allow_private, *, path=False):
    tests = [] if allow_private else [f"{prefix}private=false"]
    if scope:
        if path:
            tests.append(f"string::starts_with(({prefix}path ?? ''), {_sql(scope)})")
        else:
            tests.append(_within_scope(prefix, scope))
    tests.extend(_protected_visibility(memory, prefix, scope, allow_private))
    return tests


def _protected_visibility(memory, prefix, scope, allow_private):
    return [graph_dialogue_test(memory, prefix.rstrip("."), scope, allow_private),
            *legacy_path_tests(memory, f"({prefix}path ?? {prefix}record.path)")]


def _present(row):
    return {key: value for key, value in row.items() if value is not None}


def require_dialogue_visibility(memory, row):
    """Protect direct knowledge/history lookups, which normally include private records."""
    require_original_path(memory, row.get("path"))
    if row.get("codex_thread_id") is not None:
        exact = row.get("exact_id") or resolve_seed(memory, row["id"], row["knowledge_revision"])
        if exact is None or get_vertex(memory, exact, scope="", allow_private=True) is None:
            raise ValueError("Dialogue node unavailable within the requested scope and visibility")
    exact = row.get("exact_id", row["id"])
    if _record(exact).table == "graph_edge" and get_vertex(memory, exact, scope="", allow_private=True) is None:
        raise ValueError("Graph edge unavailable within the requested scope and visibility")


def get_vertex(memory, exact, *, scope, allow_private):
    """Return visible candidate metadata without retrieving the original snapshot."""
    target = _record(exact)
    if target.table in _LOGICAL_TABLES:
        # The identity is visible through an accessible exact version link.
        links = adjacent(memory, exact, direction="IN", types=("version_of",),
                         scope=scope, allow_private=allow_private, include_stale=False, limit=1)
        return {"id": links[0]["out"], "exact_id": links[0]["out"], "record_type": target.table,
                "identity": True, "private": links[0]["private"]} if links else None
    if target.table not in _EXACT_TABLES:
        return None
    tests = _visibility(memory, "", scope, allow_private, path=target.table == "source_version")
    if target.table == "knowledge_version":
        tests.append("state != NONE")
    if target.table == "graph_edge":
        tests.extend(_edge_endpoint_tests(memory, scope, allow_private))
    where = " WHERE " + " AND ".join(tests) if tests else ""
    if target.table == "knowledge_version":
        fields = ("id, target, knowledge_revision, private, state.status AS status, "
                  + ", ".join(f"record.{field} AS {field}" for field in _KNOWLEDGE_FIELDS))
    elif target.table == "source_version":
        fields = "id, source, path, kind, revision, private, state.status AS status"
    else:
        fields = _EDGE_FIELDS
    row = memory._execute(f"SELECT {fields} FROM ONLY {_sql(target)}{where};")[0]
    if row is None:
        return None
    item = _present(row)
    item["exact_id"] = item["id"]
    if target.table == "knowledge_version":
        item["id"] = item.pop("target")
        item["record_type"] = _record(item["id"]).table
    elif target.table == "source_version":
        item["record_type"] = "source_version"
        item["source_version"] = item["id"]
    elif "logical_id" in item:
        item["id"] = item["logical_id"]
        item["record_type"] = "semantic"
    else:
        item["record_type"] = "graph_edge"
    return item


def _endpoint_filter(memory, field, scope, allow_private):
    tests = [f"{field}.id != NONE", *_visibility(memory, f"{field}.", scope, allow_private)]
    return " AND ".join(tests)


def _edge_endpoint_tests(memory, scope, allow_private):
    identity = " AND ".join(["type='version_of'", "out.id!=NONE",
                             *_protected_visibility(memory, "out.", scope, allow_private)])
    usable_basis = " AND ".join(_protected_visibility(memory, "out.", scope, allow_private))
    basis_gap = ("SELECT VALUE id FROM graph_edge WHERE in=$parent.id AND type='has_basis' "
                 f"AND !({usable_basis}) LIMIT 1")
    return [f"({_endpoint_filter(memory, 'in', scope, allow_private)})",
            f"(({identity}) OR {_endpoint_filter(memory, 'out', scope, allow_private)})",
            f"array::len(({basis_gap}))=0"]


def visible_edge_records(memory, rows, *, scope="", allow_private=True):
    """Filter already selected relationship metadata using native edge visibility."""
    records = {_record(row["exact_id"]) for row in rows if row.get("exact_id")}
    if not records:
        return rows
    tests = " AND ".join(_edge_endpoint_tests(memory, scope, allow_private))
    rows_by_id, = memory._execute(f"SELECT VALUE id FROM {_sql(sorted(records, key=_sql))} WHERE {tests};")
    allowed = {_record(value) for value in rows_by_id}
    return [row for row in rows if not row.get("exact_id") or _record(row["exact_id"]) in allowed]


def adjacent(memory, exact, *, direction, types, scope, allow_private, include_stale, limit,
             include_historical=False, conditions=None):
    """Filter exact incident edges in SurrealDB before applying the traversal limit."""
    if direction not in {"IN", "OUT"}:
        raise ValueError("Graph direction must be IN or OUT")
    origin, neighbor = ("in", "out") if direction == "OUT" else ("out", "in")
    ref = _sql(_record(exact))
    tests = [f"{origin}={ref}"]
    if len(types) == 1:
        tests.append(f"type={_sql(types[0])}")
    elif types:
        tests.append(f"type IN {_sql(list(types))}")
    for key, expected in (conditions or {}).items():
        field = f"conditions[{_sql(key)}]"
        tests.append(f"({field}=NONE OR {field}={_sql(expected)})")
    tests.extend(_visibility(memory, "", scope, allow_private))
    tests.extend(_edge_endpoint_tests(memory, scope, allow_private))
    if not include_stale:
        historical = ("true" if include_historical else
                      f"(type='version_of' OR (in={ref} AND type IN {_HISTORICAL_EVIDENCE}))")
        tests.append(f"(state.status='current' OR (state.status='historical' AND {historical}))")
        # Fixed facts retain their IDs when an endpoint stops being a current head.
        # Incoming structural/evidence searches normally find current users of the anchor.
        sources = "in.state.status IN ['current','historical']"
        if direction == "IN" and not include_historical:
            sources = "(in.state.status='current' OR (type='version_of' AND in.state.status='historical'))"
        endpoints = f"({sources} AND (type='version_of' OR out.state.status IN ['current','historical']))"
        tests.append(f"(!(type IN {_SYSTEM_EDGES}) OR {endpoints})")
    bounded = f" ORDER BY type ASC, id ASC LIMIT {int(limit)}" if limit is not None else ""
    rows = memory._execute(f"SELECT {_EDGE_FIELDS}, {neighbor} AS neighbor FROM graph_edge "
                           f"WHERE {' AND '.join(tests)}{bounded};")[0]
    return [_present(row) for row in rows]


def _entry_refs(entry):
    if entry is None:
        return []
    identifier = entry.get("member") or entry.get("id")
    refs = [(_record(identifier), entry.get("knowledge_revision"))] if identifier else []
    if entry.get("source_version"):
        refs.append((_record(entry["source_version"], "source_version"), None))
    return refs


def _visible_references(memory, refs, scope, allow_private):
    queries = {}
    visible = set()
    for target, revision in dict.fromkeys(refs):
        ref = _sql(target)
        address = []
        tests = _visibility(memory, "", scope, allow_private, path=target.table == "source_version")
        # Old unrestricted projections include unpinned or no-longer retained
        # file provenance. Keep these links unless a retained record is hidden.
        fresh_dialogue = target.table == "node" and str(target.key).startswith("codex-")
        require_match = bool(scope) or not allow_private or fresh_dialogue
        if target.table in {"member", "node"} and revision is not None:
            selection = f"ONLY (fn::knowledge_id({ref}, {_sql(revision)}))"
        elif target.table == "semantic":
            if revision is None:
                selection = f"ONLY ({ref}.head)"
            else:
                selection = "graph_edge"
                address.extend([f"logical_id={ref}", f"knowledge_revision={_sql(revision)}"])
            tests.extend(_edge_endpoint_tests(memory, scope, allow_private))
        elif target.table in _EXACT_TABLES or target.table in {"member", "node"} and not require_match:
            selection = f"ONLY {ref}"
            if revision is not None:
                address.append(f"knowledge_revision={_sql(revision)}")
            if target.table == "graph_edge":
                tests.extend(_edge_endpoint_tests(memory, scope, allow_private))
        else:
            if not require_match:
                visible.add((target, revision))
            continue
        policy = " AND ".join(tests)
        address.append(f"({policy})" if require_match else f"!({policy})")
        queries[target, revision] = f"SELECT VALUE id FROM {selection} WHERE {' AND '.join(address)};", require_match
    if not queries:
        return visible
    rows = memory._execute(" ".join(query for query, _ in queries.values()))
    visible.update(ref for (ref, (_, require_match)), result in zip(queries.items(), rows, strict=True)
                   if bool(result) == require_match)
    return visible


def filter_record_details(memory, row, *, scope, allow_private):
    """Filter the nested provenance returned by compatibility projections."""
    citations = {field: [(entry, _entry_refs(entry)) for entry in (row[field] or ())]
                 for field in ("basis", "direct_basis") if field in row}
    endpoints = {}
    pins = row.get("endpoint_versions") or {}
    for side in ("in", "out"):
        if side in pins:
            endpoints[side] = _entry_refs(pins[side])
        elif side in row and not (side == "out" and row.get("type") == "version_of"):
            endpoints[side] = [(_record(row[side]), None)]
    parent = _entry_refs(row.get("parent_version", {}))
    original = _entry_refs({key: row[key] for key in ("source_version",) if key in row})
    refs = [ref for entries in citations.values() for _, keys in entries for ref in keys]
    refs.extend(ref for keys in endpoints.values() for ref in keys)
    visible = _visible_references(memory, [*refs, *parent, *original], scope, allow_private)

    result = dict(row)
    if scope and "scope_paths" in result:
        result["scope_paths"] = [path for path in result["scope_paths"] if path.startswith(scope)]
    unrestricted = not scope and allow_private
    for field, entries in citations.items():
        result[field] = [entry for entry, keys in entries if (keys or unrestricted) and visible.issuperset(keys)]
    allowed_sides = {side for side, keys in endpoints.items() if keys and visible.issuperset(keys)}
    if "endpoint_versions" in row:
        result["endpoint_versions"] = {side: pin for side, pin in pins.items() if side in allowed_sides}
    for side in endpoints.keys() - allowed_sides:
        result.pop(side, None)
    if "parent" in result and not ((parent or unrestricted) and visible.issuperset(parent)):
        result.pop("parent", None)
        result.pop("parent_version", None)
    if original and not visible.issuperset(original):
        for field in ("source", "source_version", "start_line", "end_line", "locator"):
            result.pop(field, None)
    return result


def _retained_records(memory, ids):
    if not ids:
        return {}
    ref = _sql(list(dict.fromkeys(_record(value) for value in ids)))
    rows = memory._execute(f"SELECT id, record FROM {ref};")[0]
    return {row["id"]: {**row["record"], "exact_id": row["id"]} for row in rows}


def _unpinned(memory, vertex, scope, allow_private):
    if vertex["record_type"] not in {"member", "node"}:
        return [], []
    ref = _sql(_record(vertex["id"]))
    visible = _visibility(memory, "record.", scope, allow_private, path=True)
    suffix = " AND " + " AND ".join(visible) if visible else ""
    return memory._execute(
        f"SELECT VALUE record FROM knowledge_version WHERE record.parent={ref} AND record.parent_version=NONE{suffix}; "
        f"SELECT VALUE record FROM knowledge_version WHERE (record.in={ref} OR record.out={ref}) "
        f"AND record.endpoint_versions=NONE AND legacy_history_only != true{suffix};")


def neighbors(memory, record_id, *, include_stale, knowledge_revision, direction, types, scope, allow_private,
              conditions):
    """Return native adjacency and the established logical summary fields."""
    from .history import knowledge
    from .query import normalize_scope

    scope = normalize_scope(scope)
    direction = direction.upper()
    if direction not in {"IN", "OUT", "BOTH"}:
        raise ValueError("Graph direction must be IN, OUT or BOTH")
    types = tuple(types)
    explicit = knowledge_revision is not None or _record(record_id).table in _EXACT_TABLES
    exact = resolve_seed(memory, record_id, knowledge_revision)
    vertex = get_vertex(memory, exact, scope=scope, allow_private=allow_private) if exact else None
    result = {"record": None, "parent": None, "children": [], "edges": [], "adjacency": []}
    if vertex is None:
        if explicit:
            result.update(unpinned_children=[], unpinned_edges=[])
        if explicit and exact is None and allow_private and not scope and _record(record_id).table in {"member", "node", "semantic"}:
            current = knowledge(memory, record_id, knowledge_revision=knowledge_revision)
            require_dialogue_visibility(memory, current)
            children, edges = _unpinned(memory, {**current, "record_type": _record(current["id"]).table}, scope, allow_private)
            result.update(record=memory.access_hints([current])[0], unpinned_children=children, unpinned_edges=edges)
        return result

    if vertex["record_type"] in {"member", "node", "semantic"}:
        current = knowledge(memory, vertex["id"], knowledge_revision=vertex["knowledge_revision"])
        result["record"] = memory.access_hints([{**current, "exact_id": exact}])[0]
    else:
        result["record"] = vertex

    directions = ("IN", "OUT") if direction == "BOTH" else (direction,)
    incident = {}
    for step in directions:
        for edge in adjacent(memory, exact, direction=step, types=types, scope=scope, allow_private=allow_private,
                             include_stale=include_stale, limit=None, include_historical=explicit,
                             conditions=conditions):
            incident[edge["id"]] = edge
    edges = [incident[key] for key in sorted(incident)]
    result["adjacency"] = edges
    hierarchy = [edge for edge in edges if edge["type"] == "part_of"]
    records = _retained_records(memory, [edge["neighbor"] for edge in hierarchy])
    parents = [records[edge["neighbor"]] for edge in hierarchy if edge["in"] == exact]
    if parents:
        result["parent"] = memory.access_hints(parents)[0]
    result["children"] = memory.access_hints([records[edge["neighbor"]] for edge in hierarchy if edge["out"] == exact])
    business = [edge for edge in edges if "logical_id" in edge]
    if business and not explicit:
        refs = _sql(list(dict.fromkeys(_record(edge["logical_id"]) for edge in business)))
        heads = set(memory._execute(f"SELECT VALUE head FROM {refs};")[0])
        business = [edge for edge in business if edge["id"] in heads]
    result["edges"] = memory.access_hints([
        {**knowledge(memory, edge["logical_id"], knowledge_revision=edge["knowledge_revision"]), "exact_id": edge["id"]}
        for edge in business])
    if explicit:
        children, edges = _unpinned(memory, vertex, scope, allow_private)
        result.update(unpinned_children=memory.access_hints(children), unpinned_edges=memory.access_hints(edges),
                      coverage={"complete": False, "note": "Only retained, version-pinned neighbors are traversable."})
    visibility = {"scope": scope, "allow_private": allow_private}
    for field in ("record", "parent"):
        if result[field] is not None:
            result[field] = filter_record_details(memory, result[field], **visibility)
    for field in ("children", "edges", "unpinned_children", "unpinned_edges"):
        if field in result:
            result[field] = [filter_record_details(memory, row, **visibility) for row in result[field]]
    return result


def basis_dependents(memory, observed, *, scope, allow_private):
    """Reverse the same native has_basis edges used by ordinary adjacency."""
    from .history import knowledge
    from .query import normalize_scope

    scope = normalize_scope(scope)
    restricted = bool(scope) or not allow_private

    requested = dict.fromkeys((member, revision) for member, revision, _ in observed)
    refs = ", ".join(f"fn::knowledge_id({_sql(member)}, {_sql(revision)})" for member, revision in requested)
    anchor_tests = _visibility(memory, "", scope, allow_private)
    anchor_tests.extend(_visibility(memory, "record.source_version.", scope, allow_private, path=True))
    if restricted:
        anchor_tests.append("record.source_version.id!=NONE")
    anchor_filter = " WHERE " + " AND ".join(anchor_tests) if anchor_tests else ""
    rows = memory._execute("SELECT id, target, knowledge_revision, record.source_version AS source_version "
                           f"FROM [{refs}]{anchor_filter};")[0]
    anchors = {}
    for row in rows:
        if "source_version" in row:
            key = (_record(row["target"]), row["knowledge_revision"], _record(row["source_version"], "source_version"))
            if key in observed:
                anchors[row["id"]] = key
    if not anchors:
        return []
    cited = _sql([_record(exact) for exact in anchors])
    edge_tests = [*_visibility(memory, "", scope, allow_private), *_edge_endpoint_tests(memory, scope, allow_private)]
    edge_filter = " AND " + " AND ".join(edge_tests)
    rows = memory._execute(
        "SELECT id, in, out, in.target AS target, in.logical_id AS logical_id, "
        "in.knowledge_revision AS knowledge_revision FROM graph_edge "
        f"WHERE out IN {cited} AND type='has_basis' AND state.status='current' "
        "AND ((in.target.knowledge_revision=in.knowledge_revision AND in.target.stale=false AND in.target.retired!=true) "
        f"OR (in.logical_id.head=in AND in.logical_id.stale=false AND in.logical_id.retired!=true)){edge_filter};")[0]
    dependents = {}
    for row in rows:
        dependents.setdefault(row["in"], []).append(row)

    fields = ("id", "kind", "title", "path", "knowledge_revision", "source_version", "private", "basis")
    matches = []
    for exact, edges in dependents.items():
        first = edges[0]
        if first.get("logical_id") and get_vertex(
                memory, exact, scope=scope, allow_private=allow_private) is None:
            continue
        identifier = first.get("logical_id") or first["target"]
        record = knowledge(memory, identifier, knowledge_revision=first["knowledge_revision"])
        summary = {field: record[field] for field in fields if field in record and record[field] is not None}
        summary = filter_record_details(memory, summary, scope=scope, allow_private=allow_private)
        summary.update(record_type=_record(identifier).table, exact_id=exact)
        cited_anchors = {anchors[edge["out"]] for edge in edges}
        matches.append({"record": summary, "matched_anchors": [a for key, a in observed.items() if key in cited_anchors],
                        "basis_edges": sorted(edge["id"] for edge in edges)})
    order = {"member": 0, "node": 1, "semantic": 2}
    return sorted(matches, key=lambda hit: (order[hit["record"]["record_type"]], hit["record"]["id"]))


def read_source_version(memory, identifier, *, start_line=None, end_line=None, locator=None,
                        scope="", allow_private=False):
    """Read a retained original through the exact snapshot named by a graph edge."""
    from .query import normalize_scope

    target = _record(identifier, "source_version")
    if target.table != "source_version":
        raise ValueError("read-source requires a source_version ID")
    visibility = _visibility(memory, "", normalize_scope(scope), allow_private, path=True)
    where = " WHERE " + " AND ".join(visibility) if visibility else ""
    snapshot = memory._execute(f"SELECT * FROM ONLY {_sql(target)}{where};")[0]
    if snapshot is None:
        raise ValueError(f"Readable source snapshot not found: {identifier}")
    if snapshot["kind"] == "text" and (start_line is None or end_line is None):
        raise ValueError("Reading an explicit source version requires start_line and end_line")
    return {"original": _read_original(memory.config, snapshot, snapshot["path"], snapshot["id"],
                                       start_line, end_line, locator)}
