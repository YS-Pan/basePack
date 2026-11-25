"""Plan host work and render prompts without opening the memory store."""

import json
import os
from hashlib import sha256
from pathlib import Path, PurePath
import shlex
from string import Template
from uuid import uuid4

from basepack.project.config import _level_from_legacy_tier


MAINTENANCE_RESERVE = {"automatic": 1, "manual": 1}
MAINTENANCE_BOOTSTRAP = (
    "First run the read-only prompt-rendering command below in the normal project sandbox. "
    "Follow the `prompt` field in its JSON output.\n"
    "Read the shell result body. A `Rejected` wrapper can contain a Windows provisioning error confirming the process "
    "never started. If Auto-review denied the command, the review route is unavailable, or execution or its result is "
    "uncertain, report the actual error and status to the original parent and stop without repeating the command. "
    "For a confirmed Windows pre-launch failure in a session that routes shell escalation to Auto-review, request at "
    "most one per-command review of that exact invocation. Use `sandbox_permissions=\"require_escalated\"` where exposed "
    "or the host's equivalent per-command option. Leave any reusable `prefix_rule` unset. "
    "Keep the command, working directory and all arguments unchanged, including any `--holder`, `--control`, "
    "`--run-id`, `--wave-id` or `--worker`. Give the actual launch error and the original rendering purpose as the "
    "review reason."
)
MAINTENANCE_ORGANIZATION = "finite-wave-v1"


def _wave_layout(layout):
    if layout.get("organization") != MAINTENANCE_ORGANIZATION:
        raise ValueError("Legacy maintenance receipt: finish the old run and start a fresh wave-based maintenance run")
    teams = [{**team, "coordinator_ai": _saved_ai(team["coordinator_ai"]),
              "reader_ai": _saved_ai(team["reader_ai"])} for team in layout["teams"]]
    return {**layout, "teams": teams}


def _saved_ai(assignment):
    """Read legacy level labels without changing the settings pinned by the receipt."""
    if "tier" not in assignment:
        return assignment
    ai = assignment.copy()
    ai["level"] = _level_from_legacy_tier(ai.pop("tier"))
    return ai


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
                      "coordinator_ai": config.resolve_ai(level=2),
                      "reader_ai": config.resolve_ai(level=1)})
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


def render_template(name, **values):
    template = Path(__file__).with_name("prompts") / f"{name}.md"
    return Template(template.read_text(encoding="utf-8")).substitute(values)


def _collection_paths(config, attempt_id):
    from .owner import attempt_control

    control = attempt_control(config.memory_dir, attempt_id)
    registry = control.with_name(f"collection-registry-{attempt_id}.json")
    return registry, control.with_name(f"collection-{attempt_id}.json")


def render_collection_prompt(config, attempt_id):
    """Render a single project collection request without executing it."""
    registry, receipt = _collection_paths(config, attempt_id)
    values = {
        "root": str(config.root),
        "registry": str(registry),
        "receipt": str(receipt),
        "command": memory_command(config, "collect", "--attempt", attempt_id,
                                  "--codex-registry", registry, "--output", receipt),
        "approval_reason": f"Run one basePack chat collection for {config.root} in the normal Windows user context. "
                           "The Codex App Server needs to open its user state database. "
                           "Project chat snapshots and the collection receipt stay in this project.",
    }
    return {"prompt": render_template("collect", **values), **values}


