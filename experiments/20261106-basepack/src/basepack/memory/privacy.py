"""Derive a lightweight marker from retained, version-pinned provenance."""

import posixpath
from hashlib import sha256
import json
import re


_UNPROVEN_PRIVATE = "_unproven_private"


def privacy_rules(config=None) -> dict:
    """Freeze the one-way project path policy, independently of discovery."""
    scope = [] if config is None else config.raw["memory"].get("private_scope", [])
    if not isinstance(scope, list) or any(not isinstance(path, str) for path in scope):
        raise ValueError("memory.private_scope must be a list of project-relative paths")
    normalized = []
    for path in scope:
        value = posixpath.normpath(path.replace("\\", "/")).casefold()
        if (not path.strip() or value.startswith("/") or re.match(r"^[a-z]:", value)
                or value == ".." or value.startswith("../") or any(char in value for char in "*?[]")):
            raise ValueError(f"memory.private_scope must contain project-relative paths without globs: {path}")
        normalized.append(value)
    return {"version": 1, "private_scope": sorted(set(normalized))}


def rules_revision(rules: dict) -> str:
    return sha256(json.dumps(rules, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def source_private(path: str, private_scope=()) -> bool:
    """Classify a normalized project-relative path, never its text content."""
    path = posixpath.normpath(path.replace("\\", "/")).casefold()
    return (path.split("/", 1)[0] == "private" or any(
        prefix == "." or path == prefix or path.startswith(prefix + "/") for prefix in private_scope))


def known_private(row: dict) -> bool | None:
    """Read a classification, excluding a conservative visibility marker."""
    marker = row.get("private")
    if type(marker) is bool and not (row.get("privacy_unknown") or row.get(_UNPROVEN_PRIVATE)):
        return marker
    return None


def privacy_fields(marker: bool | None) -> dict:
    if marker is None:
        return {"private": True, "privacy_unknown": True}
    return {"private": marker}


def derive_private(record: dict, *, source_version, knowledge_version) -> bool | None:
    """Return None when legacy provenance cannot establish either marker.

    Callbacks resolve the exact source ID or (knowledge ID, revision), and may
    return None for unavailable retained records. Current identities are never
    substituted for missing versions. This helper performs no writes.
    """
    pending = [record]
    seen = {}
    unknown = False
    while pending:
        row = pending.pop()
        if row is None:
            unknown = True
            continue
        identity = (("record", str(row["id"]), row.get("knowledge_revision")) if "id" in row
                    else ("object", id(row)))
        if identity in seen:
            continue
        seen[identity] = row
        marker = known_private(row)
        if marker is not None:
            if marker:
                return True
            continue
        if row.get(_UNPROVEN_PRIVATE):
            unknown = True
        if "source_version" in row:
            snapshot = source_version(row["source_version"])
            # Old snapshots without a path can use the path retained in the
            # exact knowledge version that refers to them, never today's source.
            if snapshot is not None and "path" not in snapshot and "path" in row:
                snapshot = {**snapshot, "path": row["path"]}
            pending.append(snapshot)
        elif "path" in row:
            if source_private(row["path"]):
                return True
            if row.get("privacy_unknown"):
                unknown = True
        elif not (row.get("basis") or row.get("direct_basis") or row.get("endpoint_versions")):
            unknown = True
        for basis in row.get("basis", []):
            pinned = (knowledge_version(basis["member"], basis["knowledge_revision"])
                      if basis.get("knowledge_revision") else None)
            pending.append(pinned)
            snapshot = source_version(basis["source_version"]) if basis.get("source_version") else None
            if (snapshot is not None and "path" not in snapshot
                    and pinned is not None and "path" in pinned
                    and pinned.get("source_version") == basis.get("source_version")):
                snapshot = {**snapshot, "path": pinned["path"]}
            pending.append(snapshot)
        for basis in row.get("direct_basis", []):
            if basis.get("source_version"):
                pending.append(source_version(basis["source_version"]))
            else:
                pending.append(knowledge_version(basis["id"], basis["knowledge_revision"])
                               if basis.get("id") and basis.get("knowledge_revision") else None)
        for endpoint in row.get("endpoint_versions", {}).values():
            pending.append(knowledge_version(endpoint["id"], endpoint["knowledge_revision"])
                           if endpoint.get("knowledge_revision") else None)
        if (str(row.get("id", "")).startswith("semantic:")
                and not row.get("endpoint_versions")):
            unknown = True
    return None if unknown else False
