"""Input boundaries shared by request rendering and memory commands."""

import json
from hashlib import sha256
from collections import defaultdict, deque
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath


def normalize_scope(value: str) -> str:
    """Keep a literal project-relative prefix; an empty prefix means all paths."""
    if not isinstance(value, str):
        raise ValueError("scope must be a project-relative path prefix string")
    scope = value.replace("\\", "/")
    if (PureWindowsPath(scope).drive or PurePosixPath(scope).is_absolute()
            or ".." in PurePosixPath(scope).parts):
        raise ValueError(f"scope must be a project-relative path prefix: {value}")
    return scope


def load_json_file(path):
    source = Path(path)
    if source.is_dir():
        raise ValueError(f"Expected a UTF-8 JSON file, got a directory: {path}")
    return json.loads(source.read_text(encoding="utf-8"))


def _interleave(groups):
    queues = deque(deque(rows) for _, rows in sorted(groups.items()))
    while queues:
        queue = queues.popleft()
        yield queue.popleft()
        if queue:
            queues.append(queue)


def _overview_groups(members, nodes, prefix):
    groups = (defaultdict(list), defaultdict(list), defaultdict(list))
    node_groups, project_groups, chat_groups = groups
    for row in members:
        path = row["path"].replace("\\", "/")
        target = chat_groups if path.startswith(prefix) else project_groups
        key = "chats" if target is chat_groups else path.split("/", 1)[0]
        target[key].append(dict(row, record_type="member", clue_role="map"))
    for row in nodes:
        node_groups[row["kind"]].append(dict(row, record_type="node", clue_role="map"))
    return groups


def _rotate(values, seed):
    if not values:
        return values
    offset = int.from_bytes(sha256(seed.encode("utf-8")).digest()[:8], "big") % len(values)
    return values[offset:] + values[:offset]


def overview_working_set(members, nodes, limit, *, chat_prefix, rotation):
    """Bound the exact access calculation; rotate a diverse structural sample daily."""
    if limit < 0:
        raise ValueError("Brief limit must be non-negative")
    if not limit:
        return []
    prefix = chat_prefix.replace("\\", "/").rstrip("/") + "/"
    groups = _overview_groups(members, nodes, prefix)
    buckets = []
    for index, category in enumerate(groups):
        keys = _rotate(sorted(category), f"{rotation}:{index}:groups")
        queues = []
        for key in keys:
            rows = sorted(category[key], key=lambda row: (row.get("path", ""), row["kind"], str(row["id"])))
            queues.append(deque(_rotate(rows, f"{rotation}:{index}:{key}")))
        bucket = []
        active = deque(queues)
        while active:
            queue = active.popleft()
            bucket.append(queue.popleft())
            if queue:
                active.append(queue)
        buckets.append(bucket)
    cap = min(max(limit * 8, 24), 96)
    selected = []
    for row in _interleave({index: rows for index, rows in enumerate(buckets) if rows}):
        if len(selected) == cap:
            break
        selected.append(row)
    return selected


def startup_overview(members: list[dict], nodes: list[dict], sources: list[dict],
                     limit: int, *, mandatory: list[dict] = (),
                     chat_prefix: str = ".basepack/memory/codex/", candidates=None) -> dict:
    """Bound startup clues across graph, project and managed-chat entrances.

    Path groups and node kinds organize an inventory; they do not measure semantic
    coverage. The full source inventory remains available through memory sources.
    """
    if limit < 0:
        raise ValueError("Brief limit must be non-negative")
    prefix = chat_prefix.replace("\\", "/").rstrip("/") + "/"
    node_groups, project_groups, chat_groups = _overview_groups(members, nodes, prefix)
    if candidates is None:
        clue_members, clue_nodes = members, nodes
    else:
        clue_members = [row for row in candidates if row["record_type"] == "member"]
        clue_nodes = [row for row in candidates if row["record_type"] == "node"]
    clue_groups = _overview_groups(clue_members, clue_nodes, prefix)
    kinds = {"file": 0, "image": 1, "section": 2}
    def priority(row):
        low, high = row.get("access_interval", [0.0, 1.0])
        return (-high, -low, kinds.get(row["kind"], 3), row.get("path", ""), str(row["id"]))
    for category in clue_groups:
        for group in category.values():
            group.sort(key=priority)
    buckets = [list(_interleave(category)) for category in clue_groups]
    clues = []
    for row in _interleave({index: rows for index, rows in enumerate(buckets) if rows}):
        if len(clues) >= limit:
            break
        item = {key: row[key] for key in ("id", "record_type", "kind", "path", "source_version",
                "knowledge_revision", "private", "clue_role", "access_interval", "access_status",
                "access_model", "access_compiled_j", "access_fact_j", "access_support", "access_prior") if key in row}
        item["title"] = row.get("title", "")[:160]
        text = row.get("text", "")
        item["text"] = text[:800]
        item["text_truncated"] = len(text) > 800
        clues.append(item)
    mapped = {row.get("path") for row in (*members, *mandatory)}
    unmapped = [row for row in sources if row.get("path") not in mapped and not row.get("deleted")]
    # A few locators signal the gap without copying the full inventory into every brief.
    unmapped_groups = {0: [], 1: []}
    for row in unmapped:
        group = 1 if row["path"].replace("\\", "/").startswith(prefix) else 0
        unmapped_groups[group].append(row)
    examples = []
    for row in _interleave({key: rows for key, rows in unmapped_groups.items() if rows}):
        if len(examples) >= min(limit, 3):
            break
        examples.append({key: row[key] for key in ("id", "path", "kind", "private") if key in row})
    count = len(members) + len(nodes)
    return {"clues": clues, "overview_count": count, "clues_omitted_count": count - len(clues),
            "overview_groups": {"graph_nodes": len(nodes),
                                "project_summaries": sum(map(len, project_groups.values())),
                                "managed_chat_summaries": sum(map(len, chat_groups.values()))},
            "unmapped_sources": examples, "unmapped_count": len(unmapped),
            "unmapped_omitted_count": len(unmapped) - len(examples)}
