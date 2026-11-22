"""Build graph records in the same native transaction as their published heads."""

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import uuid4

from .content import SourceContent, original_text
from .store import _Record, _digest, _record, _sql


_WITHDRAWN_TARGET_TYPES = ("supersedes", "contradicts")


@dataclass(frozen=True)
class Vertex:
    record: _Record
    private: bool
    paths: tuple[str, ...]


def knowledge_ids(memory, revisions):
    pairs = list(dict.fromkeys(revisions))
    if not pairs:
        return {}
    values = ", ".join(f"fn::knowledge_id({_sql(record)}, {_sql(revision)})" for record, revision in pairs)
    return dict(zip(pairs, map(_record, memory._execute(f"RETURN [{values}];")[0]), strict=True))


def state_ref(record):
    return f"fn::graph_state({_sql(record)})"


def set_state(record, status):
    return f"UPSERT ({state_ref(record)}) SET status={_sql(status)} RETURN NONE;"


def supersede(record):
    state = state_ref(record)
    return (f"IF ({state}).status = 'current' {{ "
            f"UPDATE ({state}) SET status='historical' RETURN NONE; }};")


def edge_sql(edge, start, end, kind, *, locator=None, **attributes):
    content = {"id": edge, "in": start.record, "out": end.record, "type": kind,
               "private": start.private or end.private,
               "scope_paths": sorted(set(start.paths) | set(end.paths))}
    content.update({key: value for key, value in attributes.items() if value is not None})
    if locator is not None:
        content["locator"] = locator
    payload = _sql(content)[:-1] + f",state:{state_ref(edge)}}}"
    return f"INSERT RELATION INTO graph_edge {payload} RETURN NONE;"


