"""Plan host workers and render their briefs without opening the memory store."""

import json
import os
from pathlib import Path, PurePath
import shlex
from string import Template
from uuid import uuid4


MAINTENANCE_RESERVE = {"automatic": 1, "manual": 0}


def _nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _capacity(config, available_subagents):
    configured = config.max_concurrent_subagents
    available = (_nonnegative(available_subagents, "available_subagents")
                 if available_subagents is not None else configured)
    return configured, min(configured, available)


def maintenance_layout(config, mode="manual", available_subagents=None):
    """Compute one round's fixed organization; absent availability is only a ceiling."""
    reserve = MAINTENANCE_RESERVE[mode]
    configured, limit = _capacity(config, available_subagents)
    budget = max(0, limit - reserve)
    teams = []
    if budget:
        if mode == "automatic":
            count, readers = 1, min(4, budget - 1) if budget >= 4 else 0
        else:
            count, readers = (min(10, budget // 5), 4) if budget >= 5 else (1, 0)
        for team in range(count):
            teams.append({
                "team": team,
                "task_name": f"bp_mem_coord_{team}",
                "parent_task_name": "bp_mem_coord_0" if team else None,
                "publisher": team == 0,
                "reader_task_names": [f"bp_mem_read_{team}{reader}" for reader in range(readers)],
                "coordinator_ai": config.resolve_ai(tier="tier2"),
                "reader_ai": config.resolve_ai(tier="tier1"),
            })
    used = sum(1 + len(team["reader_task_names"]) for team in teams)
    return {"mode": mode, "configured_subagents": configured,
            "concurrency_source": config.concurrency_source,
            "available_subagents": available_subagents, "reserve": reserve,
            "maintenance_budget": budget,
            "capacity_status": "verified_available" if available_subagents is not None else "organization_ceiling",
            "used_subagents": used, "unused_subagents": budget - used, "teams": teams}


def memory_command(config, *args):
    """Build a command for the current platform's standard shell."""
    parts = [str(config.python), "-X", "utf8", "-m", "basepack", "--config",
             str(config.path), "memory", *(str(arg) for arg in args)]
    if os.name == "nt":
        return "& " + " ".join("'" + part.replace("'", "''") + "'" for part in parts)
    return shlex.join(parts)


def prompt_dispatch(config, receipt, control, *, role="coordinator", tier=None, paths=None,
                    layout=None, team=0, reader=0):
    """Describe a future render without reading the receipt or loading a template."""
    ai_key = {"coordinator": "coordinator_ai", "reader": "reader_ai"}[role]
    team = _nonnegative(team, "team")
    if (role == "reader" or team > 0) and not paths:
        raise ValueError(f"{role} requires at least one project-relative path")
    if role == "coordinator" and team == 0 and paths is not None:
        raise ValueError("publisher coordinator does not accept paths")
    for path in paths or ():
        relative = PurePath(path)
        if not str(path) or relative.anchor or ".." in relative.parts:
            raise ValueError(f"Source path must be project-relative: {path}")
    layout = maintenance_layout(config) if layout is None else layout
    assigned = layout["teams"][team]
    task_name = (assigned["reader_task_names"][_nonnegative(reader, "reader")]
                 if role == "reader" else assigned["task_name"])
    resolved = config.resolve_ai(tier=tier) if tier else assigned[ai_key]
    args = ["prompt", "--receipt", str(Path(receipt).resolve()), "--control",
            str(Path(control).resolve()), "--role", role, "--team", team]
    if role == "reader":
        args.extend(["--reader", reader])
    if tier:
        args.extend(["--tier", tier])
    if paths:
        args.extend(["--paths", *paths])
    return {"role": role, "task_name": task_name, "team": team,
            "reader": reader if role == "reader" else None,
            "parent_task_name": assigned["task_name"] if role == "reader" else assigned["parent_task_name"],
            "publisher": role == "coordinator" and assigned["publisher"],
            "reader_task_names": assigned["reader_task_names"] if role == "coordinator" else [],
            **resolved, "render_command": memory_command(config, *args)}


def pending_workers(layout, available_subagents, started_task_names=()):
    """Shrink only unstarted dispatches; current availability already excludes started work."""
    budget = max(0, min(layout["configured_subagents"],
                        _nonnegative(available_subagents, "available_subagents")) - layout["reserve"])
    groups = []
    for assigned in layout["teams"]:
        workers = [{"role": "coordinator", "task_name": assigned["task_name"],
                        "team": assigned["team"], "reader": None,
                        "parent_task_name": assigned["parent_task_name"],
                        "publisher": assigned["publisher"],
                        "reader_task_names": assigned["reader_task_names"],
                        **assigned["coordinator_ai"]}]
        for reader, task_name in enumerate(assigned["reader_task_names"]):
            workers.append({"role": "reader", "task_name": task_name,
                            "team": assigned["team"], "reader": reader,
                            "parent_task_name": assigned["task_name"], "publisher": False,
                            "reader_task_names": [], **assigned["reader_ai"]})
        groups.append(workers)
    started = set(started_task_names)
    unknown = started - {worker["task_name"] for workers in groups for worker in workers}
    if unknown:
        raise ValueError(f"Started workers are outside the saved layout: {sorted(unknown)}")
    pending = []
    for workers in groups:
        remaining = [worker for worker in workers if worker["task_name"] not in started]
        if (layout["mode"] == "manual" and len(workers) > 1 and len(remaining) == len(workers)
                and len(remaining) > budget):
            continue
        accepted = remaining[:budget]
        pending.extend(accepted)
        budget -= len(accepted)
    return pending


def _reader_hints(material, paths):
    """Select compact receipt hints without copying original text into a prompt."""
    selected = {PurePath(path).as_posix() for path in paths}
    semantic = material["semantic"]
    member_paths = {member["id"]: item["path"] for item in semantic for member in item["members"]}
    sources = []
    for item in semantic:
        if item["path"] not in selected:
            continue
        sources.append({key: item[key] for key in ("path", "reason", "category") if key in item})
        sources[-1]["members"] = [{key: member[key] for key in
                                   ("id", "kind", "reasons", "source_version", "start_line", "end_line")
                                   if key in member} for member in item["members"]]
        if item.get("uncovered_ranges"):
            sources[-1]["uncovered_ranges"] = [{key: row[key] for key in ("start_line", "end_line")}
                                                  for row in item["uncovered_ranges"]]
    relevant, unknown = [], 0
    for relation in material["pending_relations"]:
        basis = relation["basis"]
        known_paths = [item.get("path") or member_paths.get(item["member"]) for item in basis]
        hint = {"id": relation["id"], "basis_members": [item["member"] for item in basis]}
        if any(path in selected for path in known_paths):
            relevant.append(hint)
        elif not basis or any(path is None for path in known_paths):
            unknown += 1
    hints = {"sources": sources, "related_pending_relations": relevant, "unresolved_pending_relations_count": unknown}
    if "codex" in material:
        hints["codex"] = material["codex"]
    return hints


def render_prompt(config, receipt, control, *, role="coordinator", tier=None, paths=None,
                  team=0, reader=0):
    """Render one brief from a saved receipt; no store, locks, or writes are used."""
    receipt_path = Path(receipt).resolve()
    material = json.loads(receipt_path.read_text(encoding="utf-8"))
    layout = material["layout"]
    dispatch = prompt_dispatch(config, receipt, control, role=role, tier=tier, paths=paths,
                               layout=layout, team=team, reader=reader)
    assigned = layout["teams"][team]
    template_role = "reading-coordinator" if role == "coordinator" and not dispatch["publisher"] else role
    template = Template((Path(__file__).with_name("prompts") / f"{template_role}.md").read_text(encoding="utf-8"))
    readers = [prompt_dispatch(config, receipt, control, role="reader", layout=layout,
                               team=team, reader=index, paths=["<project-relative-source>"])
               for index in range(len(assigned["reader_task_names"]))] if role == "coordinator" else []
    coordinators = [prompt_dispatch(config, receipt, control, layout=layout, team=item["team"],
                                    paths=["<project-relative-source>"])
                    for item in layout["teams"][1:]] if dispatch["publisher"] else []
    work = config.root / "tmp" / "basepack-maintenance" / receipt_path.stem / uuid4().hex
    reading, batch = work / "reading.json", work / "batch.json"
    values = {
        "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
        "root": str(config.root),
        "python": str(config.python),
        "config": str(config.path),
        "receipt": str(receipt_path),
        "control": str(Path(control).resolve()),
        "semantic_count": str(len(material["semantic"])),
        "relations_count": str(len(material["pending_relations"])),
        "feedback_count": str(len(material.get("feedback", []))),
        "paths": json.dumps(paths or [], ensure_ascii=False),
        "hints": json.dumps(_reader_hints(material, paths) if paths else {}, ensure_ascii=False),
        "codex": json.dumps(material.get("codex", {}), ensure_ascii=False),
        "task_name": dispatch["task_name"],
        "team": str(team),
        "publisher_task_name": layout["teams"][0]["task_name"],
        "reader_workers": json.dumps(readers, ensure_ascii=False),
        "coordinator_workers": json.dumps(coordinators, ensure_ascii=False),
        "reader_count": str(len(readers)),
        "layout": json.dumps({key: value for key, value in layout.items() if key != "teams"}, ensure_ascii=False),
        "work": str(work),
        "batch": str(batch),
        "prepare_command": memory_command(config, "prepare", "--paths", *(paths or []),
                                          "--output", reading),
        "apply_command": memory_command(config, "apply", "--batch", batch,
                                        "--control", Path(control).resolve()),
        "read_command": memory_command(config, "read", "<member-id>"),
        "neighbors_command": memory_command(config, "neighbors", "<record-id>", "--include-stale"),
        "model": dispatch["model"],
        "effort": dispatch["reasoning_effort"],
        "tier": dispatch["tier"],
    }
    return {"prompt": template.substitute(values), **dispatch}


def retrieval_dispatch(config, request_path, slot=0, available_subagents=None, tier=None):
    """Describe one complete retrieval delegation, independently of maintenance ownership."""
    slot = _nonnegative(slot, "slot")
    configured, limit = _capacity(config, available_subagents)
    worker = config.resolve_ai(purpose="retrieval", tier=tier) if limit else {
        "tier": None, "model": None, "reasoning_effort": None}
    args = ["retrieval-prompt", "--request", Path(request_path).resolve(), "--slot", slot]
    if available_subagents is not None:
        args.extend(["--available-subagents", available_subagents])
    if tier:
        args.extend(["--tier", tier])
    return {"executor": "worker" if limit else "main", "task_name": f"bp_mem_search_{slot}" if limit else None,
            "slot": slot, "configured_subagents": configured, "available_subagents": available_subagents,
            "capacity_status": "verified_available" if available_subagents is not None else "organization_ceiling",
            **worker, "render_command": memory_command(config, *args)}


def render_retrieval_prompt(config, request_path, slot=0, available_subagents=None, tier=None):
    """Read the retrieval request and template only; never claim or inspect maintenance state."""
    dispatch = retrieval_dispatch(config, request_path, slot, available_subagents, tier)
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    if not isinstance(request["question"], str) or not request["question"].strip():
        raise ValueError("question must be a nonempty string")
    if not isinstance(request["scope"], str):
        raise ValueError("scope must be a string")
    if not _nonnegative(request["content_budget"], "content_budget"):
        raise ValueError("content_budget must be positive")
    work = config.root / "tmp" / "basepack-retrieval" / uuid4().hex
    template = Template((Path(__file__).with_name("prompts") / "retrieval.md").read_text(encoding="utf-8"))
    assignment = (f"retrieval worker {dispatch['task_name']}, assigned {dispatch['tier']} / "
                  f"{dispatch['model']} / {dispatch['reasoning_effort']}" if dispatch["executor"] == "worker"
                  else "main agent performing retrieval directly because no subagent seat is available")
    values = {"assignment": assignment, "root": str(config.root), "config": str(config.path),
              "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
              "request": json.dumps(request, ensure_ascii=False), "work": str(work),
              "search_command": memory_command(config, "search", "--text", "<terms>", "--scope", request["scope"]),
              "read_command": memory_command(config, "read", "<member-id>"),
              "neighbors_command": memory_command(config, "neighbors", "<record-id>"),
              "rank_command": memory_command(config, "rank", "--input", work / "scored.json",
                                               "--budget", request["content_budget"])}
    return {"prompt": template.substitute(values), **dispatch}
