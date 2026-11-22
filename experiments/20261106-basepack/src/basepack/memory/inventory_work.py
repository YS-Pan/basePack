"""Turn selected inventory groups into tasks within an actual maintenance receipt."""

import json
from hashlib import sha256

from .content import _project_path, _read_bytes
from .inventory_groups import group_sources
from .privacy import privacy_rules, rules_revision, source_private


def inventory_report(config, memory, *, collection, group_map_path):
    from .inventory import inventory

    group_map = None
    if group_map_path is not None:
        path = _project_path(config.root, group_map_path)
        group_map_path = path.relative_to(config.root).as_posix()
        group_map = json.loads(path.read_text(encoding="utf-8-sig"))
    return {**inventory(config, memory, collection=collection, group_map=group_map),
            "group_map": group_map_path}


def grouped_tasks(config, report, receipt, group_ids, *, read_paths=(), stage=None):
    """Use inventory as a proposal. The live receipt supplies write authority."""
    if report["project_id"] != config.raw["memory"]["project_id"]:
        raise ValueError("Inventory belongs to another project")
    rules = privacy_rules(config)
    if report["privacy_rules_revision"] != rules_revision(rules):
        raise ValueError("Inventory privacy rules changed; refresh inventory")
    groups = {group["id"]: group for group in report["groups"]}
    if len(group_ids) != len(set(group_ids)) or any(key not in groups for key in group_ids):
        raise ValueError("Select distinct group IDs from this inventory")
    rows = {row["path"]: row for row in report["sources"]}
    map_path = report["group_map"]
    group_map = (json.loads(_project_path(config.root, map_path).read_text(encoding="utf-8-sig"))
                 if map_path is not None else None)
    current = {group["id"]: group for group in group_sources(config, report["sources"], group_map)["groups"]}
    if any(current.get(key) != groups[key] for key in group_ids):
        raise ValueError("Selected source grouping changed; refresh inventory")

    semantic = {row["path"]: row for row in receipt["semantic"]}
    scope = set(stage["remaining"]["paths"] if stage else receipt["workset"]["included"])
    read_paths = {_project_path(config.root, path).relative_to(config.root).as_posix() for path in read_paths}
    selected_paths = {path for key in group_ids for path in groups[key]["paths"]}
    if not read_paths <= selected_paths:
        raise ValueError("Read paths must belong to a selected inventory group")

    tasks, shared, without_work = [], [], []
    for key in group_ids:
        group = groups[key]
        paths = [path for path in group["paths"] if path in scope and path in semantic
                 and rows[path]["status"] in {"available", "missing"}]
        evidence = [path for path in group["paths"] if path in read_paths]
        if any(rows[path]["status"] != "available" for path in evidence):
            raise ValueError(f"Group {key} has unavailable read-only evidence")
        revisions = {}
        for path in dict.fromkeys([*paths, *evidence]):
            row = rows[path]
            if row["private"] != source_private(path, rules["private_scope"]):
                raise ValueError(f"Inventory privacy classification differs for {path!r}")
            revision = row["revision"]
            original = _project_path(config.root, path)
            if row["status"] == "missing":
                matches = not original.exists()
            else:
                data, _ = _read_bytes(original)
                matches = sha256(data).hexdigest() == revision
            if not matches or (path in paths and semantic[path]["current_revision"] != revision):
                raise ValueError(f"Inventory differs from current preflight or original for {path!r}")
            revisions[path] = revision

        # Omit only unregistered byte copies when their representative is itself
        # writing in this task. Accepted paths and partial ranges stay explicit.
        aliases = [alias for alias in group["aliases"]
                   if group["kind"] in {"mapped", "chat"} and alias["proof"] == "same_bytes"
                   and alias["path"] in paths
                   and alias["representative"] in paths and not rows[alias["path"]]["registered"]
                   and semantic[alias["path"]]["accepted_source_version"] is None
                   and revisions[alias["path"]] == revisions[alias["representative"]]]
        omitted = {alias["path"] for alias in aliases}
        writes = [path for path in paths if path not in omitted]
        if not writes:
            without_work.append(key)
            continue
        reads = [path for path in evidence if path not in writes]
        planned_reads = [alias for alias in group["aliases"]
                         if alias["path"] in writes and alias["representative"] in writes + reads]
        tasks.append({
            "id": key,
            "goal": "Read this source group together and resolve its authorized semantic work.",
            "paths": writes,
            "read_paths": reads,
            "write_targets": [],
            "outputs": "Scoped drafts, covered ranges, and any grouping or evidence issues.",
            "expected_revisions": {path: revisions[path] for path in [*writes, *reads]},
            "shared_reading": planned_reads,
        })
        shared.extend(aliases)
    if not tasks:
        raise ValueError("Selected groups contain no eligible work; inspect the current preflight")
    return tasks, {"shared_reading": shared, "groups_without_work": without_work}
