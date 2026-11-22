"""Build read groups from observed revisions and project-local provenance."""

from collections import defaultdict
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
import re


_REVISION = re.compile(r"[0-9a-f]{64}\Z")
_RANGE_KEYS = ("start_line", "end_line", "representative_start_line",
               "representative_end_line")


def _nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Inventory group map {label} must be a nonempty string")
    return value


def _path(value):
    path = _nonempty(value, "path")
    relative = PurePosixPath(path)
    if (relative.is_absolute() or not relative.parts or ".." in relative.parts
            or relative.as_posix() != path or "\\" in path or PureWindowsPath(path).drive):
        raise ValueError(f"Inventory group map requires a canonical project-relative path: {path}")
    return path


def _map_list(value, label):
    if not isinstance(value, list):
        raise ValueError(f"Inventory group map {label} must be an array")
    return value


def _bounds(ranges):
    spans = []
    for span in _map_list(ranges, "ranges"):
        if not isinstance(span, dict) or set(span) != set(_RANGE_KEYS):
            raise ValueError("Inventory group map ranges require both inclusive line intervals")
        start, end, other_start, other_end = (span[key] for key in _RANGE_KEYS)
        if (any(type(number) is not int for number in (start, end, other_start, other_end))
                or not (1 <= start <= end and 1 <= other_start <= other_end)):
            raise ValueError(f"Inventory group map has invalid inclusive line ranges: {span}")
        spans.append(dict(zip(_RANGE_KEYS, (start, end, other_start, other_end))))
    if not spans:
        raise ValueError("Inventory group map shared_ranges requires at least one pair of line intervals")
    return sorted(spans, key=lambda span: tuple(span[key] for key in _RANGE_KEYS))


def _proof_groups(group_map):
    if group_map is None:
        return []
    if (not isinstance(group_map, dict) or set(group_map) != {"schema_version", "groups"}
            or type(group_map["schema_version"]) is not int or group_map["schema_version"] != 1):
        raise ValueError("Inventory group map requires schema_version 1 and groups")
    group_ids, mapped_paths = set(), set()
    groups = []
    for group in _map_list(group_map["groups"], "groups"):
        if (not isinstance(group, dict) or not {"id", "members"} <= group.keys()
                or group.keys() - {"id", "members", "shared_ranges"}):
            raise ValueError("Inventory group map groups require id and members")
        group_id = _nonempty(group["id"], "group id")
        if group_id in group_ids:
            raise ValueError(f"Duplicate inventory group map id: {group_id}")
        group_ids.add(group_id)
        members = {}
        for member in _map_list(group["members"], "members"):
            if not isinstance(member, dict) or set(member) != {"path", "revision", "role"}:
                raise ValueError("Inventory group map members require path, revision, and role")
            path = _path(member["path"])
            revision = _nonempty(member["revision"], "revision")
            if not _REVISION.fullmatch(revision):
                raise ValueError(f"Inventory group map revision must be a lowercase SHA-256: {path}")
            if path in mapped_paths:
                raise ValueError(f"Inventory group map lists a path more than once: {path}")
            mapped_paths.add(path)
            members[path] = (revision, _nonempty(member["role"], "role"))
        if not members:
            raise ValueError(f"Inventory group map group has no members: {group_id}")
        shared = []
        for proof in _map_list(group.get("shared_ranges", []), "shared_ranges"):
            if not isinstance(proof, dict) or set(proof) != {"path", "representative", "ranges", "evidence"}:
                raise ValueError("Inventory group map shared_ranges requires path, representative, ranges, and evidence")
            path, representative = _path(proof["path"]), _path(proof["representative"])
            if path == representative or not {path, representative} <= members.keys():
                raise ValueError(f"Inventory group map shared range must link distinct members of {group_id}")
            shared.append({"path": path, "representative": representative,
                           "ranges": _bounds(proof["ranges"]),
                           "evidence": _nonempty(proof["evidence"], "evidence")})
        groups.append((group_id, members, shared))
    return groups


def _role(row):
    if row.get("codex_threads"):
        return "codex_capture" if row["kind"] == "text" else "codex_attachment"
    return f"{row['kind']}:{PurePosixPath(row['path']).suffix.lower()}"


def _content_key(row, role):
    if row["status"] != "available":
        return None
    return row["kind"], role, row["private"], row["size"], row["revision"]


def _digest(*parts):
    return sha256("\0".join(map(str, parts)).encode("utf-8")).hexdigest()