def fact(start, end, kind, locator=None):
    position = json.dumps(locator, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    identity = _Record("graph_edge", _digest(_sql([start.record, end.record, kind, position])))
    return (f"IF {_sql(identity)}.id = NONE {{ {set_state(identity, 'current')} "
            f"{edge_sql(identity, start, end, kind, locator=locator)} }};")


def location(row):
    return {key: row[key] for key in ("start_line", "end_line", "locator") if row.get(key) is not None}


class Publication:
    """Resolve immutable dependencies before emitting graph writes."""

    def __init__(self, memory, writes, source_versions, snapshot, knowledge):
        self.memory = memory
        self.source_versions = source_versions
        self.snapshot = snapshot
        self.knowledge = knowledge
        self.writes = {record: row for record, row, _ in writes}
        self.versions = knowledge_ids(memory, ((record, row["knowledge_revision"]) for record, row in self.writes.items()))
        self.exact = {}
        self.relationships = {}
        self.used_basis = set()
        self.required_endpoints = set()

    def vertex(self, target):
        target = _record(target)
        if target not in self.exact:
            if target.table == "source_version":
                row = self.snapshot(target)
            elif target.table in {"knowledge_version", "graph_edge"}:
                row = self.memory._execute(f"SELECT * FROM ONLY {_sql(target)};")[0]
            else:
                raise ValueError(f"An exact graph vertex is required: {_sql(target)}")
            if row is None or target.table == "knowledge_version" and "state" not in row:
                raise ValueError(f"Graph endpoint does not exist: {_sql(target)}")
            self.exact[target] = Vertex(target, row["private"], tuple(
                [row["path"]] if target.table == "source_version" else row["scope_paths"]))
        return self.exact[target]

    def version(self, target, revision=None):
        target = _record(target)
        submitted = self.writes.get(target)
        if revision is None:
            if submitted is None:
                current = self.memory.knowledge(target)
                if current.get("stale") or current.get("retired"):
                    raise ValueError(f"Graph endpoint needs an accepted version: {_sql(target)}")
                revision = current["knowledge_revision"]
            else:
                revision = submitted["knowledge_revision"]
        key = (target, revision)
        if key not in self.versions:
            self.versions.update(knowledge_ids(self.memory, [key]))
        exact = self.versions[key]
        if submitted is None or submitted["knowledge_revision"] != revision:
            return self.vertex(exact)
        if exact not in self.exact:
            row = self.knowledge(target, revision)
            paths = {row["path"]} if "path" in row else set()
            for basis in row["basis"]:
                member = self.knowledge(basis["member"], basis["knowledge_revision"])
                paths.add(member["path"])
            self.exact[exact] = Vertex(exact, row["private"], tuple(sorted(paths)))
        return self.exact[exact]

    def source(self, record, row, previous):
        snapshot = Vertex(record, row["private"], (row["path"],))
        self.exact[record] = snapshot
        output = []
        if previous and _record(previous) != record:
            output.append(supersede(_record(previous)))
        logical = Vertex(row["source"], snapshot.private, snapshot.paths)
        output.extend([set_state(record, "current"),
                       f"IF {_sql(record)}.state = NONE {{ "
                       f"UPDATE {_sql(record)} SET state={state_ref(record)} RETURN NONE; }};",
                       fact(snapshot, logical, "version_of")])
        return output

    def knowledge_facts(self, record, row, previous_revision, *, invalidated=False):
        version = self.version(record, row["knowledge_revision"])
        statements = []
        if previous_revision and not invalidated:
            previous = self.version(record, previous_revision).record
            if previous != version.record:
                statements.append(supersede(previous))
        statements.extend([set_state(version.record, "current"),
                           f"UPDATE {_sql(version.record)} SET private={_sql(version.private)}, "
                           f"scope_paths={_sql(list(version.paths))}, state={state_ref(version.record)} RETURN NONE;",
                           fact(version, Vertex(record, version.private, version.paths), "version_of")])
        if row.get("source_version"):
            statements.append(fact(version, self.vertex(row["source_version"]), "from_snapshot", location(row)))
        if row.get("parent_version"):
            parent = row["parent_version"]
            statements.append(fact(version, self.version(parent["id"], parent["knowledge_revision"]), "part_of"))
        for basis in row["basis"]:
            statements.append(fact(version, self.version(basis["member"], basis["knowledge_revision"]), "has_basis"))
        return statements

    def direct_basis(self, item):
        if "id" in item:
            target = _record(item["id"])
            if target.table == "knowledge_version":
                return self.vertex(target), None
            if target.table not in {"member", "node"}:
                raise ValueError("Relationship basis requires an exact knowledge version or source snapshot")
            return self.version(target, item.get("knowledge_revision")), None
        ref = self.source_versions[item["path"]] if "path" in item else _record(item["source_version"])
        target = self.vertex(ref)
        original = self.snapshot(ref)
        locator = location(item)
        if original["kind"] == "text":
            if "start_line" not in locator or "end_line" not in locator:
                raise ValueError("Text snapshot basis requires inclusive start_line and end_line")
            text = original["text"]
            if _digest(text) != original["revision"]:
                raise ValueError(f"Snapshot revision mismatch for {original['path']}")
            source = SourceContent(original["path"], original["revision"], len(text.encode("utf-8")), 0, text)
            original_text(source, locator["start_line"], locator["end_line"], locator.get("locator"))
        else:
            asset = self.memory.config.memory_dir / original["asset"]
            if sha256(asset.read_bytes()).hexdigest() != original["revision"]:
                raise ValueError(f"Image snapshot revision mismatch for {original['path']}")
            if "start_line" in locator or "end_line" in locator:
                raise ValueError("Image snapshot basis uses an image locator")
            image_locator = locator.get("locator", {})
            if "region" in image_locator:
                region = image_locator["region"]
                if (not isinstance(region, list) or len(region) != 4
                        or any(type(coord) not in (int, float) or not 0 <= coord < float("inf") for coord in region)
                        or region[0] >= region[2] or region[1] >= region[3]):
                    raise ValueError("Image locator region requires ordered nonnegative coordinates")
        return target, locator or None

    def endpoint(self, identity, pin):
        target = _record(identity)
        if pin and _record(pin["id"]) != target:
            raise ValueError(f"Relation endpoint identity mismatch: {identity}")
        revision = pin["knowledge_revision"] if pin else None
        if target.table in {"knowledge_version", "graph_edge", "source_version"}:
            return self.vertex(target)
        if target.table in {"member", "node"}:
            return self.version(target, revision)
        if target.table != "semantic":
            raise ValueError(f"Unsupported relationship endpoint: {identity}")
        if target in self.relationships and revision is None:
            return self.relationships[target]
        row = self.memory.knowledge(target, knowledge_revision=revision)
        if revision is None and (row["stale"] or row["retired"]):
            raise ValueError(f"Graph endpoint needs an accepted version: {identity}")
        return self.vertex(row["exact_id"])

    def business(self, edges, basis, previous, frozen_private):
        remaining = {_record(item["id"], "semantic"): item for item in edges}
        statements = []
        while remaining:
            ready = [(record, item) for record, item in remaining.items() if all(
                item.get("endpoint_versions", {}).get(direction) or _record(item[direction]) not in remaining
                for direction in ("in", "out"))]
            if not ready:
                raise ValueError("Relationship endpoints contain a same-batch dependency cycle")
            for record, item in ready:
                del remaining[record]
                start, end = (self.endpoint(item[direction], item.get("endpoint_versions", {}).get(direction))
                              for direction in ("in", "out"))
                citations = [(self.version(ref["member"], ref["knowledge_revision"]), None)
                             for ref in basis(item.get("evidence", []))]
                citations.extend(self.direct_basis(ref) for ref in item.get("basis", []))
                if not citations:
                    raise ValueError(f"Relationship requires original evidence: {item['id']}")
                self.used_basis.update(vertex.record for vertex, _ in citations)
                self.required_endpoints.add(start.record)
                # These types can explicitly address a withdrawn claim or rule.
                if item["type"] not in _WITHDRAWN_TARGET_TYPES:
                    self.required_endpoints.add(end.record)
                origins = [start, end, *(vertex for vertex, _ in citations)]
                revision = uuid4().hex
                edge = _Record("graph_edge", revision)
                version = Vertex(edge, any(ref.private for ref in origins),
                                 tuple(sorted({path for ref in origins for path in ref.paths})))
                if frozen_private is not None and frozen_private[record] != version.private:
                    raise ValueError(f"Frozen private marker changed for {record}")
                if record in previous:
                    statements.append(supersede(_record(previous[record]["head"])))
                statements.extend([set_state(edge, "current"),
                                   edge_sql(edge, start, end, item["type"], logical_id=record,
                                            knowledge_revision=revision, private=version.private,
                                            scope_paths=list(version.paths), text=item["text"],
                                            conditions=item.get("conditions", ""), label=item.get("label")),
                                   f"UPSERT {_sql(record)} CONTENT {_sql({'head': edge, 'knowledge_revision': revision, 'stale': False, 'retired': False})} RETURN NONE;",
                                   fact(version, Vertex(record, version.private, version.paths), "version_of")])
                statements.extend(fact(version, citation, "has_basis", locator) for citation, locator in citations)
                self.relationships[record] = version
        return statements

    def availability_guards(self):
        """Check citations and endpoints after the transaction's own withdrawals."""
        groups = (("evidence", self.used_basis), ("endpoint", self.required_endpoints))
        return [f"IF NOT (({state_ref(record)}).status IN ['current', 'historical']) "
                f"{{ THROW 'Relationship {role} is unavailable; review its exact version again'; }};"
                for role, records in groups for record in sorted(records, key=_sql)]


def invalidate(memory, roots, status):
    """Invalidate exact versions and the current relations that depend on them."""
    affected = set(roots)
    ready = affected.copy()
    withdrawn_target_types = _sql(list(_WITHDRAWN_TARGET_TYPES))
    while ready:
        refs = _sql(sorted(ready, key=_sql))
        incoming, linked = memory._execute(
            f"SELECT VALUE in FROM graph_edge WHERE out IN {refs} AND type IN ['has_basis', 'from_snapshot']; "
            "SELECT VALUE id FROM graph_edge WHERE logical_id != NONE "
            f"AND (in IN {refs} OR (out IN {refs} AND NOT (type IN {withdrawn_target_types})));")
        ready = {_record(value) for value in [*incoming, *linked]} - affected
        affected.update(ready)
    if not affected:
        return []
    refs = _sql(sorted(affected, key=_sql))
    states = ", ".join(state_ref(ref) for ref in sorted(affected, key=_sql))
    retired = ", retired=true" if status == "retired" else ""
    targets = f"(SELECT VALUE target FROM knowledge_version WHERE id IN {refs})"
    return [f"UPDATE [{states}] SET status={_sql(status)} WHERE status != 'retired' RETURN NONE;",
            f"UPDATE semantic SET stale=true{retired} WHERE head IN {refs} RETURN NONE;",
            f"UPDATE member, node SET stale=true WHERE id IN {targets} "
            f"AND fn::knowledge_id(id, knowledge_revision) IN {refs} RETURN NONE;"]
