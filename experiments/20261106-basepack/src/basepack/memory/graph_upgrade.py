"""Convert a stopped, isolated schema 3 restore to the versioned graph."""

from collections import defaultdict
from hashlib import file_digest
import json
from pathlib import Path, PurePosixPath
import re

from .content import SourceContent, original_text
from .graph_write import Vertex, _WITHDRAWN_TARGET_TYPES, edge_sql, fact, location, set_state, state_ref
from .privacy import source_private
from .relation_contract import validate_edge
from .store import Memory, _Record, _digest, _record, _sql


class _Schema3Publication(Memory):
    def _project_guard(self):
        project = _sql(self.connection["project_id"])
        return (f"IF meta:project.project_id != {project} OR meta:project.member_identity_version != 2 "
                "OR meta:project.memory_schema_version != 3 "
                "{ THROW 'Expected the restored project at schema 3'; };")


def _identity(row):
    return row["id"], row["knowledge_revision"]


def _status(row, current):
    if row.get("retired"):
        return "retired"
    if row.get("stale"):
        return "needs_review"
    return "current" if current else "historical"


def _versions(memory):
    """Use native archive rows, then current heads and actual audit preimages."""
    members, nodes, relations, retained, changes = memory._execute(
        "SELECT * OMIT embedding FROM member; SELECT * FROM node; SELECT * FROM semantic; "
        "SELECT * FROM knowledge_version; SELECT id,operation,previous FROM change WHERE previous != NONE;")
    heads = {row["id"]: row for row in [*members, *nodes, *relations]}
    rows = {_identity(item["record"]): item["record"] for item in retained}
    identities = {_identity(item["record"]): _record(item["id"]) for item in retained}
    expressions = {}
    corrections = set()
    for change in changes:
        previous = change["previous"]
        ref = _sql(_record(change["id"])) + ".previous"
        if "id" in previous:
            records = [(previous, ref)]
        else:
            records = [(row, f"{ref}.{field}[{index}]") for field in ("members", "nodes", "edges")
                       for index, row in enumerate(previous.get(field, []))]
        for row, expression in records:
            if not row.get("knowledge_revision"):
                continue
            identity = _identity(row)
            if change.get("operation") == "correction":
                corrections.add(identity)
            if identity not in rows:
                rows[identity], expressions[identity] = row, expression
    for row in heads.values():
        if not row.get("knowledge_revision"):
            continue
        identity = _identity(row)
        rows[identity] = row
        if identity not in identities:
            # Membership, feedback and deliveries still use the original logical key.
            expressions[identity] = f"(SELECT * FROM ONLY {_sql(_record(row['id']))})"
    for identity in rows.keys() - identities.keys():
        identities[identity] = _Record("knowledge_version", _digest("\n".join(identity)))
    return heads, rows, identities, expressions, corrections


def _reviewed(decisions, rows):
    selected = {}
    if not isinstance(decisions, list):
        raise ValueError("Reviewed relationships must be an array")
    for entry in decisions:
        identity = entry["id"], entry["knowledge_revision"]
        if (_record(identity[0]).table != "semantic" or identity in selected
                or identity not in rows or rows[identity]["kind"] != entry["legacy_kind"]
                or entry.keys() - {"id", "knowledge_revision", "legacy_kind", "type", "label"}):
            raise ValueError(f"Invalid reviewed relationship identity or legacy kind: {identity}")
        shape = {key: entry[key] for key in ("type", "label") if key in entry}
        validate_edge({**shape, "in": rows[identity]["in"], "out": rows[identity]["out"],
                       "text": rows[identity]["text"], "evidence": ["confirmed"]},
                      location=f"Reviewed relationship {identity}")
        selected[identity] = shape
    return selected


