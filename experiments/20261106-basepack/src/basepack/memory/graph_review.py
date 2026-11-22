"""Fixed wave authority and review records for nominated member pairs."""

from pathlib import Path

from .owner import _read, _write
from .relation_contract import validate_edge
from .stages import _read_reference
from .store import _record


_NONPUBLISHED = ("no_relation", "nonpersistent")


def _index_path(memory_dir):
    return Path(memory_dir) / "maintenance" / "graph-reviewed.json"


def reviewed_pairs(memory_dir):
    """Return exact pairs whose fixed co-read received a completed disposition."""
    return set(_read(_index_path(memory_dir)) or ())


def retain_reviews(memory_dir, reviews):
    """Append closed reviews under the current owner's wave lock."""
    resolved = {review["candidate"] for review in reviews if review["outcome"] in ("accepted", *_NONPUBLISHED)}
    if resolved:
        previous = reviewed_pairs(memory_dir)
        if not resolved <= previous:
            _write(_index_path(memory_dir), sorted(previous | resolved))


def grant(task, candidates, resolved, path_key):
    if "graph_candidate" not in task:
        if any(isinstance(value, str) and value.startswith("pair:") for value in task["write_targets"]):
            raise PermissionError("A pair write target requires its authorized graph candidate task")
        return task
    identifier = task["graph_candidate"]
    if (not isinstance(identifier, str) or not identifier.startswith("pair:")
            or identifier not in candidates or identifier in resolved):
        raise PermissionError(f"Graph candidate is outside the fixed scope or already resolved: {identifier}")
    if task["paths"] or task["write_targets"] != [identifier]:
        raise PermissionError("A graph candidate requires empty write paths and its sole pair write target")
    endpoints = candidates[identifier]["endpoints"]
    if (len(endpoints) != 2 or len({row["id"] for row in endpoints}) != 2
            or any(not row["id"].startswith("member:") for row in endpoints)):
        raise ValueError(f"Graph candidate requires two distinct member endpoints: {identifier}")
    read_paths = {}
    revisions = {}
    for endpoint in endpoints:
        path = endpoint["path"]
        key = path_key(path)
        if key in read_paths:
            previous = read_paths[key]
            if revisions[previous] != endpoint["source_revision"]:
                raise ValueError(f"Graph candidate has conflicting original revisions: {identifier}")
        else:
            read_paths[key] = path
            revisions[path] = endpoint["source_revision"]
    return {**task, "graph_endpoints": endpoints, "read_paths": list(revisions), "expected_revisions": revisions}


def _pins(task):
    return {row["id"]: {"id": row["id"], "knowledge_revision": row["knowledge_revision"]}
            for row in task["graph_endpoints"]}


def _edge_matches(edge, pins):
    endpoint_ids = [edge.get("in"), edge.get("out")]
    return (all(isinstance(value, str) and value in pins for value in endpoint_ids)
            and endpoint_ids[0] != endpoint_ids[1]
            and edge.get("endpoint_versions") == {key: pins[edge[key]] for key in ("in", "out")})


def edge_spec(edge):
    """Identify a relation without treating the same pair as a unique edge."""
    return {**{key: edge.get(key) for key in ("in", "out", "endpoint_versions", "type", "label")},
            "conditions": edge.get("conditions") or None}


def edge_content(edge):
    return {"text": edge["text"], "evidence": edge.get("evidence", []), "basis": edge.get("basis", [])}


def _source_basis_within(ref, endpoint):
    if _record(ref["source_version"]) != _record(endpoint["source_version"]):
        return False
    locator = endpoint.get("locator") or {}
    if ref.get("start_line") is None:
        return endpoint["kind"] == "image" and (not locator or ref.get("locator") == locator)
    start, end = ref["start_line"], ref["end_line"]
    if endpoint["kind"] == "image" or not endpoint["start_line"] <= start <= end <= endpoint["end_line"]:
        return False
    if not locator:
        return True
    actual = ref.get("locator") or {}
    return ((start > endpoint["start_line"] or actual.get("start_col", 0) >= locator["start_col"])
            and (end < endpoint["end_line"] or actual.get("end_col", float("inf")) <= locator["end_col"]))