def maintenance_start(config, *, holder, mode, available_subagents=None, scope=None, collection=None,
                      retained=False, allow_retained=False):
    """Prepare one early coordinator and a stop handle; ownership starts at preflight."""
    from .codex_index_config import configured
    from .owner import attempt_control, status

    indexed = configured(config)
    if indexed and (collection is not None or retained or allow_retained):
        raise ValueError("Dialogue indexing cannot use --collection, --retained, or --allow-retained")
    current_owner = status(config.memory_dir)
    if current_owner is not None:
        return {"status": "busy", "owner": current_owner}
    attempt_id = uuid4().hex
    layout = maintenance_layout(config, mode=mode, available_subagents=available_subagents,
                                work_items=1, run_id=attempt_id)
    if not layout["teams"]:
        return {"status": "capacity_unavailable",
                "reason": "A coordinator, a reader and a recovery seat are needed to launch delegated maintenance."}
    team = layout["teams"][0]
    control = attempt_control(config.memory_dir, attempt_id)
    preflight = ["maintain", "--attempt", attempt_id, "--holder", holder, "--control", control, "--mode", mode]
    if scope:
        preflight.extend(["--scope", *scope])
    if available_subagents is not None:
        preflight.extend(["--available-subagents", available_subagents])
    capture = (not indexed and not collection and not retained
               and bool(config.raw["memory"].get("codex", {}).get("project_id")))
    if collection:
        preflight.extend(["--collection", Path(collection).resolve()])
    elif retained:
        preflight.append("--retained")
    if capture:
        _, receipt = _collection_paths(config, attempt_id)
        fallback = "If fresh capture is unavailable, report the gap and leave maintenance pending."
        if allow_retained:
            retained_command = memory_command(config, *preflight, "--retained")
            fallback = ("If fresh capture is unavailable, the parent has authorized retained originals. Report current chat "
                        f"freshness as unknown and run this in the normal project sandbox:\n\n```text\n{retained_command}\n```")
        source_step = render_template("maintenance-collection",
            collect_prompt=memory_command(config, "collect-prompt", "--attempt", attempt_id),
            captured_command=memory_command(config, *preflight, "--collection", receipt),
            fallback=fallback)
    elif indexed:
        source_step = ("This project's explicit dialogue index reads authorized messages directly from Codex in memory. "
                       "Do not run collect, collect-prompt, or use retained chat snapshots. Run the ordinary preflight "
                       "below and report a host access failure with its original error.\n\n"
                       f"```text\n{memory_command(config, *preflight)}\n```")
    else:
        source_step = f"Run this preflight command in the normal project sandbox:\n\n```text\n{memory_command(config, *preflight)}\n```"
    ai = team["coordinator_ai"]
    message = render_template("maintenance-start", root=str(config.root), holder=holder,
                              attempt_id=attempt_id, task_name=team["task_name"], source_step=source_step)
    return {"status": "prepared", "attempt_id": attempt_id, "control": str(control),
            "spawn_arguments": {"task_name": team["task_name"], "fork_turns": "none", "model": ai["model"],
                                "reasoning_effort": ai["reasoning_effort"], "message": message},
            "stop_command": memory_command(config, "stop", "--attempt", attempt_id),
            "release_command": memory_command(config, "release", "--control", control)}


def prompt_dispatch(config, receipt, control, *, role="coordinator", level=None, paths=None,
                    layout=None, team=0, reader=0, stage=None, stage_sha256=None):
    """Describe a future render without reading the receipt or loading a template."""
    team = _nonnegative(team, "team")
    if role != "coordinator" or team != 0 or reader != 0 or paths is not None:
        raise ValueError("Wave maintenance uses one coordinator; readers are registered by wave create")
    layout = _wave_layout(maintenance_layout(config) if layout is None else layout)
    assigned = layout["teams"][team]
    task_name = assigned["task_name"]
    resolved = config.resolve_ai(level=level) if level is not None else assigned["coordinator_ai"]
    args = ["prompt", "--receipt", str(Path(receipt).resolve()), "--control",
            str(Path(control).resolve()), "--role", role, "--team", team]
    if level is not None:
        args.extend(["--level", level])
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


