"""Derive a lightweight marker from retained, version-pinned provenance."""

import posixpath


def source_private(path: str) -> bool:
    """Classify a normalized project-relative path, never its text content."""
    return posixpath.normpath(path.replace("\\", "/")).split("/", 1)[0].casefold() == "private"


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
        if "private" in row:
            if row["private"]:
                return True
            continue
        if "source_version" in row:
            snapshot = source_version(row["source_version"])
            # Old snapshots without a path can use the path retained in the
            # exact knowledge version that refers to them, never today's source.
            if snapshot is None or "private" not in snapshot and "path" not in snapshot:
                snapshot = {**(snapshot or {}), **({"path": row["path"]} if "path" in row else {})}
            pending.append(snapshot)
        elif "path" in row:
            if source_private(row["path"]):
                return True
        elif not row.get("basis"):
            unknown = True
        for basis in row.get("basis", []):
            pinned = (knowledge_version(basis["member"], basis["knowledge_revision"])
                      if basis.get("knowledge_revision") else None)
            pending.append(pinned)
            snapshot = source_version(basis["source_version"]) if basis.get("source_version") else None
            if (snapshot is not None and "private" not in snapshot and "path" not in snapshot
                    and pinned is not None and "path" in pinned
                    and pinned.get("source_version") == basis.get("source_version")):
                snapshot = {**snapshot, "path": pinned["path"]}
            pending.append(snapshot)
        for endpoint in row.get("endpoint_versions", {}).values():
            pending.append(knowledge_version(endpoint["id"], endpoint["knowledge_revision"])
                           if endpoint.get("knowledge_revision") else None)
        if (str(row.get("id", "")).startswith("semantic:")
                and not row.get("endpoint_versions")):
            unknown = True
    return None if unknown else False