_OTHER_WRITES = ("sources", "members", "nodes", "corrections", "delete_members", "delete_nodes", "delete_edges")


def validate_draft(task, draft, label):
    edges = draft.get("edges")
    if (any(draft.get(field) for field in _OTHER_WRITES) or not isinstance(edges, list)
            or len(edges) != 1 or "id" in edges[0]):
        raise PermissionError(f"{label}: Graph candidate admits exactly one new edge and no other writes")
    edge = edges[0]
    validate_edge(edge, location=label)
    pins = _pins(task)
    if not _edge_matches(edge, pins):
        raise ValueError(f"{label}: Relationship requires the assigned pair and both exact endpoint versions")
    if any(not isinstance(ref, str) or ref not in pins for ref in edge.get("evidence", ())):
        raise ValueError(f"{label}: Relationship evidence must belong to the fixed endpoints")
    for ref in edge.get("basis", ()):
        if "source_version" in ref:
            if any(_source_basis_within(ref, endpoint) for endpoint in task["graph_endpoints"]):
                continue
        elif isinstance(ref.get("id"), str) and ref == pins.get(ref["id"]):
            continue
        raise PermissionError(f"{label}: Relationship basis must stay within the fixed endpoint versions and ranges")


def read_review(task, coverage_ref, draft_count):
    coverage = _read_reference(coverage_ref)
    review = coverage.get("graph_review") if isinstance(coverage, dict) else None
    if not isinstance(review, dict) or review.get("candidate") != task["graph_candidate"]:
        raise ValueError(f"{coverage_ref['path']}: graph_review must identify the assigned candidate")
    if (review.get("outcome"), draft_count) not in (("no_relation", 0), ("nonpersistent", 0), ("proposed", 1)):
        raise ValueError(f"{coverage_ref['path']}: graph_review requires zero drafts for no_relation or nonpersistent, "
                         "or one for proposed")
    reason = review.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(f"{coverage_ref['path']}: graph_review requires a reason")
    expected = [{key: row[key] for key in ("id", "knowledge_revision", "source_version")}
                for row in task["graph_endpoints"]]
    read = review.get("read")
    if read not in (expected, expected[::-1]):
        raise ValueError(f"{coverage_ref['path']}: graph_review.read must identify both exact endpoint versions")
    return {"candidate": task["graph_candidate"], "outcome": review["outcome"], "read": expected, "reason": reason}


def _verify_prepare(task, prepared, label):
    sources = {source["path"]: source for source in prepared["sources"]}
    for endpoint in task["graph_endpoints"]:
        path, identity = endpoint["path"], endpoint["id"]
        source = sources.get(path)
        member = next((row for row in source.get("members", ()) if row["id"] == identity), None) if source else None
        if (source is None or source.get("deleted") or source.get("revision") != endpoint["source_revision"]
                or member is None or member.get("stale") is not False or member.get("retired") is not False
                or any(member.get(key) != endpoint.get(key) for key in (
                    "path", "kind", "knowledge_revision", "source_version", "source_revision",
                    "start_line", "end_line", "locator"))
                or prepared["expected"].get(identity) != endpoint["knowledge_revision"]):
            raise ValueError(f"{label}: Graph prepare does not contain the exact fresh endpoint {identity} at {path}")


def _read_prepare(draft):
    reference = draft["prepare"]
    return _read_reference({**reference, "file_sha256": reference["file_sha256"].lower()})


def _reject_existing_edge(spec, prepared, label):
    for current in prepared["neighborhood"]["edges"]:
        if current.get("stale") is False and current.get("retired") is False and edge_spec(current) == spec:
            raise ValueError(f"{label}: Fixed prepare already contains this current graph edge: {current['id']}")


def _reject_conflicting_members(draft, endpoint_ids, label):
    targets = [member["id"] for member in draft.get("members", ()) if "id" in member]
    targets.extend(draft.get("delete_members", ()))
    targets.extend(item["target"] for item in draft.get("corrections", ()))
    if any(_record(target) in endpoint_ids for target in targets):
        raise ValueError(f"{label}: Wave writes supersede a nominated graph endpoint; prepare a later wave")


