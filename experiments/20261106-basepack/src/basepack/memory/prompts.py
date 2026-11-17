"""Plan host workers and render their briefs without opening the memory store."""

import json
import os
from hashlib import sha256
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


def maintenance_layout(config, mode="manual", available_subagents=None, *, work_items=None, run_id=None):
    """Allocate a fixed roster from actual work; capacity remains an upper bound."""
    reserve = MAINTENANCE_RESERVE[mode]
    configured, limit = _capacity(config, available_subagents)
    budget = max(0, limit - reserve)
    work_items = budget if work_items is None else _nonnegative(work_items, "work_items")
    remaining = min(work_items, budget)
    identity = run_id or uuid4().hex
    prefix = f"bp_mem_{identity[:8]}_"
    teams = []
    while remaining:
        team = len(teams)
        readers = min(4, remaining - 1)
        teams.append({"team": team, "task_name": f"{prefix}coord_{team}",
                      "parent_task_name": f"{prefix}coord_0" if team else None,
                      "publisher": team == 0,
                      "reader_task_names": [f"{prefix}read_{team}_{reader}" for reader in range(readers)],
                      "coordinator_ai": config.resolve_ai(tier="tier2"),
                      "reader_ai": config.resolve_ai(tier="tier1")})
        remaining -= 1 + readers
        if mode == "automatic":
            break
    planned = sum(1 + len(team["reader_task_names"]) for team in teams)
    return {"mode": mode, "run_id": identity, "work_items": work_items,
            "configured_subagents": configured, "concurrency_source": config.concurrency_source,
            "available_subagents": available_subagents, "reserve": reserve,
            "maintenance_budget": budget,
            "capacity_status": "verified_available" if available_subagents is not None else "organization_ceiling",
            "planned_subagents": planned, "unused_subagents": budget - planned, "teams": teams}


def memory_command(config, *args):
    """Build a command for the current platform's standard shell."""
    parts = [str(config.python), "-X", "utf8", "-m", "basepack", "--config",
             str(config.path), "memory", *(str(arg) for arg in args)]
    if os.name == "nt":
        return "& " + " ".join("'" + part.replace("'", "''") + "'" for part in parts)
    return shlex.join(parts)


def prompt_dispatch(config, receipt, control, *, role="coordinator", tier=None, paths=None,
                    layout=None, team=0, reader=0, stage=None, stage_sha256=None):
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
    if stage:
        args.extend(["--stage", str(Path(stage).resolve())])
    if stage_sha256:
        args.extend(["--stage-sha256", stage_sha256])
    if paths:
        args.extend(["--paths", *paths])
    return {"role": role, "task_name": task_name, "team": team,
            "fork_turns": "none",
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
        sources.append({key: item[key] for key in
                        ("path", "reason", "category", "current_revision", "accepted_source_version") if key in item})
        sources[-1]["members"] = [{key: member[key] for key in
                                   ("id", "kind", "reasons", "source_version", "start_line", "end_line", "locator")
                                   if key in member} for member in item["members"]]
        if item.get("uncovered_ranges"):
            sources[-1]["uncovered_ranges"] = [{key: row[key] for key in ("start_line", "end_line", "locator") if key in row}
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
                  team=0, reader=0, stage=None, stage_sha256=None):
    """Render one brief from a saved receipt; no store, locks, or writes are used."""
    receipt_path = Path(receipt).resolve()
    material = json.loads(receipt_path.read_text(encoding="utf-8"))
    layout = material["layout"]
    stage_context = None
    if stage:
        from .stages import load_stage
        stage_context = load_stage(receipt, control, stage, file_sha256=stage_sha256)
        layout = stage_context["layout"]
    dispatch = prompt_dispatch(config, receipt, control, role=role, tier=tier, paths=paths,
                               layout=layout, team=team, reader=reader, stage=stage, stage_sha256=stage_sha256)
    if stage_context:
        stage_context = {key: stage_context[key] for key in
                         ("index", "receipt", "control", "owner_run_id", "previous_stage", "handoff", "remaining", "completion")}
        if not dispatch["publisher"]:
            stage_context.pop("remaining")
            stage_context["assigned_paths"] = paths
    assigned = layout["teams"][team]
    template_role = "reading-coordinator" if role == "coordinator" and not dispatch["publisher"] else role
    template = Template((Path(__file__).with_name("prompts") / f"{template_role}.md").read_text(encoding="utf-8"))
    readers = [prompt_dispatch(config, receipt, control, role="reader", layout=layout,
                               team=team, reader=index, paths=["<project-relative-source>"],
                               stage=stage, stage_sha256=stage_sha256)
               for index in range(len(assigned["reader_task_names"]))] if role == "coordinator" else []
    coordinators = [prompt_dispatch(config, receipt, control, layout=layout, team=item["team"],
                                    paths=["<project-relative-source>"], stage=stage, stage_sha256=stage_sha256)
                    for item in layout["teams"][1:]] if dispatch["publisher"] else []
    work = config.root / "tmp" / "basepack-maintenance" / receipt_path.stem / uuid4().hex
    reading, batch = work / "reading.json", work / "batch.json"
    values = {
        "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
        "prepare_inspection": (Path(__file__).with_name("prompts") / "prepare-inspection.md").read_text(encoding="utf-8").strip(),
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
        "stage_context": json.dumps(stage_context, ensure_ascii=False) if stage_context else "Initial stage; original receipt scope.",
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
    return {"prompt": template.substitute(values), "stage_context": stage_context, **dispatch}