def _codex_summary(codex):
    """Keep capture status, counts and evidence pointers in maintenance prompts."""
    summary = {key: codex[key] for key in
               ("status", "project_id", "freshness", "receipt", "capture_dir", "attachment_dir") if key in codex}
    counts = {}
    for field, category in (("discovered", "discovered"), ("unresolved", "unresolved"),
                            ("unresolved_threads", "unresolved"), ("excluded", "excluded"),
                            ("gaps", "gaps"), ("discovery_gaps", "discovery_gaps"),
                            ("selected_root_thread_ids", "selected_roots")):
        if field in codex and category not in counts:
            value = codex[field]
            counts[category] = value if isinstance(value, int) else len(value)
    if counts:
        summary["counts"] = counts
    return summary


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
        known_paths = relation.get("scope_paths") or [item.get("path") or member_paths.get(item["member"])
                                                      for item in basis]
        hint = {"id": relation["id"], "basis_members": [item["member"] for item in basis]}
        if any(path in selected for path in known_paths):
            relevant.append(hint)
        elif not known_paths or any(path is None for path in known_paths):
            unknown += 1
    hints = {"sources": sources, "related_pending_relations": relevant, "unresolved_pending_relations_count": unknown}
    if "codex" in material:
        hints["codex"] = _codex_summary(material["codex"])
    return hints


def render_prompt(config, receipt, control, *, role="coordinator", level=None, paths=None,
                  team=0, reader=0, stage=None, stage_sha256=None):
    """Render one brief from a saved receipt; no store, locks, or writes are used."""
    receipt_path = Path(receipt).resolve()
    receipt_bytes = receipt_path.read_bytes()
    receipt_ref = {"path": str(receipt_path), "file_sha256": sha256(receipt_bytes).hexdigest()}
    material = json.loads(receipt_bytes.decode("utf-8"))
    layout = _wave_layout(material["layout"])
    stage_context = None
    if stage:
        from .stages import load_stage
        stage_context = load_stage(receipt, control, stage, file_sha256=stage_sha256)
        if stage_context["receipt"]["file_sha256"] != receipt_ref["file_sha256"]:
            raise ValueError(f"Maintenance receipt changed during stage rendering: {receipt_path}")
        layout = _wave_layout(stage_context["layout"])
    dispatch = prompt_dispatch(config, receipt, control, role=role, level=level, paths=paths,
                               layout=layout, team=team, reader=reader, stage=stage, stage_sha256=stage_sha256)
    if stage_context:
        stage_context = {key: stage_context[key] for key in
                         ("index", "receipt", "control", "owner_run_id", "previous_stage", "handoff", "remaining", "completion")}
        if not dispatch["publisher"]:
            stage_context.pop("remaining")
            stage_context["assigned_paths"] = paths
    graph_candidates = material.get("graph_candidates", [])
    outcome_candidate = material.get("outcome_candidate")
    if stage_context and dispatch["publisher"]:
        remaining = set(stage_context["remaining"]["relations"])
        graph_candidates = [item for item in graph_candidates if item["id"] in remaining]
        if outcome_candidate and outcome_candidate["id"] not in remaining:
            outcome_candidate = None
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
        "receipt": json.dumps(receipt_ref, ensure_ascii=False),
        "control": str(Path(control).resolve()),
        "run_id": material["owner_run_id"],
        "wave_create_command": memory_command(config, *wave_create),
        "wave_commands": json.dumps(wave_commands, ensure_ascii=False),
        "reader_capacity": str(len(layout["teams"][0]["reader_task_names"])),
        "semantic_count": str(len(material["semantic"])),
        "relations_count": str(len(material["pending_relations"])),
        "graph_candidates": json.dumps(graph_candidates, ensure_ascii=False),
        "outcome_candidate": json.dumps(outcome_candidate, ensure_ascii=False),
        "feedback_count": str(len(material.get("feedback", []))),
        "paths": json.dumps(paths or [], ensure_ascii=False),
        "hints": json.dumps(_reader_hints(material, paths) if paths else {}, ensure_ascii=False),
        "codex": json.dumps(_codex_summary(material.get("codex", {})), ensure_ascii=False),
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
        "level": dispatch["level"],
    }
    return {"prompt": render_template(role, **values), "stage_context": stage_context, **dispatch}
