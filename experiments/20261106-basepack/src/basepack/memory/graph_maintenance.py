"""Suggest bounded co-reads of exact accepted member versions."""

from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import json
from random import Random

from .store import _record, _sql


_DELIVERY_WINDOW = 256
_BASKET_LIMIT = 12
_MIN_DELIVERIES = 2
_RANDOM_ATTEMPTS = 64


def _pair(left, right):
    return tuple(sorted((left, right), key=_sql))


def _pair_id(pair, endpoints):
    versions = [[_sql(record), endpoints[record]["knowledge_revision"],
                 _sql(_record(endpoints[record]["source_version"], "source_version"))] for record in pair]
    return "pair:" + sha256(json.dumps(versions, separators=(",", ":")).encode("utf-8")).hexdigest()


def _current_endpoints(members, sources):
    endpoints = {}
    for member in members:
        if member.get("stale") is not False or member.get("retired"):
            continue
        if not member.get("knowledge_revision") or not member.get("source_version"):
            continue
        if member["path"] not in sources:
            continue
        source = sources[member["path"]]
        if (member.get("source_revision") != source["revision"]
                or _record(member["source_version"], "source_version") != _record(source["version"], "source_version")):
            continue
        identity = _record(member["id"])
        endpoint_fields = ("id", "knowledge_revision", "path", "source_version", "source_revision", "kind",
                           "start_line", "end_line", "locator")
        endpoint = {field: member[field] for field in endpoint_fields if field in member}
        private = True if source.get("private") is True else member.get("private")
        if type(private) is bool:
            endpoint["private"] = private
        endpoints[identity] = endpoint
    return endpoints


def _delivery_support(memory, endpoints):
    events = memory._execute("SELECT j,items FROM delivery WHERE j >= 1 AND legacy != true "
                             f"ORDER BY j DESC LIMIT {_DELIVERY_WINDOW};")[0]
    support = defaultdict(set)
    for event in events:
        basket = set()
        for item in event["items"]:
            identity = _record(item["id"])
            row = endpoints.get(identity)
            if row and item["knowledge_revision"] == row["knowledge_revision"]:
                basket.add(identity)
        for pair in combinations(sorted(basket, key=_sql)[:_BASKET_LIMIT], 2):
            support[pair].add(event["j"])
    return support


def _random_pair(endpoints, signals, available, seed):
    by_original = defaultdict(list)
    for identity in sorted(endpoints, key=_sql):
        by_original[endpoints[identity]["source_revision"]].append(identity)
    groups = [by_original[digest] for digest in sorted(by_original)]
    rng = Random(seed)
    for _ in range(_RANDOM_ATTEMPTS):
        first, second = rng.sample(groups, 2)
        pair = _pair(rng.choice(first), rng.choice(second))
        if pair not in signals and available(pair):
            return pair
    return None


def nominate(memory, *, members, eligible_sources, reviewed=(), limit=4):
    """Return bounded, project-local clues; nomination never creates a relation."""
    if type(limit) is not int or limit < 0:
        raise ValueError("Graph nomination limit must be a nonnegative integer")
    if not limit:
        return []
    endpoints = _current_endpoints(members, eligible_sources)
    if len({endpoint["source_revision"] for endpoint in endpoints.values()}) < 2:
        return []
    reviewed = set(reviewed)

    def available(pair):
        left, right = (endpoints[record] for record in pair)
        return (left["path"] != right["path"] and left["source_revision"] != right["source_revision"]
                and (not reviewed or _pair_id(pair, endpoints) not in reviewed))

    support = _delivery_support(memory, endpoints)
    shared = {pair for pair, events in support.items() if len(events) >= _MIN_DELIVERIES}
    ranked = sorted((pair for pair in shared if available(pair)),
                    key=lambda pair: (-len(support[pair]), tuple(map(_sql, pair))))

    # Give a small unbiased co-read a seat while retaining the strongest clue when budget is one.
    random_pair = _random_pair(endpoints, shared, available, len(reviewed)) if limit > 1 or not ranked else None
    selected = [{"id": _pair_id(pair, endpoints), "endpoints": [endpoints[record] for record in pair],
                 "signals": ["co_delivery"], "delivery_events": sorted(support[pair])}
                for pair in ranked[:limit - bool(random_pair)]]
    if random_pair:
        selected.append({"id": _pair_id(random_pair, endpoints),
                         "endpoints": [endpoints[record] for record in random_pair], "signals": ["random"]})
    return selected