def validate_publication(publication):
    """Check the actual selected drafts and any necessary prepare outside the owner lock."""
    from .waves import _path_key

    grants = publication["graph_tasks"]
    scopes = {frozenset(_record(row["id"]) for row in task["graph_endpoints"]) for task in grants.values()}
    if len(scopes) != len(grants):
        raise ValueError("A graph pair may be published by only one wave assignment")
    endpoint_ids = set().union(*scopes)
    revisions = {_path_key(path): revision for task in grants.values()
                 for path, revision in task["expected_revisions"].items()}
    for ref in publication["intent"]["drafts"]:
        draft = _read_reference(ref)
        label = ref["path"]
        if ref["assignment"] in grants:
            task = grants[ref["assignment"]]
            validate_draft(task, draft, label)
            prepared = _read_prepare(draft)
            _verify_prepare(task, prepared, label)
            _reject_existing_edge(task["graph_edge_spec"], prepared, label)
            continue
        _reject_conflicting_members(draft, endpoint_ids, label)
        paths = {_path_key(source if isinstance(source, str) else source["path"]) for source in draft["sources"]}
        overlapping = paths & revisions.keys()
        if overlapping:
            prepared = {_path_key(row["path"]): row for row in _read_prepare(draft)["sources"]}
            if any(prepared[path].get("deleted") or prepared[path].get("revision") != revisions[path]
                   for path in overlapping):
                raise ValueError(f"{label}: Wave changes a nominated original; prepare a later wave")


def frozen_edges(publication, batch):
    """Resolve an exact frozen graph edge per selected grant without rereading author prepare."""
    from .waves import _path_key

    grants = publication["graph_tasks"]
    edges = batch.get("edges", [])
    if len(grants) == len(publication["intent"]["drafts"]):
        if any(batch.get(field) for field in _OTHER_WRITES) or len(edges) != len(grants):
            raise PermissionError("Frozen graph wave contains writes outside its authorized pairs")
    result = {}
    for task in grants.values():
        pins = _pins(task)
        _reject_conflicting_members(batch, {_record(identity) for identity in pins}, "Frozen graph wave")
        revisions = {_path_key(path): revision for path, revision in task["expected_revisions"].items()}
        for source in batch["sources"]:
            key = _path_key(source["path"])
            if key in revisions and (source.get("deleted") or source.get("revision") != revisions[key]):
                raise ValueError("Frozen wave changes a nominated original; prepare a later wave")
        matches = [edge for edge in edges if edge_spec(edge) == task["graph_edge_spec"]]
        if len(matches) != 1 or matches[0]["id"] in batch["expected"]:
            raise ValueError(f"Frozen graph wave must contain one new edge for {task['graph_candidate']}")
        edge, = matches
        if edge_content(edge) != task["graph_edge_content"]:
            raise ValueError(f"Frozen relationship text or evidence changed for {task['graph_candidate']}")
        if any(batch["expected"].get(key) != pin["knowledge_revision"] for key, pin in pins.items()):
            raise ValueError(f"Frozen graph wave supersedes pinned versions for {task['graph_candidate']}")
        result[task["graph_candidate"]] = edge["id"]
    if len(set(result.values())) != len(grants):
        raise ValueError("A frozen graph edge must belong to exactly one wave assignment")
    return result


def closure_reviews(state):
    publication = state["publication"]
    published = publication.get("graph_edges", {}) if publication and publication["status"] == "committed" else {}
    records = []
    for task in state["tasks"]:
        if "graph_candidate" not in task:
            continue
        record = {"candidate": task["graph_candidate"], "task": task["id"], "outcome": "pending",
                  "task_status": task["status"]}
        if task["result"]:
            record.update(coverage=task["result"]["coverage"], errors=task["result"]["errors"])
        if task["status"] == "submitted":
            coverage = task["result"]["coverage"]
            review = read_review(task, coverage, len(task["result"]["drafts"]))
            record.update(coverage=coverage, read=review["read"], reason=review["reason"])
            if review["outcome"] in _NONPUBLISHED:
                record["outcome"] = review["outcome"]
            elif record["candidate"] in published:
                record.update(outcome="accepted", edge=published[record["candidate"]])
        records.append(record)
    return records
