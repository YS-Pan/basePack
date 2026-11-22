"""Prepare and execute a fixed retrieval request."""

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .prompts import _capacity, _nonnegative, memory_command, render_template


def retrieval_dispatch(config, request_path, slot=0, available_subagents=None, level=None):
    """Describe one complete retrieval delegation, independently of maintenance ownership."""
    slot = _nonnegative(slot, "slot")
    configured, limit = _capacity(config, available_subagents)
    ai = config.resolve_ai(purpose="retrieval", level=level) if limit or level is not None else None
    worker = ai if limit else {"level": None, "model": None, "reasoning_effort": None}
    args = ["retrieval-prompt", "--request", Path(request_path).resolve(), "--slot", slot]
    if available_subagents is not None:
        args.extend(["--available-subagents", available_subagents])
    if level is not None:
        args.extend(["--level", level])
    path = Path(request_path).resolve()
    identity = str(path).encode("utf-8")
    if path.is_file():
        identity += b"\n" + path.read_bytes()
    request_name = sha256(identity).hexdigest()[:20]
    return {"status": "prepared", "started": False,
            "host_action": "Spawn the assigned worker and receive its final result" if limit else
                           "Run the complete retrieval in the main agent; no subagent seat is available",
            "executor": "worker" if limit else "main", "task_name": f"bp_mem_search_{request_name}_{slot}" if limit else None,
            "slot": slot, "configured_subagents": configured, "available_subagents": available_subagents,
            "capacity_status": "verified_available" if available_subagents is not None else "organization_ceiling",
            **worker, "render_command": memory_command(config, *args)}


def _retrieval_request(request_path):
    from .query import load_json_file, normalize_scope

    request = load_json_file(request_path)
    if not isinstance(request["question"], str) or not request["question"].strip():
        raise ValueError("question must be a nonempty string")
    request["scope"] = normalize_scope(request.get("scope", ""))
    request["content_budget"] = request.get("content_budget", 6000)
    if not _nonnegative(request["content_budget"], "content_budget"):
        raise ValueError("content_budget must be positive")
    if not isinstance(request.get("include_private", False), bool):
        raise ValueError("include_private must be a boolean")
    # Existing request files remain read-only and acquire the same identity on every render.
    identity = str(Path(request_path).resolve()) + "\n" + json.dumps(request, sort_keys=True, ensure_ascii=False)
    request.setdefault("delivery_id", "retrieval-" + sha256(identity.encode("utf-8")).hexdigest())
    if not isinstance(request["delivery_id"], str) or not request["delivery_id"].strip():
        raise ValueError("delivery_id must be a nonempty string")
    return request


