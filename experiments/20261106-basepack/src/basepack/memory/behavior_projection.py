"""Replayable access projection in a fixed, immutable behavior space."""

from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from uuid import uuid4

from .behavior_model import influence_bounds, mass_score, train_model
from .maintenance import _locked
from .store import _record, _sql

EPSILON = 0.001
BETA = 0.2
STRENGTH = 8.0


def _key(item):
    target = _record(item["id"])
    if isinstance(target.key, str):
        key = target.key.replace("\\", "\\\\").replace("⟩", "\\⟩")
        logical = f"{target.table}:⟨{key}⟩"
    else:
        logical = f"{target.table}:{target.key}"
    return logical, item["knowledge_revision"]


def _version_id(generation, item):
    target, revision = _key(item)
    digest = sha256((generation + "\n" + target + "\n" + revision).encode()).hexdigest()
    return _sql(_record("behavior_version:" + digest))


def _mass_id(generation, logical):
    digest = sha256((generation + "\n" + logical).encode()).hexdigest()
    return _sql(_record("behavior_mass:" + digest))


def _artifact(memory, model):
    data = json.dumps(model, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = sha256(data).hexdigest()
    directory = memory.config.memory_dir / "behavior"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (digest + ".json")
    if not path.exists():
        temp = directory / (uuid4().hex + ".tmp")
        temp.write_bytes(data)
        temp.replace(path)
    return digest


def _load(memory, metadata):
    digest = metadata["artifact"]
    data = (memory.config.memory_dir / "behavior" / (digest + ".json")).read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Behavior model artifact hash mismatch")
    return json.loads(data)


def _snapshot(memory, *, full=False, logicals=(), read_facts=True):
    # Bind the cutoff inside the snapshot so SurrealDB can use the range indexes.
    bind_cutoff = "LET $compiled_j = (meta:behavior.j ?? 0); " if read_facts and not full else ""
    projection_filter = "" if full else " WHERE id=type::record('behavior_projection', meta:behavior.active)"
    state_filter = " WHERE false" if not logicals else (
        " WHERE generation=meta:behavior.active AND target IN " + _sql(list(logicals)))
    mass_filter = " WHERE generation=meta:behavior.active"
    version_filter = "" if full else " WHERE j_enter >= $compiled_j"
    event_filter = "" if full else " WHERE j > $compiled_j"
    if not read_facts:
        version_filter = event_filter = " WHERE false"
    rows = memory._execute(f"BEGIN; {bind_cutoff}SELECT * FROM ONLY meta:behavior; SELECT * FROM ONLY meta:delivery; "
                           f"SELECT * FROM behavior_projection{projection_filter}; "
                           f"SELECT * FROM behavior_version{state_filter}; "
                           f"SELECT * FROM behavior_mass{mass_filter}; "
                           "SELECT target,knowledge_revision,j_enter,observed_j,age_origin FROM knowledge_version"
                           f"{version_filter}; SELECT * FROM delivery{event_filter}; COMMIT;")
    return rows[-8:-1]


def _j(head):
    return (head or {}).get("j", 0)


def _baseline(model, h, r, c, item, hits=0):
    logical, revision = _key(item)
    return {"target": logical, "knowledge_revision": revision, "tau": c,
            "b": mass_score(model, logical, h, model["beta"]) if logical in model["vectors"] else 0.0,
            "r": r, "hits": hits}


def _step(model, h, r, c, states, event):
    if not event["items"]:
        return r, c
    c += 1
    context = event.get("context")
    anchors = context["anchors"] if context is not None else []
    known = 0.0
    for anchor in anchors:
        logical = _key(anchor)[0]
        if logical in model["vectors"]:
            alpha = anchor["alpha"]
            h[logical] = h.get(logical, 0.0) + alpha
            known += alpha
    r += 1.0 - known
    for item in event["items"]:
        key = _key(item)
        previous = states.get(key)
        states[key] = _baseline(model, h, r, c, item, (previous["hits"] if previous else 0) + 1)
    return r, c


def _replay(model, versions, events):
    """Build from old nonempty facts, then ordered new facts and acceptance heads."""
    h, r, c, states = {}, 0.0, 0, {}
    legacy = sorted((e for e in events if e.get("legacy")), key=lambda e: e["legacy_event"])
    for event in legacy:
        r, c = _step(model, h, r, c, states, event)
    def accept(j):
        for version in versions:
            enter = version.get("j_enter")
            origin = version.get("observed_j") if enter is None else enter
            if origin == j:
                item = {"id": version["target"], "knowledge_revision": version["knowledge_revision"]}
                key = _key(item)
                if key not in states:
                    states[key] = _baseline(model, h, r, c, item)
                    states[key]["age_origin"] = version.get("age_origin") or "acceptance"
    accept(0)
    for event in sorted((e for e in events if not e.get("legacy")), key=lambda e: e["j"]):
        r, c = _step(model, h, r, c, states, event)
        accept(event["j"])
    return h, r, c, states


def _persist(memory, generation, model_id, model, j, h, r, c, states, expected):
    projection = _sql(_record("behavior_projection:" + generation))
    statements = ["BEGIN;",
        f"IF (meta:behavior.active ?? NULL) != {_sql(expected)} {{ THROW 'Behavior projection changed'; }};",
        f"IF (meta:delivery.j ?? 0) != {j} {{ THROW 'Delivery head changed during replay'; }};",
        f"CREATE {projection} CONTENT {_sql({'model': model_id, 'j': j, 'c': c, 'r': r})};"]
    for logical, mass in h.items():
        statements.append(f"CREATE {_mass_id(generation, logical)} CONTENT "
                          f"{_sql({'generation': generation, 'logical': logical, 'mass': mass})};")
    for state in states.values():
        item = {"id": state["target"], "knowledge_revision": state["knowledge_revision"]}
        statements.append(f"CREATE {_version_id(generation, item)} CONTENT {_sql({**state, 'generation': generation})};")
    statements += [f"UPSERT meta:behavior SET active={_sql(generation)}, j={j};", "COMMIT;"]
    memory._publish(statements)


def train_behavior(memory, rank=8, epsilon=EPSILON, beta=BETA, strength=STRENGTH):
    if not (isfinite(epsilon) and 0 < epsilon < 1 and isfinite(beta) and beta > 0
            and isfinite(strength) and strength > 0):
        raise ValueError("Behavior parameters require 0 < epsilon < 1 and positive beta and strength")
    with _locked(memory.config.memory_dir / "behavior.lock", timeout=30):
        active, head, projections, _, _, versions, events = _snapshot(memory, full=True)
        j = _j(head)
        baskets = [sorted({_key(item)[0] for item in event["items"]}) for event in events]
        model = train_model(baskets, rank=rank)
        training_bytes = json.dumps(sorted(baskets), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        model["training_input_sha256"] = sha256(training_bytes).hexdigest()
        legacy = [{"event": event["legacy_event"], "items": event["items"]}
                  for event in events if event.get("legacy")]
        legacy.sort(key=lambda event: (event["event"], json.dumps(event["items"], sort_keys=True)))
        model["legacy_input_sha256"] = sha256(json.dumps(legacy, ensure_ascii=False, sort_keys=True,
                                                        separators=(",", ":")).encode("utf-8")).hexdigest()
        model.update({"epsilon": float(epsilon), "beta": float(beta), "strength": float(strength),
                      "training_j": j, "anchor_rule": "deduplicated_equal_shares"})
        model_id = _artifact(memory, model)
        metadata = _sql(_record("behavior_model:" + model_id))
        memory._execute(f"UPSERT {metadata} CONTENT {_sql({'artifact': model_id, 'training_j': j})};")
        h, r, c, states = _replay(model, versions, events)
        generation = uuid4().hex
        _persist(memory, generation, model_id, model, j, h, r, c, states,
                 (active or {}).get("active"))
        return {"model": model_id, "compiled_j": j, "c": c, "training": model["training"]}


def compile_behavior(memory):
    """Advance only uncompiled facts in the current model, with an optimistic commit."""
    with _locked(memory.config.memory_dir / "behavior.lock", timeout=30):
        active, head, projections, rows, masses, versions, events = _snapshot(memory)
        if not active or not active.get("active"):
            return {"status": "cold_start", "fact_j": _j(head), "compiled_j": None}
        generation = active["active"]
        projection = next(row for row in projections if _record(row["id"]) == _record("behavior_projection:" + generation))
        metadata = memory._execute(f"SELECT * FROM ONLY {_sql(_record('behavior_model:' + projection['model']))};")[0]
        model = _load(memory, metadata)
        old_j, j = projection["j"], _j(head)
        h = {row["logical"]: row["mass"] for row in masses}
        initial_h = dict(h)
        r, c = projection["r"], projection["c"]
        relevant = {_key({"id": version["target"], "knowledge_revision": version["knowledge_revision"]})
                    for version in versions}
        relevant.update(_key(item) for event in events for item in event["items"])
        ref = _sql(_record("behavior_projection:" + generation))
        statements = ["BEGIN;", f"IF meta:behavior.active != {_sql(generation)} OR {ref}.j != {old_j} "
                      "{ THROW 'Behavior projection changed'; };"]
        statements.extend(f"SELECT * FROM ONLY {_version_id(generation, {'id': key[0], 'knowledge_revision': key[1]})};"
                          for key in sorted(relevant))
        statements.append("COMMIT;")
        rows = memory._execute("\n".join(statements))[2:-1]
        states = {(row["target"], row["knowledge_revision"]):
                  {k: v for k, v in row.items() if k not in {"id", "generation"}}
                  for row in rows if row is not None}
        initial = {key: dict(value) for key, value in states.items()}
        def accept(head_j):
            for version in versions:
                if version.get("j_enter") != head_j:
                    continue
                item = {"id": version["target"], "knowledge_revision": version["knowledge_revision"]}
                key = _key(item)
                if key not in states:
                    states[key] = _baseline(model, h, r, c, item)
                    states[key]["age_origin"] = "acceptance"
        accept(old_j)
        pending = sorted((event for event in events if event.get("j") is not None and old_j < event["j"] <= j),
                         key=lambda event: event["j"])
        if [event["j"] for event in pending] != list(range(old_j + 1, j + 1)):
            raise ValueError("Delivery facts have a gap in the strict cursor")
        for event in pending:
            r, c = _step(model, h, r, c, states, event)
            accept(event["j"])
        ref = _sql(_record("behavior_projection:" + generation))
        statements = ["BEGIN;", f"IF meta:behavior.active != {_sql(generation)} OR {ref}.j != {old_j} "
                      "{ THROW 'Behavior projection changed'; };"]
        for logical, mass in h.items():
            if initial_h.get(logical) != mass:
                statements.append(f"UPSERT {_mass_id(generation, logical)} CONTENT "
                                  f"{_sql({'generation': generation, 'logical': logical, 'mass': mass})};")
        for key, state in states.items():
            if initial.get(key) != state:
                item = {"id": state["target"], "knowledge_revision": state["knowledge_revision"]}
                statements.append(f"UPSERT {_version_id(generation, item)} CONTENT "
                                  f"{_sql({**state, 'generation': generation})};")
        statements += [f"UPDATE {ref} SET j={j},c={c},r={r};",
                       f"UPDATE meta:behavior SET j={j};", "COMMIT;"]
        memory._publish(statements)
        return {"status": "ready", "model": projection["model"], "fact_j": j, "compiled_j": j, "c": c}


def access_hints(memory, items):
    if not items:
        return []
    active, head, projections, versions, masses, retained, _ = _snapshot(
        memory, logicals={_key(item)[0] for item in items}, read_facts=False)
    fact_j = _j(head)
    if not active or not active.get("active"):
        return [{**item, "access_interval": [0.0, 1.0], "access_hits": None, "access_prior": None,
                 "access_support": None, "access_model": None, "access_compiled_j": None,
                 "access_fact_j": fact_j, "access_status": "cold_start"} for item in items]
    generation = active["active"]
    projection = next(row for row in projections if _record(row["id"]) == _record("behavior_projection:" + generation))
    metadata = memory._execute(f"SELECT * FROM ONLY {_sql(_record('behavior_model:' + projection['model']))};")[0]
    model = _load(memory, metadata)
    states = {(row["target"], row["knowledge_revision"]): row for row in versions if row["generation"] == generation}
    h = {row["logical"]: row["mass"] for row in masses}
    result = []
    for item in items:
        logical, revision = _key(item)
        state = states.get((logical, revision))
        if state is None:
            result.append({**item, "access_interval": [0.0, 1.0], "access_hits": None,
                           "access_prior": None, "access_support": model["support"].get(logical, 0),
                           "access_model": projection["model"], "access_compiled_j": projection["j"],
                           "access_fact_j": fact_j, "access_status": "pending"})
            continue
        n = projection["c"] - state["tau"]
        strength = model["strength"] * (1 + state["hits"])
        if logical in model["vectors"]:
            lo = model["epsilon"] * n + (1-model["epsilon"]) * (
                mass_score(model, logical, h, model["beta"]) - state["b"])
            hi = lo + (1-model["epsilon"]) * (projection["r"] - state["r"])
        else:
            lo, hi = model["epsilon"] * n, n
        if min(lo, hi) < -1e-9 or hi + 1e-9 < lo:
            raise ValueError("Invalid access projection age")
        lo, hi = max(0.0, lo), max(0.0, hi)
        result.append({**item, "access_interval": [strength/(strength+hi), strength/(strength+lo)],
                       "access_hits": state["hits"], "access_prior": state["hits"] == 0,
                       "access_support": model["support"].get(logical, 0), "access_model": projection["model"],
                       "access_compiled_j": projection["j"], "access_fact_j": fact_j,
                       "access_status": "ready" if projection["j"] == fact_j else "lagging",
                       "access_age_origin": state.get("age_origin", "hit")})
    return result


def behavior_candidates(memory, anchors, limit=20, scope="", *, allow_private=True):
    from .dialogue_query import graph_dialogue_test, legacy_path_tests
    from .graph_query_store import visible_edge_records

    active, _, projections, _, _, _, _ = _snapshot(memory, read_facts=False)
    if not active or not active.get("active"):
        return {"model": None, "candidates": []}
    projection = next(row for row in projections if _record(row["id"]) == _record("behavior_projection:" + active["active"]))
    metadata = memory._execute(f"SELECT * FROM ONLY {_sql(_record('behavior_model:' + projection['model']))};")[0]
    model = _load(memory, metadata)
    shares = {_key(a)[0]: a["alpha"] for a in anchors}
    if not any(key in model["vectors"] for key in shares):
        return {"model": projection["model"], "candidates": []}
    if limit <= 0:
        return {"model": projection["model"], "candidates": []}
    scored = [(influence_bounds(model, logical, shares, model["beta"]), logical)
              for logical in model["vectors"]]
    scored.sort(key=lambda pair: (-pair[0][0], pair[1]))
    visible = [graph_dialogue_test(memory, "", scope, allow_private), *legacy_path_tests(memory, "path")]
    if not allow_private:
        visible.append("private=false")
    visible_edges = "" if allow_private else " WHERE head.private=false"
    objects, relations = memory._execute(
        "SELECT id,knowledge_revision,stale,retired,path FROM member,node "
        f"WHERE {' AND '.join(visible)}; "
        f"SELECT id,head AS exact_id,knowledge_revision,stale,retired FROM semantic{visible_edges};")
    rows = objects + visible_edge_records(memory, relations, scope=scope, allow_private=allow_private)
    current = {_key(row)[0]: row for row in rows if row.get("knowledge_revision")}
    candidates = []
    for interval, logical in scored:
        row = current.get(logical)
        if row and not row.get("stale") and not row.get("retired") and (not scope or (row.get("path") or "").startswith(scope)):
            candidates.append({"id": row["id"], "knowledge_revision": row["knowledge_revision"],
                               "behavior_similarity_interval": list(interval)})
            if len(candidates) >= limit:
                break
    return {"model": projection["model"], "candidates": candidates}