class _Plan:
    def __init__(self, memory, *, decisions, assets, behavior_assets):
        self.memory = memory
        self.heads, self.rows, self.identities, self.preimages, self.corrections = _versions(memory)
        self.review = _reviewed(decisions, self.rows)
        sources, snapshots = memory._execute("SELECT * FROM source; SELECT * OMIT text FROM source_version;")
        self.sources = {row["id"]: row for row in sources}
        self.snapshots = {row["id"]: row for row in snapshots}
        self.assets = self._verify_assets(assets, behavior_assets)
        self.vertices = {}
        self.states = {}
        self.provenance = {}
        self.missing_facts = []
        self.archives = []
        self.business = {}
        self._texts = {}
        self.reference_gaps = self._reference_gaps()

    def _reference_gaps(self):
        deliveries, feedback = self.memory._execute(
            "SELECT id,items FROM delivery; SELECT id,target,observed_revision FROM feedback WHERE target != NONE;")
        references = [(row["id"], entry, "delivery") for row in deliveries for entry in row.get("items", [])]
        references.extend((row["id"], {"id": row["target"], "knowledge_revision": row["observed_revision"]},
                           "feedback") for row in feedback)
        return [{"reference": ref, "kind": kind, "target": pin.get("id"),
                 "knowledge_revision": pin.get("knowledge_revision")}
                for ref, pin, kind in references if (pin.get("id"), pin.get("knowledge_revision")) not in self.rows]

    def _verify_assets(self, assets, behavior_assets):
        relative_assets = set()
        candidates = []
        for row in self.snapshots.values():
            if row.get("kind") != "image":
                continue
            candidates.append((assets, "assets", row["asset"], row["revision"]))
        for model in self.memory._execute("SELECT artifact FROM behavior_model;")[0]:
            digest = model["artifact"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Retained behavior artifact has an invalid content hash")
            candidates.append((behavior_assets, "behavior", f"behavior/{digest}.json", digest))
        for directory, prefix, reference, digest in candidates:
            relative = PurePosixPath(reference)
            if directory is None or len(relative.parts) != 2 or relative.parts[0] != prefix:
                raise ValueError(f"Missing recovery asset: {relative}")
            root = Path(directory).resolve(strict=True)
            path = (root / relative.name).resolve(strict=True)
            if path.parent != root:
                raise ValueError(f"Recovery asset outside the supplied directory: {relative}")
            with path.open("rb") as stream:
                if file_digest(stream, "sha256").hexdigest() != digest:
                    raise ValueError(f"Recovery asset hash differs: {relative}")
            relative_assets.add(relative.as_posix())
        return sorted(relative_assets)

    def _snapshot_vertices(self):
        evidence_paths = defaultdict(set)
        for row in self.rows.values():
            if row.get("source_version") and row.get("path"):
                evidence_paths[row["source_version"]].add(row["path"])
        for identity, row in self.snapshots.items():
            source = self.sources[row["source"]]
            paths = evidence_paths[identity]
            if source.get("version") == identity:
                paths.add(source["path"])
            path = row.get("path") or (next(iter(paths)) if len(paths) == 1 else None)
            private = row.get("private") is not False or path is None or source_private(path)
            self.vertices[identity] = Vertex(_record(identity), private, (path,) if path else ())
            self.states[identity] = ("retired" if source.get("deleted") else
                                     "current" if source.get("version") == identity else "historical")
            if path is None:
                self.missing_facts.append({"id": identity, "type": "from_snapshot", "reason": "snapshot_path_ambiguous"})

    def _has_original(self, row, vertex):
        snapshot = self.snapshots[vertex]
        if snapshot.get("kind") == "image":
            return not row.get("raw_revision") or row["raw_revision"] == snapshot["revision"]
        if vertex not in self._texts:
            text = self.memory._execute(f"SELECT VALUE text FROM ONLY {_sql(_record(vertex))};")[0]
            if not isinstance(text, str) or _digest(text) != snapshot["revision"]:
                raise ValueError(f"Retained text snapshot hash differs: {vertex}")
            self._texts[vertex] = text
        text = self._texts[vertex]
        source = SourceContent(row["path"], snapshot["revision"], len(text.encode("utf-8")), 0, text)
        try:
            located = original_text(source, row["start_line"], row["end_line"], row.get("locator"))
        except (KeyError, ValueError):
            return False
        return not row.get("raw_revision") or _digest(located) == row["raw_revision"]

    def _basis(self, row):
        citations = []
        for entry in row.get("basis") or []:
            identity = entry.get("member"), entry.get("knowledge_revision")
            evidence = self.rows.get(identity)
            if (evidence is None or identity not in self.provenance
                    or not self.provenance[identity]["snapshot"]
                    or entry.get("source_version") != evidence.get("source_version")
                    or location(entry) != location(evidence)):
                return None
            citations.append(identity)
        return citations

    def _knowledge_vertices(self):
        knowledge = {identity: row for identity, row in self.rows.items()
                     if _record(identity[0]).table in {"member", "node"}}
        for identity, row in knowledge.items():
            current = self.heads.get(identity[0], {}).get("knowledge_revision") == identity[1]
            self.states[identity] = _status(row, current)
            if identity in self.corrections and self.states[identity] != "retired":
                self.states[identity] = "needs_review"
            snapshot = row.get("source_version")
            has_original = (snapshot in self.snapshots and self.snapshots[snapshot]["source"] == row.get("source")
                            and row.get("path") in self.vertices[snapshot].paths and self._has_original(row, snapshot))
            parent = row.get("parent_version") or {}
            parent_identity = parent.get("id"), parent.get("knowledge_revision")
            if parent.get("id") != row.get("parent") or parent_identity not in knowledge:
                parent_identity = None
            self.provenance[identity] = {"snapshot": snapshot if has_original else None, "parent": parent_identity}
            for type_name, missing in (("from_snapshot", snapshot and not has_original),
                                       ("part_of", row.get("parent") and parent_identity is None)):
                if missing:
                    self.missing_facts.append({"id": identity[0], "knowledge_revision": identity[1],
                                               "type": type_name, "reason": "exact_provenance_unavailable"})
        for identity, row in knowledge.items():
            citations = self._basis(row)
            if citations is None:
                self.missing_facts.append({"id": identity[0], "knowledge_revision": identity[1],
                                           "type": "has_basis", "reason": "exact_provenance_unavailable"})
            self.provenance[identity]["basis"] = citations or []
            self.provenance[identity]["basis_unknown"] = citations is None

        dependents = defaultdict(set)
        for identity, row in knowledge.items():
            basis = self.provenance[identity]
            snapshot = basis["snapshot"]
            paths = self.vertices[snapshot].paths if snapshot else ()
            private = (row.get("private") is not False or basis["basis_unknown"]
                       or (snapshot and self.vertices[snapshot].private)
                       or (row.get("source_version") and snapshot is None))
            self.vertices[identity] = Vertex(self.identities[identity], bool(private), paths)
            if snapshot:
                dependents[snapshot].add(identity)
            for citation in basis["basis"]:
                dependents[citation].add(identity)
        ready = set(dependents)
        while ready:
            origin = ready.pop()
            source, origin_status = self.vertices[origin], self.states[origin]
            for identity in dependents[origin]:
                previous = self.vertices[identity]
                derived = Vertex(previous.record, previous.private or source.private,
                                 tuple(sorted(set(previous.paths) | set(source.paths))))
                if derived != previous:
                    self.vertices[identity] = derived
                    ready.add(identity)
                if origin_status in {"needs_review", "retired"} and self.states[identity] in {"current", "historical"}:
                    self.states[identity] = "needs_review"
                    ready.add(identity)

    def _business_vertices(self):
        for identity, row in self.rows.items():
            if _record(identity[0]).table != "semantic":
                continue
            pinned = row.get("endpoint_versions") or {}
            ends = [(pinned.get(direction, {}).get("id"), pinned.get(direction, {}).get("knowledge_revision"))
                    for direction in ("in", "out")]
            citations = self._basis(row)
            approval = self.review.get(identity)
            if identity[0] not in self.heads:
                reason = "logical_identity_unavailable"
            elif any(pin[0] != row[direction] or pin not in self.vertices
                   for direction, pin in zip(("in", "out"), ends, strict=True)):
                reason = "exact_endpoints_unavailable"
            elif not citations:
                reason = "exact_basis_unavailable"
            elif approval is None:
                reason = "direction_and_meaning_unreviewed"
            elif not isinstance(row.get("conditions", ""), (str, dict)):
                reason = "conditions_unavailable"
            else:
                start, end = (self.vertices[value] for value in ends)
                origins = [self.vertices[value] for value in ends + citations]
                private = row.get("private") is not False or any(origin.private for origin in origins)
                paths = tuple(sorted({path for origin in origins for path in origin.paths}))
                exact = _Record("graph_edge", _digest(_sql(["schema3", *identity])))
                current = self.heads.get(identity[0], {}).get("knowledge_revision") == identity[1]
                status = _status(row, current)
                required = [ends[0], *citations]
                if approval["type"] not in _WITHDRAWN_TARGET_TYPES:
                    required.append(ends[1])
                if status in {"current", "historical"} and (identity in self.corrections or any(
                        self.states[dependency] in {"needs_review", "retired"} for dependency in required)):
                    status = "needs_review"
                self.business[identity] = (Vertex(exact, private, paths), status, start, end, citations, approval)
                continue
            known_provenance = ends + (citations or [])
            privacy_unknown = (type(row.get("private")) is not bool or not citations
                               or any(pin not in self.vertices for pin in ends))
            private = (row.get("private") is True or privacy_unknown
                       or any(self.vertices[pin].private for pin in known_provenance if pin in self.vertices))
            self.archives.append({"id": identity[0], "knowledge_revision": identity[1],
                                  "legacy_kind": row["kind"], "known_endpoint_versions": pinned,
                                  "private": private, "privacy_unknown": privacy_unknown, "reason": reason})

    def build(self):
        self._snapshot_vertices()
        self._knowledge_vertices()
        self._business_vertices()
        statements = ["BEGIN;"]
        for identity, expression in self.preimages.items():
            exact = self.identities[identity]
            statements.append(f"CREATE {_sql(exact)} SET target={_sql(_record(identity[0]))}, "
                              f"knowledge_revision={_sql(identity[1])}, "
                              f"record=object::remove({expression}, 'embedding') RETURN NONE;")
        schema = Path(__file__).with_name("schema.surql").read_text(encoding="utf-8")
        statements.extend(["REMOVE TABLE semantic;", schema])
        for identity, row in self.heads.items():
            if _record(identity).table != "semantic":
                continue
            if not row.get("knowledge_revision"):
                raise ValueError(f"Schema 3 relationship has no retained revision: {identity}")
            key = _identity(row)
            edge = self.business.get(key)
            if edge:
                vertex, status, *_ = edge
                head = {"head": vertex.record, "knowledge_revision": key[1],
                        "stale": status in {"needs_review", "retired"}, "retired": status == "retired"}
            else:
                head = {"knowledge_revision": key[1], "stale": True,
                        "retired": bool(row.get("retired")), "legacy_history_only": True}
            statements.append(f"CREATE {_sql(_record(identity))} CONTENT {_sql(head)} RETURN NONE;")

        for identity, vertex in self.vertices.items():
            status = self.states[identity]
            statements.append(set_state(vertex.record, status))
            link = f"state={state_ref(vertex.record)}"
            if isinstance(identity, str):
                snapshot = self.snapshots[identity]
                row = {"private": vertex.private, "privacy_unknown": type(snapshot.get("private")) is not bool}
                if vertex.paths:
                    row["path"] = vertex.paths[0]
                logical = _record(snapshot["source"])
            else:
                row = {"private": vertex.private, "scope_paths": list(vertex.paths),
                       "privacy_unknown": type(self.rows[identity].get("private")) is not bool}
                logical = _record(identity[0])
                logical_head = self.heads.get(identity[0], {})
                if logical_head.get("knowledge_revision") == identity[1]:
                    if vertex.private and logical_head.get("private") is False:
                        statements.append(f"UPDATE {_sql(logical)} SET private=true RETURN NONE;")
                    if status == "needs_review" and not logical_head.get("stale"):
                        statements.append(f"UPDATE {_sql(logical)} SET stale=true RETURN NONE;")
            fields = [f"{name}={_sql(value)}" for name, value in row.items()]
            statements.append(f"UPDATE {_sql(vertex.record)} SET {', '.join([link, *fields])} RETURN NONE;")
            if isinstance(identity, str) or identity[0] in self.heads:
                statements.append(fact(vertex, Vertex(logical, vertex.private, vertex.paths), "version_of"))
            else:
                self.missing_facts.append({"id": identity[0], "knowledge_revision": identity[1],
                                           "type": "version_of", "reason": "logical_identity_unavailable"})
        for identity, details in self.provenance.items():
            vertex = self.vertices[identity]
            if details["snapshot"]:
                statements.append(fact(vertex, self.vertices[details["snapshot"]], "from_snapshot",
                                       location(self.rows[identity])))
            if details["parent"]:
                statements.append(fact(vertex, self.vertices[details["parent"]], "part_of"))
            statements.extend(fact(vertex, self.vertices[citation], "has_basis") for citation in details["basis"])
        for identity, relation in self.business.items():
            vertex, status, start, end, citations, approved = relation
            logical = _record(identity[0])
            text = self.rows[identity]
            statements.extend([
                set_state(vertex.record, status),
                edge_sql(vertex.record, start, end, approved["type"], logical_id=logical,
                         knowledge_revision=identity[1], private=vertex.private, scope_paths=list(vertex.paths),
                         text=text["text"], conditions=text.get("conditions", ""), label=approved.get("label")),
                fact(vertex, Vertex(logical, vertex.private, vertex.paths), "version_of"),
                f"UPDATE {_sql(self.identities[identity])} SET record={_sql({'id': logical, 'head': vertex.record, 'knowledge_revision': identity[1], 'stale': status in {'needs_review', 'retired'}, 'retired': status == 'retired'})} RETURN NONE;",
            ])
            statements.extend(fact(vertex, self.vertices[citation], "has_basis") for citation in citations)
        for archive in self.archives:
            statements.append(f"UPDATE {_sql(self.identities[_identity(archive)])} SET legacy_history_only=true, "
                              f"legacy_reason={_sql(archive['reason'])}, private={_sql(archive['private'])}, "
                              f"privacy_unknown={_sql(archive['privacy_unknown'])} RETURN NONE;")
        return statements


def upgrade(memory, *, source_sha256, assets=None, behavior_assets=None, relations=None):
    """Upgrade only a disposable, exclusive restoration of the pinned export."""
    source = _Schema3Publication(memory.config)
    project, marker, info = memory._execute(
        "SELECT * FROM ONLY meta:project; SELECT * FROM ONLY meta:graph_migration; INFO FOR DB;",
        check_project=False)
    project_id = memory.connection["project_id"]
    relations = [] if relations is None else relations
    decisions_sha256 = _digest(json.dumps(relations, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if not project or project["project_id"] != project_id:
        raise ValueError("Restored project ID differs from the requested source project")
    if marker:
        report = marker["result"]
        if (project["memory_schema_version"] == 4 and report["source_sha256"] == source_sha256
                and report["decisions_sha256"] == decisions_sha256):
            return report
        raise ValueError("The restore has a different migration receipt")
    source.verify_project()
    tables = info["tables"]
    if "TYPE RELATION" not in tables.get("semantic", "") or {"graph_edge", "graph_state"} & tables.keys():
        raise ValueError("Expected an untouched schema 3 relation table")
    plan = _Plan(source, decisions=relations, assets=assets, behavior_assets=behavior_assets)
    statements = plan.build()
    report = {
        "source_sha256": source_sha256, "decisions_sha256": decisions_sha256, "project_id": project_id,
        "assets": plan.assets,
        "counts": {"knowledge_versions": len(plan.provenance), "source_versions": len(plan.snapshots),
                   "converted_relations": len(plan.business), "archived_relations": len(plan.archives)},
        "archived_relations": plan.archives, "missing_facts": plan.missing_facts,
        "reference_gaps": plan.reference_gaps,
    }
    detail_fields = ("archived_relations", "missing_facts", "reference_gaps")
    receipt = {**report, **{field: [] for field in detail_fields}}
    statements.append(f"CREATE meta:graph_migration CONTENT {_sql({'result': receipt})} RETURN NONE;")
    for field in detail_fields:
        for start in range(0, len(report[field]), 250):
            statements.append(f"UPDATE meta:graph_migration SET result.{field} += "
                              f"{_sql(report[field][start:start + 250])} RETURN NONE;")
    statements.extend(["UPDATE meta:project SET memory_schema_version=4 RETURN NONE;", "COMMIT;"])
    source._publish(statements)
    memory.verify_project()
    return report
