"""Select bounded outcome work and retain its fixed wave closure references."""

from hashlib import sha256
import json
from pathlib import Path

from .owner import _read
from .query import normalize_scope
from .stages import _read_reference


def _identity(path, revision, version):
    value = json.dumps([path, revision, version], ensure_ascii=False, separators=(",", ":"))
    return "outcome:" + sha256(value.encode("utf-8")).hexdigest()


def nominate(memory_dir, sources, native_paths, line_count):
    """Offer one current chat or a continuation from its closed wave."""
    state = _read(Path(memory_dir) / "maintenance" / "wave.json") or {}
    reviews = state.get("outcome_reviews", {})
    ordered = sorted((sources[path] for path in dict.fromkeys(native_paths) if path in sources),
                     key=lambda row: (-row["mtime_ns"], row["path"]))
    continuation = fresh = retry = None
    for source in ordered:
        identity = _identity(source["path"], source["revision"], source["version"])
        review = reviews.get(source["path"])
        if review is None or review["candidate"] != identity:
            if fresh is None:
                fresh = (source, identity, None, {})
            continue
        if review["status"] == "continue":
            continuation = (source, identity, review, {})
            break
        if review["status"] == "blocked":
            new_evidence = {path: sources[path]["version"] for path, version in review["observed_dependencies"].items()
                            if path in sources and sources[path]["version"] != version}
            if new_evidence:
                continuation = (source, identity, review, new_evidence)
                break
        if review["status"] == "retry" and retry is None:
            retry = (source, identity, review, {})
    selected = continuation or fresh or retry
    if selected is None:
        return None
    source, identity, review, new_evidence = selected
    path = source["path"]
    candidate = {"id": identity, "path": path, "revision": source["revision"], "source_version": source["version"],
                 "start_line": 1, "end_line": line_count(path)}
    if "private" in source:
        candidate["private"] = source["private"]
    if review:
        if _read_reference(review["closure"])["outcome_review"]["candidate"] != identity:
            raise ValueError("Outcome closure does not match its selected chat version")
        candidate.update(start_line=review["resume_line"], previous=review["closure"])
    if new_evidence:
        candidate["new_evidence"] = new_evidence
    return candidate if candidate["end_line"] else None


def grant(task, candidate, resolved):
    identifier = task.get("outcome_candidate")
    if identifier is None:
        if any(isinstance(value, str) and value.startswith("outcome:") for value in task["write_targets"]):
            raise PermissionError("An outcome target requires its authorized outcome task")
        return task
    if candidate is None or candidate["id"] != identifier or identifier in resolved:
        raise PermissionError("Outcome task is outside the fixed scope or already reviewed")
    if (task["paths"] or task.get("read_paths") or task["write_targets"] != [identifier]
            or "graph_candidate" in task):
        raise PermissionError("Outcome tasks require empty write paths and their sole outcome target")
    path = candidate["path"]
    return {**task, "outcome_candidate": candidate, "read_paths": [path],
            "expected_revisions": {path: candidate["revision"]}}


def validate_draft(task, draft, label):
    from .draft import _read_prepare
    from .graph_review import _reject_existing_edge, edge_spec

    fields = ("sources", "members", "nodes", "corrections", "delete_members", "delete_nodes", "delete_edges")
    edges = draft.get("edges", ())
    if any(draft.get(field) for field in fields) or not edges or any("id" in edge for edge in edges):
        raise PermissionError(f"{label}: An outcome draft may write only new relationships")
    prepared, _ = _read_prepare(draft["prepare"], f"{label}: prepare")
    seed = task["outcome_candidate"]
    if not any(source["path"] == seed["path"] and source.get("revision") == seed["revision"]
               and source.get("previous", {}).get("source_version") == seed["source_version"]
               for source in prepared["sources"]):
        raise ValueError(f"{label}: Prepare must contain the exact selected chat source version")
    seen = []
    for edge in edges:
        if any(not isinstance(edge[side], str) for side in ("in", "out")):
            raise ValueError(f"{label}: Outcome relationships require existing exact or prepared endpoints")
        spec = edge_spec(edge)
        if spec in seen:
            raise ValueError(f"{label}: Duplicate relationship in outcome draft")
        _reject_existing_edge(spec, prepared, label)
        seen.append(spec)


