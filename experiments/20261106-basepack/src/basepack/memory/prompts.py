"""Plan host workers and render their briefs without opening the memory store."""

import json
import os
from hashlib import sha256
from pathlib import Path, PurePath
import shlex
from string import Template
from uuid import uuid4


MAINTENANCE_RESERVE = {"automatic": 1, "manual": 1}
MAINTENANCE_BOOTSTRAP = "Run the following command and follow the `prompt` field in its JSON output:"
MAINTENANCE_ORGANIZATION = "finite-wave-v1"


def _wave_layout(layout):
    if layout.get("organization") != MAINTENANCE_ORGANIZATION:
        raise ValueError("Legacy maintenance receipt: finish the old run and start a fresh wave-based maintenance run")
    return layout


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
    readers = min(work_items, max(0, budget - 1))
    identity = run_id or uuid4().hex
    prefix = f"bp_mem_{identity[:8]}_"
    teams = []
    if readers:
        teams.append({"team": 0, "task_name": f"{prefix}coord_0",
                      "parent_task_name": None, "publisher": True,
                      "reader_task_names": [f"{prefix}read_0_{reader}" for reader in range(readers)],
                      "coordinator_ai": config.resolve_ai(tier="tier2"),
                      "reader_ai": config.resolve_ai(tier="tier1")})
    planned = sum(1 + len(team["reader_task_names"]) for team in teams)
    return {"organization": MAINTENANCE_ORGANIZATION, "mode": mode, "run_id": identity, "work_items": work_items,
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
    team = _nonnegative(team, "team")
    if role != "coordinator" or team != 0 or reader != 0 or paths is not None:
        raise ValueError("Wave maintenance uses one coordinator; readers are registered by wave create")
    layout = _wave_layout(maintenance_layout(config) if layout is None else layout)
    assigned = layout["teams"][team]
    task_name = assigned["task_name"]
    resolved = config.resolve_ai(tier=tier) if tier else assigned["coordinator_ai"]
    args = ["prompt", "--receipt", str(Path(receipt).resolve()), "--control",
            str(Path(control).resolve()), "--role", role, "--team", team]
    if tier:
        args.extend(["--tier", tier])
    if stage:
        args.extend(["--stage", str(Path(stage).resolve())])
    if stage_sha256:
        args.extend(["--stage-sha256", stage_sha256])
    render_command = memory_command(config, *args)
    spawn_arguments = {"task_name": task_name, "fork_turns": "none",
                       "model": resolved["model"], "reasoning_effort": resolved["reasoning_effort"],
                       "message": f"{MAINTENANCE_BOOTSTRAP}\n{render_command}"}
    return {"role": role, "task_name": task_name, "team": team,
            "fork_turns": "none",
            "reader": None,
            "parent_task_name": assigned["parent_task_name"],
            "publisher": assigned["publisher"],
            "reader_task_names": assigned["reader_task_names"],
            **resolved, "render_command": render_command, "spawn_arguments": spawn_arguments}


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
    layout = _wave_layout(material["layout"])
    stage_context = None
    if stage:
        from .stages import load_stage
        stage_context = load_stage(receipt, control, stage, file_sha256=stage_sha256)
        layout = _wave_layout(stage_context["layout"])
    dispatch = prompt_dispatch(config, receipt, control, role=role, tier=tier, paths=paths,
                               layout=layout, team=team, reader=reader, stage=stage, stage_sha256=stage_sha256)
    if stage_context:
        stage_context = {key: stage_context[key] for key in
                         ("index", "receipt", "control", "owner_run_id", "previous_stage", "handoff", "remaining", "completion")}
        if not dispatch["publisher"]:
            stage_context.pop("remaining")
            stage_context["assigned_paths"] = paths
    template_role = role
    template = Template((Path(__file__).with_name("prompts") / f"{template_role}.md").read_text(encoding="utf-8"))
    work = config.root / "tmp" / "basepack-maintenance" / receipt_path.stem / uuid4().hex
    reading, batch = work / "reading.json", work / "batch.json"
    wave_create = ["wave", "create", "--receipt", str(receipt_path), "--control", str(Path(control).resolve()),
                   "--run-id", material["owner_run_id"], "--tasks", "<tasks.json>",
                   "--coordinator", "<canonical-coordinator>", "--readers", "<reader-count>"]
    if stage:
        wave_create.extend(["--stage", str(Path(stage).resolve())])
    if stage_sha256:
        wave_create.extend(["--stage-sha256", stage_sha256])
    wave_base = ["--control", str(Path(control).resolve()), "--run-id", material["owner_run_id"],
                 "--wave-id", "<wave-id>"]
    wave_commands = {
        "started": memory_command(config, "wave", "started", *wave_base, "--worker", "<worker>", "--handle", "<host-handle>"),
        "worker_failed": memory_command(config, "wave", "worker-failed", *wave_base, "--worker", "<worker>", "--error", "<original-error>"),
        "initialized": memory_command(config, "wave", "initialized", *wave_base),
        "finish": memory_command(config, "wave", "finish", *wave_base),
        "inspect": memory_command(config, "wave", "inspect", *wave_base),
        "publish": memory_command(config, "wave", "publish", *wave_base, "--completed", "<completed.json>",
                                  "--frozen", "<frozen.json>", "--result", "<result.json>"),
        "publication_failed": memory_command(config, "wave", "publication-failed", *wave_base,
                                             "--error", "<original-error>", "--publisher-ended", "--no-commit"),
        "close": memory_command(config, "wave", "close", *wave_base),
    }
    values = {
        "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
        "prepare_inspection": (Path(__file__).with_name("prompts") / "prepare-inspection.md").read_text(encoding="utf-8").strip(),
        "root": str(config.root),
        "python": str(config.python),
        "config": str(config.path),
        "receipt": str(receipt_path),
        "control": str(Path(control).resolve()),
        "run_id": material["owner_run_id"],
        "wave_create_command": memory_command(config, *wave_create),
        "wave_commands": json.dumps(wave_commands, ensure_ascii=False),
        "reader_capacity": str(len(layout["teams"][0]["reader_task_names"])),
        "semantic_count": str(len(material["semantic"])),
        "relations_count": str(len(material["pending_relations"])),
        "feedback_count": str(len(material.get("feedback", []))),
        "paths": json.dumps(paths or [], ensure_ascii=False),
        "hints": json.dumps(_reader_hints(material, paths) if paths else {}, ensure_ascii=False),
        "codex": json.dumps(material.get("codex", {}), ensure_ascii=False),
        "task_name": dispatch["task_name"],
        "team": str(team),
        "publisher_task_name": layout["teams"][0]["task_name"],
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
