"""Run one bounded, version-pinned graph query."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass

from . import graph_query_store as graph
from .query import normalize_scope
from .relation_contract import EDGE_TYPES


MAX_SEEDS = 4
MAX_HOPS = 2
MAX_ADJACENCY = 12
MAX_SCANNED = 96
MAX_CANDIDATES = 12
MAX_PATHS = 3
TYPES = tuple(sorted(EDGE_TYPES))
PROTECTED = (
    ("out", "has_basis", 2), ("out", "from_snapshot", 1), ("in", "supersedes", 2),
    ("in", "contradicts", 2), ("in", "supports", 1), ("out", "version_of", 1),
)
ACCESS_FIELDS = ("access_model", "access_compiled_j", "access_fact_j", "access_interval", "access_status")
LOCATOR_FIELDS = ("start_line", "end_line", "locator")
ITEM_FIELDS = (
    "id", "exact_id", "knowledge_revision", "record_type", "kind", "type", "title", "text", "label", "private",
    "path", "revision", "source_revision", "source_version", *LOCATOR_FIELDS, "conditions", "status",
)
EDGE_FIELDS = ("id", "in", "out", "type", "conditions", "label", "locator", "private", "status")
_RECORD_MENTION = re.compile(r"(?<![\w:])(?:member|node|semantic|source|knowledge_version|source_version|graph_edge):(?:⟨[^⟩]+⟩|`[^`]+`|[A-Za-z0-9_-]+)")
_CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def parse_branch(value):
    direction, _, kind = value.partition(":")
    if direction not in {"in", "out"} or kind not in TYPES:
        raise ValueError(f"Expected in:TYPE or out:TYPE with a published edge type: {value!r}")
    return direction, kind


def base_search(memory, text, *, scope, allow_private, literal=False, access=True):
    """Use the configured text/vector entrance with an explicit visibility scope."""
    options = {"scope": scope, "limit": MAX_CANDIDATES, "allow_private": allow_private, "access": access}
    if memory.config.memory_search_mode == "vector":
        if literal:
            raise ValueError("Literal search requires hybrid memory search mode")
        return memory.vector_search(text, **options)
    return memory.hybrid_search(text, literal=literal, **options)


def _words(text):
    def split_cjk(match):
        run = match[0]
        return " ".join(run[index:index + 2] for index in range(max(1, len(run) - 1)))

    return set(re.findall(r"\w+", _CJK_RUN.sub(split_cjk, text.casefold())))


def _matches(terms, *values):
    if not terms:
        return 0.0
    return len(terms & _words(" ".join(value for value in values if isinstance(value, str)))) / len(terms)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class Route:
    index: int
    vertices: tuple
    edges: tuple = ()

    @property
    def role(self):
        for _, kind, _ in PROTECTED:
            if any(edge["type"] == kind for edge in self.edges):
                return kind
        return self.edges[-1]["type"] if self.edges else "seed"

    @property
    def roles(self):
        return (edge["type"] for edge in self.edges) if self.edges else ("seed",)

    @property
    def key(self):
        return tuple((edge["type"], edge["direction"], _json(edge.get("conditions")),
                      _json(edge.get("locator")), edge.get("via_edge", False)) for edge in self.edges)

    def extend(self, endpoint, step):
        return Route(self.index, (*self.vertices, endpoint), (*self.edges, step))


def _route_priority(route):
    roles = [kind for _, kind, _ in PROTECTED]
    priority = roles.index(route.role) if route.role in roles else len(roles)
    return priority, len(route.edges), route.index, tuple(edge["id"] for edge in route.edges)


def _add_route(routes, route):
    before = routes.get(route.key)
    if before is None or _route_priority(route) < _route_priority(before):
        routes[route.key] = route


def _branches(vertex, requested):
    if requested:
        protected = {kind for _, kind, _ in PROTECTED}
        groups = [(direction, (kind,)) for direction, kind in requested if kind in protected]
        for direction in dict.fromkeys(direction for direction, _ in requested):
            kinds = tuple(kind for way, kind in requested if way == direction and kind not in protected)
            if kinds:
                groups.append((direction, kinds))
        for index, (direction, kinds) in enumerate(groups):
            yield direction, kinds, lambda remaining, count=len(groups) - index: remaining // count
        return
    if vertex.get("identity"):
        yield "in", ("version_of",), lambda remaining: remaining
        return
    if vertex["record_type"] == "source_version":
        return
    for direction, kind, quota in PROTECTED:
        if kind != "from_snapshot" or vertex["record_type"] == "member":
            yield direction, (kind,), lambda remaining, cap=quota: min(remaining, cap)
    for direction, groups in (("out", 2), ("in", 1)):
        excluded = {kind for way, kind, _ in PROTECTED if way == direction}
        excluded.update({"version_of", "from_snapshot"})
        yield direction, tuple(kind for kind in TYPES if kind not in excluded), lambda remaining, count=groups: remaining // count


def _short_item(vertex):
    item = {field: vertex[field] for field in ITEM_FIELDS if field in vertex}
    text = item.get("text")
    if text is not None and len(text) > 240:
        item.update(text=text[:240], text_truncated=True)
    return item


def _at_position(vertex, edge):
    if vertex["record_type"] != "source_version" or not edge or not edge.get("locator"):
        return vertex
    return {**vertex, **{key: edge["locator"][key] for key in LOCATOR_FIELDS if key in edge["locator"]}}


def graph_query(memory, text="", *, seeds=(), branches=(), scope="", allow_private=False, include_stale=False,
                literal=False, conditions=None, base=None):
    """Traverse visible native relations and rank a single bounded window."""
    scope = normalize_scope(scope)
    if not isinstance(text, str) or not (text.strip() or seeds):
        raise ValueError("Provide query text or at least one graph seed")
    if conditions is not None and not isinstance(conditions, dict):
        raise ValueError("conditions must be a JSON object")
    requested = tuple(dict.fromkeys(parse_branch(branch) for branch in branches))
    visibility = {"scope": scope, "allow_private": allow_private}
    vertices = {}
    seed_rows = []
    seed_ids = set()
    named_truncated = False
    terms = _words(text)

    def vertex(exact):
        if exact not in vertices:
            row = graph.get_vertex(memory, exact, **visibility)
            if row is not None and not include_stale and row.get("status") in {"needs_review", "retired"}:
                row = None
            vertices[exact] = row
        return vertices[exact]

    def add_seed(identifier, revision, origin, rank):
        exact = graph.resolve_seed(memory, identifier, knowledge_revision=revision)
        if exact is None or exact in seed_ids or vertex(exact) is None:
            return False
        if len(seed_rows) == MAX_SEEDS:
            return True
        seed_ids.add(exact)
        seed_rows.append({**_short_item(vertex(exact)), "origin": origin, "input_rank": rank})
        return False

    named = [*seeds, *_RECORD_MENTION.findall(text)]
    for entry in named:
        identifier, revision = (entry, None) if isinstance(entry, str) else (entry["id"], entry["knowledge_revision"])
        if add_seed(identifier, revision, "named", len(seed_rows)):
            named_truncated = True
            break
    named_count = len(seed_rows)
    search_coverage = None
    if len(seed_rows) < MAX_SEEDS and text.strip():
        if base is None:
            base = base_search(memory, text, scope=scope, allow_private=allow_private, literal=literal, access=False)
        search_coverage = base["vector_coverage"]
        for index, row in enumerate(base["matches"]):
            add_seed(row["id"], row["knowledge_revision"], "base", index)
            if len(seed_rows) == MAX_SEEDS:
                break

    candidates = {}
    frontier = defaultdict(dict)
    truncation = {}
    adjacency = {}
    scanned = 0

    def truncate(reason, start=None, *, direction=None, kinds=(), cap=None):
        key = (reason, direction, kinds, cap)
        note = truncation.setdefault(key, {"limit": reason, "cap": cap, "affected": 0, "seeds": []})
        if direction:
            note.update(direction=direction, types=list(kinds))
        note["affected"] += 1
        if start and start not in note["seeds"] and len(note["seeds"]) < MAX_SEEDS:
            note["seeds"].append(start)

    def consider(exact, route, pending):
        step = route.edges[-1] if route.edges else None
        if step and step["type"] == "version_of" and exact == step["out"] and exact not in vertices:
            vertices[exact] = {"id": exact, "exact_id": exact, "record_type": exact.partition(":")[0],
                               "identity": True, "private": step["private"]}
        current = vertex(exact)
        if current is None:
            return False
        if not current.get("identity"):
            item = _at_position(current, step)
            key = (exact, *(_json(item.get(field)) for field in LOCATOR_FIELDS))
            candidate = candidates.setdefault(key, {"item": _short_item(item), "routes": {}})
            _add_route(candidate["routes"], route)
        _add_route(pending[exact], route)
        return True

    def scan_adjacency(exact):
        nonlocal scanned
        steps = []
        per_vertex = 0
        for direction, kinds, quota in _branches(vertex(exact), requested):
            remaining = min(MAX_ADJACENCY - per_vertex, MAX_SCANNED - scanned)
            if not remaining:
                reason = "scanned" if scanned == MAX_SCANNED else "adjacency"
                truncate(reason, exact, direction=direction, kinds=kinds,
                         cap=MAX_SCANNED if reason == "scanned" else MAX_ADJACENCY)
                continue
            take = max(1, quota(remaining))
            edges = graph.adjacent(memory, exact, direction=direction.upper(), types=kinds, limit=take,
                                   include_stale=include_stale, conditions=conditions, **visibility)
            scanned += len(edges)
            per_vertex += len(edges)
            if len(edges) == take:
                truncate("adjacency", exact, direction=direction, kinds=kinds, cap=take)
            for edge in edges:
                if edge["type"] == "other" and not _matches(terms, edge.get("label"), edge.get("text")) and (
                        direction, "other") not in requested:
                    continue
                step = {key: edge[key] for key in EDGE_FIELDS if key in edge}
                step["direction"] = direction
                steps.append((edge, step))
        return steps

    for index, seed in enumerate(seed_rows):
        exact = seed["exact_id"]
        consider(exact, Route(index, (exact,)), frontier)
    if named_truncated:
        truncate("seeds", cap=MAX_SEEDS)
    for _depth in range(MAX_HOPS):
        following = defaultdict(dict)
        for exact, variants in sorted(frontier.items(), key=lambda pair: (min(map(_route_priority, pair[1].values())), pair[0])):
            # Reuse the first bounded scan when a later route reaches an earlier seed.
            if exact not in adjacency:
                adjacency[exact] = scan_adjacency(exact)
            paths = sorted(variants.values(), key=_route_priority)[:MAX_PATHS]
            for edge, step in adjacency[exact]:
                endpoint = edge["neighbor"]
                for path in paths:
                    reachable = endpoint in path.vertices or consider(endpoint, path.extend(endpoint, step), following)
                    if reachable and edge.get("logical_id") and edge["id"] not in path.vertices:
                        consider(edge["id"], path.extend(edge["id"], {**step, "via_edge": True}), following)
        frontier = following
    for exact in sorted(set(frontier) - adjacency.keys()):
        for direction, kinds, _ in _branches(vertex(exact), requested):
            truncate("hops", exact, direction=direction, kinds=kinds, cap=MAX_HOPS)

    result = _rank(memory, candidates.values(), seed_rows, named_count, terms)
    if len(result["observations"]) > len(result["candidates"]):
        truncate("candidates", cap=MAX_CANDIDATES)
        truncation[("candidates", None, (), MAX_CANDIDATES)]["affected"] = (
            len(result["observations"]) - len(result["candidates"]))
    return {**result, "text": text, "scope": scope, "include_private": allow_private, "include_stale": include_stale,
            "conditions": conditions, "branches": list(branches), "seeds": seed_rows, "scanned": scanned,
            "limits": {"seeds": MAX_SEEDS, "hops": MAX_HOPS, "adjacency": MAX_ADJACENCY,
                       "scanned": MAX_SCANNED, "candidates": MAX_CANDIDATES},
            "truncation": list(truncation.values()), "vector_coverage": search_coverage}


def _rank(memory, candidates, seeds, named_count, terms):
    rows = []
    for candidate in candidates:
        item = candidate["item"]
        routes = sorted(candidate["routes"].values(), key=_route_priority)
        # Keep paths from explicitly named starts visible when the result has alternate roots.
        in_view = sorted(routes, key=lambda route: route.index >= named_count)[:MAX_PATHS]
        content = _matches(terms, item.get("title"), item.get("text"), item.get("path"), item.get("label"))
        def path_quality(route):
            seed_quality = 1 / (1 + seeds[route.index]["input_rank"] / 3)
            role = 0.12 if route.role in {"has_basis", "from_snapshot", "supersedes", "contradicts", "supports"} else 0
            return (0.55 * seed_quality + role) / (1 + 0.35 * len(route.edges))

        rows.append({**item, "base_score": round(0.3 * content + max(map(path_quality, routes)), 8),
                     "roles": list(dict.fromkeys(role for path in routes for role in path.roles)),
                     "paths": [{"seed": seeds[path.index]["exact_id"], "edges": list(path.edges)} for path in in_view],
                     "additional_paths": len(routes) - len(in_view),
                     "named_seed": any(not path.edges and path.index < named_count for path in routes)})

    observed = [row for row in rows if "knowledge_revision" in row]
    hints = memory.access_hints(observed) if observed else []
    snapshots = {tuple(row.get(field) for field in ACCESS_FIELDS[:3]) for row in hints}
    if len(snapshots) > 1:
        raise ValueError("Graph initial ranking requires a single access snapshot")
    for row, hint in zip(observed, hints, strict=True):
        row.update({field: hint[field] for field in ACCESS_FIELDS if field in hint})
    for row in rows:
        interval = row.get("access_interval") if row.get("access_model") else None
        adjustment = 0.1 * (sum(interval) / 2 - 0.5) if interval else 0.0
        row["initial_score"] = round(row["base_score"] + adjustment, 8)
    rows.sort(key=lambda row: (-row["initial_score"], row["exact_id"], *(_json(row.get(field)) for field in LOCATOR_FIELDS)))

    selected = [index for index, row in enumerate(rows) if row["named_seed"]]
    for _, kind, _ in PROTECTED:
        if not any(kind in rows[index]["roles"] for index in selected):
            pick = next((index for index, row in enumerate(rows) if kind in row["roles"]), None)
            if pick is not None:
                selected.append(pick)
    keep = set(selected[:MAX_CANDIDATES])
    for index in range(len(rows)):
        if len(keep) == MAX_CANDIDATES:
            break
        keep.add(index)
    snapshot = next(iter(snapshots), None)
    observation_fields = ("id", "knowledge_revision", "exact_id", "record_type", "private", "revision", "path", "status",
                          *LOCATOR_FIELDS, "base_score", "initial_score", "roles", *ACCESS_FIELDS)
    return {"candidates": [row for index, row in enumerate(rows) if index in keep],
            "observations": [{key: row[key] for key in observation_fields if key in row} | {"returned": index in keep}
                             for index, row in enumerate(rows)],
            "access_snapshot": dict(zip(ACCESS_FIELDS[:3], snapshot)) if snapshot is not None else None}