def reject_current_duplicates(memory, reference):
    """Check just the evidenced endpoint pairs before a new freeze."""
    from .draft import _read_prepare, read_fixed_author_draft
    from .graph_query_store import resolve_seed
    from .relation_contract import EXACT_ENDPOINT_TABLES
    from .store import _record, _sql

    draft = read_fixed_author_draft(reference)
    prepared, _ = _read_prepare(draft["prepare"], "Outcome prepare")
    endpoints = {}
    for edge in draft["edges"]:
        exact = []
        for side in ("in", "out"):
            identity = edge[side]
            pin = edge.get("endpoint_versions", {}).get(side)
            target = _record(identity)
            if target.table in EXACT_ENDPOINT_TABLES:
                exact.append(target)
                continue
            revision = pin["knowledge_revision"] if pin else prepared["expected"][identity]
            key = (identity, revision)
            if key not in endpoints:
                endpoints[key] = _record(resolve_seed(memory, identity, knowledge_revision=revision))
            exact.append(endpoints[key])
        start, end = exact
        rows, = memory._execute("SELECT id, conditions, label FROM graph_edge WHERE "
                                f"in={_sql(start)} AND type={_sql(edge['type'])} AND out={_sql(end)} "
                                "AND logical_id != NONE AND state.status = 'current';")
        for row in rows:
            if row.get("label") == edge.get("label") and (row.get("conditions") or None) == (edge.get("conditions") or None):
                raise ValueError(f"{reference['path']}: Outcome relationship already current: {row['id']}")


def read_review(task, coverage_ref):
    candidate = task["outcome_candidate"]
    coverage = _read_reference(coverage_ref)
    review = coverage.get("outcome_review") if isinstance(coverage, dict) else None
    if not isinstance(review, dict):
        raise ValueError("Outcome coverage requires an outcome_review object")
    status = review.get("status")
    through = review.get("checked_through")
    missing = review.get("missing_paths", {})
    reason = review.get("reason")
    breakpoint = review.get("breakpoint", candidate["start_line"])
    if (review.get("candidate") != candidate["id"] or review.get("revision") != candidate["revision"]
            or review.get("source_version") != candidate["source_version"]
            or not isinstance(reason, str) or not reason.strip()):
        raise ValueError("Outcome coverage requires the assigned candidate, exact revision and reason")
    if (type(through) is not int or not candidate["start_line"] <= through <= candidate["end_line"]
            or status not in ("continue", "exhausted", "blocked")
            or (status == "continue" and through == candidate["end_line"])
            or (status == "exhausted" and (through != candidate["end_line"] or missing))
            or type(breakpoint) is not int or not 1 <= breakpoint <= through
            or not isinstance(missing, dict)
            or any(not path or (version is not None and (not isinstance(version, str)
                                                       or not version.startswith("source_version:")))
                   for path, version in missing.items())):
        raise ValueError("Outcome coverage requires a checked range and a valid continuation or final disposition")
    return {"status": status, "checked_through": through, "breakpoint": breakpoint,
            "missing_paths": {Path(normalize_scope(path)).as_posix(): version for path, version in missing.items()},
            "reason": reason}


def checkpoint(review, closure):
    offered = review.get("offered_paths", {})
    observed = {path: offered.get(path, version) for path, version in review["missing_paths"].items()}
    return {"closure": closure, "observed_dependencies": observed,
            **{key: review[key] for key in ("candidate", "status", "resume_line")}}


def closure_review(state, published):
    """Advance an outcome only when the wave admitted its coverage and all of its drafts."""
    task = next((task for task in state["tasks"] if "outcome_candidate" in task), None)
    if task is None:
        return None
    candidate = task["outcome_candidate"]
    result = task["result"]
    record = {"candidate": candidate["id"], "path": candidate["path"], "source_version": candidate["source_version"],
              "revision": candidate["revision"],
              "status": "retry", "resume_line": candidate["start_line"],
              "missing_paths": {}}
    if result is not None:
        record.update(coverage=result["coverage"], errors=result["errors"])
    if task["status"] == "submitted":
        review = read_review(task, result["coverage"])
        if all({**ref, "assignment": task["id"]} in published for ref in result["drafts"]):
            record.update(review)
            if review["status"] == "continue":
                record["resume_line"] = review["checked_through"] + 1
            elif review["status"] == "blocked":
                record["resume_line"] = review["breakpoint"]
                if "new_evidence" in candidate:
                    record["offered_paths"] = candidate["new_evidence"]
    return record