def _reviewed_ranges(proof, observed):
    path, representative = proof["path"], proof["representative"]
    left, right = observed[path], observed[representative]
    if left["private"] != right["private"]:
        return "different_privacy"
    if left["status"] != "available" or right["status"] != "available":
        return "range_source_unavailable"
    if left["kind"] != "text" or right["kind"] != "text":
        return "range_source_not_text"
    if any(span["end_line"] > left["line_count"]
           or span["representative_end_line"] > right["line_count"] for span in proof["ranges"]):
        return "range_outside_source"
    return None


def _build_group(group_id, kind, paths, roles, observed, shared):
    members = [{"path": path, "role": roles[path]} for path in sorted(paths)]
    reviewed = {path for proof in shared for path in (proof["path"], proof["representative"])}
    representatives, seen, exact = [], {}, []
    for member in members:
        path, role = member["path"], member["role"]
        key = _content_key(observed[path], role)
        if observed[path]["status"] != "available":
            continue
        if key in seen and path not in reviewed:
            exact.append({"path": path, "representative": seen[key],
                          "proof": "same_bytes", "ranges": []})
        else:
            seen.setdefault(key, path)
            representatives.append(path)
    aliases = sorted([*exact, *shared], key=lambda proof: (
        proof["path"], proof["representative"], proof["proof"],
        [tuple(span[key] for key in _RANGE_KEYS) for span in proof["ranges"]],
        proof.get("evidence", "")))
    return {"id": group_id, "kind": kind, "private": observed[members[0]["path"]]["private"],
            "paths": [member["path"] for member in members],
            "members": members, "representatives": representatives,
            "aliases": aliases}


def group_sources(config, rows, group_map=None) -> dict:
    """Return a partition and read hints, without changing any source status.

    The caller's inventory supplies canonical paths, raw-byte SHA-256, line
    counts for readable text, and any thread IDs verified by Codex custody.
    The optional map records externally reviewed groups and shared ranges. The
    program checks their pins and scope. It does not establish semantic equivalence.
    """
    observed = {row["path"]: row for row in rows}
    if len(observed) != len(rows):
        raise ValueError("Inventory grouping requires one row per observed path")
    roles = {path: _role(row) for path, row in observed.items()}
    groups, gaps, assigned, invalid = [], [], set(), set()
    for group_id, members, shared in _proof_groups(group_map):
        matching = set()
        for path, (revision, role) in sorted(members.items()):
            row = observed.get(path)
            if row is None or row["revision"] is None:
                gaps.append({"group": group_id, "path": path, "reason": "unobserved_revision",
                             "expected_revision": revision})
                invalid.add(path)
            elif row["revision"] != revision:
                gaps.append({"group": group_id, "path": path, "reason": "revision_changed",
                             "expected_revision": revision, "observed_revision": row["revision"]})
                invalid.add(path)
            else:
                matching.add(path)
                roles[path] = role
        proven = defaultdict(list)
        for proof in shared:
            path, representative = proof["path"], proof["representative"]
            if not {path, representative} <= matching:
                continue
            issue = _reviewed_ranges(proof, observed)
            if issue:
                gaps.append({"group": group_id, "path": path, "representative": representative,
                             "reason": issue})
            else:
                proven[observed[path]["private"]].append({**proof, "proof": "reviewed_ranges"})
        for private in (False, True):
            paths = [path for path in matching if observed[path]["private"] == private]
            if paths:
                scope = "private" if private else "public"
                groups.append(_build_group(f"map:{scope}:{group_id}", "mapped", paths,
                                           roles, observed, proven[private]))
        assigned.update(matching)

    candidates = defaultdict(list)
    for path, row in observed.items():
        if path in assigned:
            continue
        threads = row.get("codex_threads", [])
        content = _content_key(row, roles[path])
        if path not in invalid and len(threads) == 1:
            scope = "private" if row["private"] else "public"
            key = (f"codex:{scope}:{threads[0]}", "chat")
        elif path not in invalid and not threads and content is not None:
            key = ("content:" + _digest(*content), "content")
        else:
            key = ("path:" + _digest(path), "single")
        candidates[key].append(path)
    for (group_id, kind), paths in candidates.items():
        if kind == "content" and len(paths) == 1:
            group_id, kind = "path:" + _digest(paths[0]), "single"
        groups.append(_build_group(group_id, kind, paths, roles, observed, []))
    return {"groups": sorted(groups, key=lambda group: group["id"]),
            "grouping_gaps": sorted(gaps, key=lambda gap: (gap["group"], gap["path"], gap["reason"],
                                                          gap.get("representative", "")))}
