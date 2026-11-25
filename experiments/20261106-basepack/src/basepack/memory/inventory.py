"""Observe project originals and registered versions without starting maintenance."""

from collections import Counter
from hashlib import sha256
from pathlib import Path

from .collection import _inside, load_collection
from .content import _check_collection_revision, _project_path, _read_bytes
from .discovery import retained_codex_paths, source_candidates
from .images import IMAGE_SUFFIXES
from .privacy import privacy_rules, rules_revision, source_private


_CAPTURE_GAP_FIELDS = ("path", "project_id", "thread_id", "turn_id", "item_id", "part", "part_type",
                       "reason", "classification", "binding_reason", "referenced_thread_id", "item_count")


def _codex_sources(config, collection):
    from .codex_index_config import configured

    if configured(config):
        if collection is not None:
            raise ValueError("Dialogue indexing cannot use a legacy collection receipt")
        return {"paths": [], "gaps": [], "expected": {}, "thread_ids": {}, "observation": {"status": "indexed"}}
    project_id = config.raw["memory"].get("codex", {}).get("project_id")
    if collection is None:
        retained = retained_codex_paths(config, project_id, include_threads=True)
        return {**retained, "expected": {}, "observation": {
            "status": "retained" if project_id else "not_configured",
            "project_id": project_id, "freshness": "unknown",
        }}

    root = Path(config.root).resolve()
    receipt = load_collection(config, collection)
    thread_ids = {}
    details = receipt.get("capture", {})
    for thread in details.get("threads", []):
        for path in [thread.get("path"), *thread.get("attachments", [])]:
            if path is not None:
                relative = _inside(root, path).relative_to(root).as_posix()
                thread_ids.setdefault(relative, set()).add(thread["thread_id"])
    return {"paths": receipt["paths"],
            "thread_ids": {path: sorted(ids) for path, ids in thread_ids.items()},
            "gaps": [*receipt.get("discovery_gaps", []), *details.get("gaps", [])],
            "expected": {item["path"]: item["sha256"] for item in receipt["snapshots"]},
            "observation": {"status": "captured", "project_id": receipt["project_id"],
                            "freshness": "receipt_cutoff",
                            "receipt": _inside(root, collection).relative_to(root).as_posix(),
                            "unresolved_threads": receipt.get("unresolved_threads", [])}}


def _observe(target, path, *, expected, registered, missing_reason):
    suffix = target.suffix.lower()
    kind = "image" if suffix in IMAGE_SUFFIXES else (registered or {}).get("kind")
    fields = {"kind": kind, "suffix": suffix, "revision": None, "size": None}
    try:
        raw, stat = _read_bytes(target)
    except FileNotFoundError:
        _check_collection_revision(path, expected, None)
        return {**fields, "status": "missing", "reason": missing_reason}
    except OSError as error:
        return {**fields, "status": "unreadable", "reason": "read_error", "error": str(error)}
    except RuntimeError as error:
        return {**fields, "status": "unreadable", "reason": "changed_during_read", "error": str(error)}

    revision = sha256(raw).hexdigest()
    _check_collection_revision(path, expected, revision)
    fields.update(revision=revision, size=stat.st_size, mtime_ns=stat.st_mtime_ns)
    if kind == "image":
        return {**fields, "status": "available"}
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return {**fields, "kind": "binary", "status": "unsupported", "reason": "non_utf8", "error": str(error)}
    if "\0" in content:
        return {**fields, "kind": "binary", "status": "unsupported", "reason": "binary"}
    return {**fields, "kind": "text", "status": "available", "line_count": len(content.splitlines())}


def _registration_status(registered, observed):
    if registered is None:
        return "unregistered"
    if registered["deleted"]:
        return "deleted"
    if observed["revision"] is None:
        return "missing" if observed["status"] == "missing" else "unknown"
    if observed["revision"] == registered["revision"]:
        return "unchanged"
    return "changed"


def inventory(config, memory, *, collection=None, group_map=None) -> dict:
    """Return disk observations and proposed groups without acquiring maintenance ownership.

    A row's ``registered`` object is the prior database metadata, or ``None``
    for an unregistered path. Its hashes and privacy need not match the live
    observation. Neither registration nor grouping establishes acceptance.
    """
    from .codex_index_config import configured, legacy_capture_path
    from .inventory_groups import group_sources

    root = Path(config.root).resolve()
    candidates, mode = source_candidates(config, include_missing=True)
    indexed = configured(config)
    registered = {_project_path(root, row["path"]): {key: row[key] for key in row if key != "path"}
                  for row in memory.sources() if not indexed or not legacy_capture_path(config, row["path"])}
    for target in registered:
        candidates.setdefault(target, set()).add("registered")

    codex = _codex_sources(config, collection)
    capture_paths = {_project_path(root, path) for path in codex["paths"]}
    missing = {_project_path(root, gap["path"]) for gap in codex["gaps"]
               if gap.get("reason") == "missing_attachment" and "path" in gap}
    capture_sources = capture_paths | missing
    for target in capture_sources:
        candidates.setdefault(target, set()).add("codex")
    expected = {_project_path(root, path): value for path, value in codex["expected"].items()}
    threads = {_project_path(root, path): value for path, value in codex["thread_ids"].items()}

    rules = privacy_rules(config)
    rows, gaps = [], []
    for target, origins in sorted(candidates.items(), key=lambda item: item[0].as_posix()):
        path = target.relative_to(root).as_posix()
        previous = registered.get(target)
        observed = _observe(target, path, expected=expected.get(target), registered=previous,
                            missing_reason="missing_attachment" if target in missing else "missing")
        row = {"path": path, **observed, "private": source_private(path, rules["private_scope"]),
               "origins": sorted(origins), "registered": previous,
               "registration_status": _registration_status(previous, observed)}
        if target in capture_sources and target in threads:
            row["codex_threads"] = threads[target]
        rows.append(row)
        if observed["status"] != "available":
            gaps.append({key: row[key] for key in ("path", "reason", "private", "error") if key in row})
    capture_gaps = [{key: gap[key] for key in _CAPTURE_GAP_FIELDS if key in gap} for gap in codex["gaps"]
                    if gap.get("reason") != "missing_attachment" or "path" not in gap]
    grouping = group_sources(config, rows, group_map)
    by_status = dict(sorted(Counter(row["status"] for row in rows).items()))
    counts = {"paths": len(rows), "by_status": by_status,
              "groups": len(grouping["groups"]),
              "byte_duplicates": sum(alias["proof"] == "same_bytes" for group in grouping["groups"]
                                     for alias in group["aliases"]),
              "gaps": len(gaps) + len(capture_gaps) + len(grouping["grouping_gaps"])}
    return {"project_id": config.raw["memory"]["project_id"], "discovery_mode": mode,
            "privacy_rules_revision": rules_revision(rules), "capture": codex["observation"],
            "sources": rows, "gaps": gaps, "capture_gaps": capture_gaps, "counts": counts, **grouping}