def prepare_retrieval(config, *, question=None, request_path=None, scope="", budget=6000,
                      slot=0, available_subagents=None, level=None, allow_private=False):
    """Prepare sensible defaults; the host owns actual execution and final receipt."""
    from .query import normalize_scope

    if question is None and request_path is None:
        return {"status": "needs_input", "started": False, "required_input": "question",
                "message": "Provide --question with the business question, or --request to reuse a prepared retrieval."}
    if request_path is None:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a nonempty string")
        scope = normalize_scope(scope)
        if not _nonnegative(budget, "content_budget"):
            raise ValueError("content_budget must be positive")
        # Resolve capacity/model and reject invalid host parameters before creating a request.
        retrieval_dispatch(config, config.root / "tmp/request.json", slot, available_subagents, level)
        work = config.root / "tmp" / "basepack-retrieval" / uuid4().hex
        request_path = work / "request.json"
        work.mkdir(parents=True)
        request_path.write_text(json.dumps({"question": question, "scope": scope, "content_budget": budget,
                                           "include_private": allow_private,
                                           "delivery_id": "retrieval-" + uuid4().hex},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
    request = _retrieval_request(request_path)
    if allow_private and not request.get("include_private", False):
        raise ValueError("This retrieval request does not authorize private results")
    dispatch = retrieval_dispatch(config, request_path, slot, available_subagents, level)
    return {**dispatch, "request": str(Path(request_path).resolve()),
            "delivery_id": request["delivery_id"], "scope": request["scope"],
            "include_private": request.get("include_private", False),
            "content_budget": request["content_budget"],
            "work": str(_retrieval_work(config, request_path, request)),
            "delivery_receipt": str(_retrieval_work(config, request_path, request) / "delivery.json"),
            "delivery_command": memory_command(config, "delivery", "--input",
                                                _retrieval_work(config, request_path, request) / "delivery.json")}


def _retrieval_work(config, request_path, request):
    path = Path(request_path).resolve()
    if path.parent.parent == (config.root / "tmp" / "basepack-retrieval").resolve():
        return path.parent
    identity = str(path) + "\n" + request["delivery_id"]
    return config.root / "tmp" / "basepack-retrieval" / sha256(identity.encode("utf-8")).hexdigest()[:32]


def render_retrieval_prompt(config, request_path, slot=0, available_subagents=None, level=None):
    """Read the retrieval request and template only; never claim or inspect maintenance state."""
    dispatch = retrieval_dispatch(config, request_path, slot, available_subagents, level)
    request = _retrieval_request(request_path)
    work = _retrieval_work(config, request_path, request)
    assignment = (f"retrieval worker {dispatch['task_name']}, assigned level {dispatch['level']} / "
                  f"{dispatch['model']} / {dispatch['reasoning_effort']}" if dispatch["executor"] == "worker"
                  else "main agent performing retrieval directly because no subagent seat is available")
    search = ["search", "--text", "<terms>"]
    start = memory_command(config, "retrieval-start", "--request", Path(request_path).resolve())
    graph_args = ["graph-query", "--request", Path(request_path).resolve()]
    evidence_args = ["--scope", request["scope"]] if request["scope"] else []
    accepted_args = list(evidence_args)
    if request.get("include_private"):
        evidence_args.append("--include-private")
    else:
        search.append("--public-only")
        accepted_args.append("--public-only")
    if request["scope"]:
        search.extend(["--scope", request["scope"]])
    values = {"assignment": assignment, "root": str(config.root), "config": str(config.path),
              "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
              "request": json.dumps(request, ensure_ascii=False), "work": str(work),
              "python": str(config.python), "delivery_id": request["delivery_id"],
              "scope": json.dumps(request["scope"], ensure_ascii=False),
              "search_command": memory_command(config, *search), "start_command": start,
              "graph_command": memory_command(config, *graph_args),
              "graph_followup": memory_command(config, *graph_args, "--text", "<subquestion>"),
              "capture_check_command": memory_command(config, "check-codex-capture"),
              "read_command": memory_command(config, "read", "<member-id>", "--knowledge-revision", "<observed-knowledge-revision>", *accepted_args),
              "read_source_command": memory_command(config, "read-source", "<source_version>", *evidence_args),
              "knowledge_command": memory_command(config, "knowledge", "<record-id>", "--knowledge-revision", "<observed-knowledge-revision>", *accepted_args),
              "neighbors_command": memory_command(config, "neighbors", "<record-id>", "--knowledge-revision", "<observed-knowledge-revision>", *evidence_args),
              "rank_command": memory_command(config, "rank", "--input", work / "scored.json",
                                               "--budget", request["content_budget"], "--output", work / "ranked.json"),
              "receipt_command": memory_command(config, "retrieval-receipt", "--request", Path(request_path).resolve(),
                                                "--ranked", work / "ranked.json", "--candidates", work / "candidates.json",
                                                "--output", work / "delivery.json")}
    return {"prompt": render_template("retrieval", **values), "delivery_id": request["delivery_id"],
            "search_command": values["search_command"], "graph_command": values["graph_command"],
            "work": str(work), "scope": request["scope"], **dispatch}


def start_retrieval(memory, request_path):
    """Freeze the base result before adding behavioral candidates; reuse it for every round."""
    from .behavior_projection import behavior_candidates
    from .graph_query_store import filter_record_details
    from .graph_retrieval import base_search

    request = _retrieval_request(request_path)
    work = _retrieval_work(memory.config, request_path, request)
    anchor_path = work / "anchors.json"
    request_hash = sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if anchor_path.exists():
        frozen = json.loads(anchor_path.read_text(encoding="utf-8"))
        if frozen["request_hash"] != request_hash:
            raise ValueError("Retrieval request changed after its anchors were frozen")
    else:
        mode = memory.config.memory_search_mode
        base = base_search(memory, request["question"], scope=request["scope"],
                           allow_private=request.get("include_private", False))
        unique = {}
        for row in base["matches"]:
            unique.setdefault(row["id"], row)
        rows = list(unique.values())
        anchors = [{"id": row["id"], "knowledge_revision": row["knowledge_revision"],
                    "alpha": 1.0 / len(rows),
                    "base_quality": row["rrf_score"] if "rrf_score" in row else 1.0 - row["distance"],
                    "base_quality_details": {key: row[key] for key in
                                     ("rrf_score", "lexical_score", "lexical_rank", "distance", "vector_rank")
                                     if key in row}} for row in rows]
        frozen = {"request_hash": request_hash, "delivery_id": request["delivery_id"], "query": request["question"],
                  "episode": request["delivery_id"], "anchors": anchors,
                  "knowledge_cutoff": {"kind": "observed_versions",
                      "observed_at": datetime.now(timezone.utc).isoformat(),
                      "versions": [{"id": row["id"], "knowledge_revision": row["knowledge_revision"]}
                                   for row in rows]},
                  "budget": request["content_budget"],
                  "policy": {"anchor": "base-search-logical-id-equal-v1", "mode": mode,
                             "scope": request["scope"], "limit": 12},
                  "base": base}
        work.mkdir(parents=True, exist_ok=True)
        # Exclusive creation makes accidental concurrent reuse visible. A failed write is not retried silently.
        with anchor_path.open("x", encoding="utf-8") as output:
            json.dump(frozen, output, ensure_ascii=False, indent=2)
    candidate_path = work / "behavior.json"
    if candidate_path.exists():
        related = json.loads(candidate_path.read_text(encoding="utf-8"))
    else:
        allow_private = request.get("include_private", False)
        related = behavior_candidates(memory, frozen["anchors"], limit=12, scope=frozen["policy"]["scope"],
                                      allow_private=allow_private)
        observed = []
        for row in related["candidates"]:
            item = memory.knowledge(row["id"])
            if item["knowledge_revision"] != row["knowledge_revision"] or item.get("stale") or item.get("retired"):
                continue
            if not allow_private and item.get("private"):
                continue
            if frozen["policy"]["scope"] and not item.get("path", "").startswith(frozen["policy"]["scope"]):
                continue
            item = filter_record_details(memory, item, scope=frozen["policy"]["scope"], allow_private=allow_private)
            observed.append({**item, "behavior_similarity_interval": row["behavior_similarity_interval"]})
        related["candidates"] = memory.access_hints(observed)
        with candidate_path.open("x", encoding="utf-8") as output:
            json.dump(related, output, ensure_ascii=False, indent=2)
    return {"anchor_file": str(anchor_path), "frozen": frozen, "behavior_candidates": related}


def retrieval_graph_round(memory, request_path, *, text=None, scope=None, allow_private=False, **options):
    """Keep requested query observations beside the fixed anchors for the receipt."""
    from .graph_retrieval import graph_query

    request = _retrieval_request(request_path)
    authorized = request.get("include_private", False)
    if allow_private and not authorized:
        raise ValueError("This retrieval request does not authorize private results")
    effective_scope = request["scope"] if scope is None else scope
    frozen = start_retrieval(memory, request_path)["frozen"]
    use_frozen = text is None and effective_scope == request["scope"] and not options.get("literal")
    text = request["question"] if text is None else text
    result = graph_query(memory, text, scope=effective_scope, allow_private=authorized,
                         base=frozen["base"] if use_frozen else None, **options)
    rounds = _retrieval_work(memory.config, request_path, request) / "graph-rounds"
    rounds.mkdir(exist_ok=True)
    round_id = uuid4().hex
    snapshot = {key: value for key, value in result.items() if key not in {"candidates", "vector_coverage"}}
    snapshot.update(round_id=round_id, observed_at=datetime.now(timezone.utc).isoformat())
    path = rounds / f"{round_id}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(snapshot, output, ensure_ascii=False, indent=2)
    return {**result, "round_id": round_id, "round_file": str(path)}


def make_delivery_receipt(config, request_path, ranked, candidates):
    """Build host-confirmable delivery context from the independent fixed anchor package."""
    request = _retrieval_request(request_path)
    work = _retrieval_work(config, request_path, request)
    frozen = json.loads((work / "anchors.json").read_text(encoding="utf-8"))
    request_hash = sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if frozen["request_hash"] != request_hash:
        raise ValueError("Retrieval request changed after its anchors were frozen")
    behavior = json.loads((work / "behavior.json").read_text(encoding="utf-8"))
    rounds = sorted((json.loads(path.read_text(encoding="utf-8")) for path in
                     (work / "graph-rounds").glob("*.json")), key=lambda row: (row["observed_at"], row["round_id"]))
    graph_observations = [row for episode in rounds for row in episode["observations"]]
    knowledge_candidates = [row for row in candidates if row.get("record_type") != "source_version"]
    actual_candidates = []
    seen = set()
    for row in [*knowledge_candidates, *(row for row in graph_observations if "knowledge_revision" in row)]:
        key = (row["id"], row["knowledge_revision"])
        if key not in seen:
            actual_candidates.append({"id": key[0], "knowledge_revision": key[1]})
            seen.add(key)
    source_fields = ("id", "revision", "path", "start_line", "end_line", "locator", "private")
    sources_selected = [{field: row[field] for field in source_fields if field in row}
                        for row in ranked["items"] if row.get("record_type") == "source_version"]
    observed_sources = {(row["id"], row["revision"]) for row in [*candidates, *graph_observations]
                        if row.get("record_type") == "source_version"}
    missing_sources = {(row["id"], row["revision"]) for row in sources_selected} - observed_sources
    if missing_sources:
        raise ValueError(f"Candidate manifest omits observed originals: {sorted(missing_sources)}")
    items = [{"id": row["id"], "knowledge_revision": row["knowledge_revision"]}
             for row in ranked["items"] if row.get("record_type") != "source_version"]
    known = frozen["base"]["matches"] + behavior["candidates"] + items
    missing = {(row["id"], row["knowledge_revision"]) for row in known} - seen
    if missing:
        raise ValueError(f"Candidate manifest omits observed versions: {sorted(missing)}")
    context = {key: frozen[key] for key in
               ("anchors", "knowledge_cutoff", "query", "episode", "budget", "policy")}
    access_fields = ("access_model", "access_compiled_j", "access_fact_j", "access_interval")
    observations = []
    sources = [("base", frozen["base"]["matches"]), ("behavior", behavior["candidates"]),
               ("followup", knowledge_candidates)]
    sources.extend((f"graph:{episode['round_id']}", [row for row in episode["observations"] if "knowledge_revision" in row])
                   for episode in rounds)
    for source, rows in sources:
        for row in rows:
            if any(key in row for key in access_fields):
                observation = {"id": row["id"], "knowledge_revision": row["knowledge_revision"],
                               "source": source}
                observation.update({key: row[key] for key in access_fields if key in row})
                observations.append(observation)
    context.update(candidates=actual_candidates, model=behavior["model"], access_observations=observations)
    if rounds:
        context["graph_rounds"] = rounds
    if sources_selected:
        context["source_items"] = sources_selected
    return {"delivery_id": request["delivery_id"], "items": items, "context": context}
