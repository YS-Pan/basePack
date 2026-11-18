"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import json
from pathlib import Path


def register_commands(subparsers):
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory")
    commands = memory.add_subparsers(dest="memory_action", required=True)
    actions = {name: commands.add_parser(name) for name in
               ("init", "guide", "collect", "sources", "prepare", "freeze", "publish", "apply", "stop", "owner", "release", "recover-owner", "embed", "search", "read", "knowledge", "history", "neighbors", "brief", "changes", "maintain", "stage", "prompt", "retrieve", "retrieval-start", "retrieval-receipt", "behavior-train", "behavior-compile", "behavior-candidates", "retrieval-dispatch", "retrieval-prompt", "freshness", "rank", "delivery", "access-hints", "feedback-report", "feedback-list", "feedback-resolve")}
    from .wave_cli import register as register_waves
    register_waves(commands.add_parser("wave", help="Host-driven finite maintenance wave"))
    actions["feedback-report"].add_argument("--kind", choices=["knowledge", "retrieval"], required=True)
    actions["feedback-report"].add_argument("--issue", required=True)
    actions["feedback-report"].add_argument("--target", help="Member, node or semantic edge ID")
    actions["feedback-report"].add_argument("--observed-revision", help="knowledge_revision returned when the target was observed; put software version in --issue")
    actions["feedback-report"].add_argument("--query", help="Query, including for missed results")
    actions["feedback-report"].add_argument("--source", help="Original location or source clue")
    actions["feedback-report"].add_argument("--reporter", help="Reporting agent or worker")
    actions["feedback-list"].add_argument("--all", action="store_true", help="Include resolved reports")
    actions["feedback-resolve"].add_argument("id", help="Feedback report ID")
    actions["feedback-resolve"].add_argument("--outcome", choices=["fixed", "invalid", "duplicate", "obsolete"], required=True)
    actions["feedback-resolve"].add_argument("--result", required=True)
    actions["feedback-resolve"].add_argument("--control", required=True, help="Current maintenance owner's control file")
    actions["feedback-resolve"].add_argument("--expected-revision", help="Target version confirmed after handling")
    actions["collect"].add_argument("--codex-registry", help="Explicit Codex project registry")
    actions["prepare"].add_argument("--paths", nargs="+", required=True,
                                    help="Project-relative files; enumerate directories first")
    actions["prepare"].add_argument("--historical-versions", help="JSON array of explicitly observed historical {id, knowledge_revision}")
    actions["freeze"].add_argument("--drafts", nargs="+", required=True, help="Reader-scoped UTF-8 JSON drafts")
    publication = actions["publish"].add_mutually_exclusive_group(required=True)
    publication.add_argument("--completed", help="Ordered JSON list of completed {path, file_sha256, assignment} drafts")
    publication.add_argument("--frozen", help="Resume this exact frozen UTF-8 JSON batch")
    actions["publish"].add_argument("--control", required=True, help="Current owner's control file")
    actions["publish"].add_argument("--result", required=True, help="Local detailed database-receipt projection")
    actions["publish"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["apply"].add_argument("--batch", required=True, help="Frozen UTF-8 JSON batch")
    actions["apply"].add_argument("--control", required=True, help="Current owner control file")
    actions["apply"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["stop"].add_argument("--control", required=True, help="The task's unique control file")
    actions["release"].add_argument("--control", required=True, help="Stopped owner control file")
    actions["recover-owner"].add_argument("--run-id", required=True)
    actions["recover-owner"].add_argument("--owner-ended", action="store_true", required=True, help="Attest that the previous owner and workers have ended")
    actions["recover-owner"].add_argument("--publication-resolved", action="store_true", required=True, help="Attest that each publication result has been verified")
    actions["search"].add_argument("--text", required=True)
    actions["search"].add_argument("--scope", default="", help="Project-relative path prefix; empty searches the whole project. Put business constraints in --text")
    actions["search"].add_argument("--limit", type=int, default=12)
    actions["search"].add_argument("--literal", action="store_true", help="With hybrid: prioritize case-insensitive path/title/text substring matches")
    actions["search"].add_argument("--mode", choices=["hybrid", "vector"],
                                 help="Override memory.search_mode from the project config")
    actions["search"].add_argument("--timeout", type=float, default=600)
    actions["embed"].add_argument("--ids", nargs="+", help="Member IDs; otherwise index current representations")
    actions["embed"].add_argument("--timeout", type=float, default=600)
    actions["read"].add_argument("id", help="Member ID; follow a knowledge node's evidence via neighbors")
    actions["read"].add_argument("--knowledge-revision", help="Read the observed knowledge version, including its original evidence")
    actions["read"].add_argument("--source-version", help="Read an original evidence snapshot; use --knowledge-revision for the old accepted representation")
    actions["read"].add_argument("--start-line", type=int, help="Evidence start line (inclusive)")
    actions["read"].add_argument("--end-line", type=int, help="Evidence end line (inclusive)")
    actions["read"].add_argument("--locator", help="Text-column or image evidence locator as a JSON object")
    actions["neighbors"].add_argument("id")
    actions["neighbors"].add_argument("--knowledge-revision", help="Expand the observed knowledge version")
    actions["neighbors"].add_argument("--include-stale", action="store_true", help="Explicit historical inspection")
    actions["knowledge"].add_argument("id", help="Member, node or semantic relation ID")
    actions["knowledge"].add_argument("--knowledge-revision", help="Observed knowledge version; default is current")
    actions["history"].add_argument("id", help="List retained knowledge versions and actual history coverage")
    actions["delivery"].add_argument("--input", required=True, help="Host-confirmed final receipt: delivery_id, items [{id, knowledge_revision}], optional context")
    actions["access-hints"].add_argument("--input", required=True, help="UTF-8 JSON array of observed {id, knowledge_revision} records")
    actions["brief"].add_argument("--task", default="", help="Task label only; brief directly reads published startup knowledge without search or embedding")
    actions["brief"].add_argument("--limit", type=int, default=6)
    actions["changes"].add_argument("--scope", nargs="+", required=True)
    actions["changes"].add_argument("--deep", action="store_true")
    actions["maintain"].add_argument("--scope", nargs="+", help="Restrict the actual workset to these project-relative paths")
    captured = actions["maintain"].add_mutually_exclusive_group()
    captured.add_argument("--collection", help="Verified receipt from independent memory collect")
    captured.add_argument("--retained", action="store_true", help="Explicitly consume retained chat snapshots; freshness remains unknown")
    actions["maintain"].add_argument("--control", required=True, help="Fresh, never-used task control file")
    actions["maintain"].add_argument("--holder", required=True, help="Host thread identity")
    actions["maintain"].add_argument("--mode", choices=["automatic", "manual"], default="manual",
                                    help="Both modes reserve one coordinator recovery seat; direct maintenance defaults to manual")
    actions["maintain"].add_argument("--available-subagents", type=int,
                                    help="Host raw free subagent seats, excluding the main agent and before business reserve")
    actions["maintain"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["stage"].add_argument("--receipt", required=True, help="Original fixed maintenance receipt")
    actions["stage"].add_argument("--control", required=True, help="The original maintenance control file")
    actions["stage"].add_argument("--handoff", required=True, help="Fixed JSON boundary with completed/remaining work and saved references")
    actions["stage"].add_argument("--previous-stage", help="Current stage package; omit only for the first handoff")
    actions["stage"].add_argument("--available-subagents", type=int,
                                  help="Current free subagent slots for the next bounded stage")
    actions["stage"].add_argument("--workers-ended", action="store_true", required=True,
                                 help="Host confirms the previous coordinator and its workers have ended")
    actions["prompt"].add_argument("--receipt", required=True, help="Maintenance receipt to render as worker context")
    actions["prompt"].add_argument("--control", required=True, help="The same task control file used by maintain and apply")
    actions["prompt"].add_argument("--role", choices=["coordinator"], default="coordinator")
    actions["prompt"].add_argument("--level", type=int, help="Override the role's default AI level")
    actions["prompt"].add_argument("--team", type=int, default=0, help="Fixed team from this receipt's saved layout")
    actions["prompt"].add_argument("--stage", help="Saved stage package for this original receipt/control")
    actions["prompt"].add_argument("--stage-sha256", help="Expected stage package hash from the saved reference")
    for name in ("retrieval-dispatch", "retrieval-prompt"):
        actions[name].add_argument("--request", required=True, help="UTF-8 JSON with question, scope and content_budget")
        actions[name].add_argument("--slot", type=int, default=0, help="Parent-owned retrieval slot")
        actions[name].add_argument("--available-subagents", type=int, help="Host raw free subagent seats")
        actions[name].add_argument("--level", type=int)
    retrieve = actions["retrieve"]
    request = retrieve.add_mutually_exclusive_group()
    request.add_argument("--question", help="Business question; the host runs the returned retrieval assignment")
    request.add_argument("--request", help="Reuse a prepared request and its stable delivery ID")
    retrieve.add_argument("--scope", default="", help="Project-relative path prefix; empty means the whole project")
    retrieve.add_argument("--budget", type=int, default=6000, help="Returned text character budget (default: 6000)")
    retrieve.add_argument("--slot", type=int, default=0, help="Parent-owned retrieval slot")
    retrieve.add_argument("--available-subagents", type=int, help="Host raw free subagent seats; zero uses the main agent")
    retrieve.add_argument("--level", type=int)
    actions["retrieval-start"].add_argument("--request", required=True)
    actions["retrieval-receipt"].add_argument("--request", required=True)
    actions["retrieval-receipt"].add_argument("--ranked", required=True)
    actions["retrieval-receipt"].add_argument("--candidates", required=True)
    actions["behavior-train"].add_argument("--rank", type=int, default=8)
    for parameter in ("epsilon", "beta", "strength"):
        actions["behavior-train"].add_argument("--" + parameter, type=float)
    actions["behavior-candidates"].add_argument("--input", required=True, help="Fixed original anchors and weights as JSON")
    actions["behavior-candidates"].add_argument("--limit", type=int, default=20)
    actions["behavior-candidates"].add_argument("--scope", default="")
    actions["freshness"].add_argument("--codex-registry", help="Host project binding and complete registered roots as UTF-8 JSON")
    actions["freshness"].add_argument("--thread", help="Read and compare one project-owned chat by ID")
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for name, command in actions.items():
        if name in ("prompt", "retrieval-dispatch", "retrieval-prompt"):
            command.set_defaults(output=None)
        else:
            command.add_argument("--output", help=("New frozen batch path (requires --completed)" if name == "publish"
                                                  else "Write JSON here and return its location"))


def dispatch(args, config):
    from .query import load_json_file

    action = args.memory_action
    if action == "wave":
        from .wave_cli import dispatch as dispatch_wave
        return dispatch_wave(config, args), 0
    if action == "maintain":
        from .owner import acquire, release_failed_startup
        claim = acquire(config.memory_dir, config.raw["memory"]["project_id"], args.holder, args.control)
        if not claim["acquired"]:
            if args.output:
                path = Path(args.output).resolve()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(claim, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"output": str(path)}, 0
            return claim, 0
        try:
            result = _maintain(config, args, claim)
            return _output(result, args.output), 0
        except Exception as error:
            try:
                release_failed_startup(config.memory_dir, args.control, claim["owner"]["run_id"])
            except Exception as cleanup_error:
                raise ExceptionGroup("Maintenance startup and ownership cleanup failed",
                                     [error, cleanup_error]) from error
            raise
    if action == "freeze":
        from .draft import freeze_file
        if not args.output:
            raise ValueError('memory freeze requires --output for the frozen batch')
        path = Path(args.output).resolve()
        batch = freeze_file([load_json_file(path) for path in args.drafts], path, config=config)
        return {"output": str(path), "batch_id": batch['batch_id']}, 0
    if action == "guide":
        result = {"skill": str(Path(__file__).with_name("SKILL.md"))}
    elif action == "stop":
        from .owner import stop_owned
        result = {"stopped": True, "owner": stop_owned(config.memory_dir, args.control)}
    elif action == "owner":
        from .owner import status
        result = {"owner": status(config.memory_dir)}
    elif action == "release":
        from .owner import release
        result = {"released": True, "owner": release(config.memory_dir, args.control)}
    elif action == "recover-owner":
        from .owner import recover
        result = {"recovered": True, "owner": recover(config.memory_dir, args.run_id,
                  owner_ended=args.owner_ended, publication_resolved=args.publication_resolved)}
    elif action == "rank":
        from .selection import select_scored
        result = select_scored(load_json_file(args.input), args.budget)
    elif action == "prompt":
        from .prompts import render_prompt
        result = render_prompt(config, args.receipt, args.control,
                               role=args.role, level=args.level, team=args.team,
                               stage=args.stage, stage_sha256=args.stage_sha256)
    elif action == "stage":
        from .stages import prepare_stage
        if not args.output:
            raise ValueError("memory stage requires --output for the new fixed stage package")
        return prepare_stage(config, args.receipt, args.control, args.handoff, args.output,
                             workers_ended=args.workers_ended, previous_stage=args.previous_stage,
                             available_subagents=args.available_subagents), 0
    elif action in ("retrieval-dispatch", "retrieval-prompt"):
        from .retrieval import retrieval_dispatch, render_retrieval_prompt
        render = retrieval_dispatch if action == "retrieval-dispatch" else render_retrieval_prompt
        result = render(config, args.request, slot=args.slot,
                        available_subagents=args.available_subagents, level=args.level)
    elif action == "collect":
        from .collection import collect
        result = collect(config, args.codex_registry, output=args.output)
        return ({"output": result["receipt"], "status": result["status"]} if args.output else result), 0
    elif action == "retrieval-receipt":
        from .retrieval import make_delivery_receipt
        result = make_delivery_receipt(config, args.request, load_json_file(args.ranked),
                                       load_json_file(args.candidates))
    elif action == "freshness":
        from .freshness import inspect_codex
        result = inspect_codex(config, registry_path=args.codex_registry, thread_id=args.thread)
    elif action == "retrieve":
        from .retrieval import prepare_retrieval
        result = prepare_retrieval(config, question=args.question, request_path=args.request,
                                   scope=args.scope, budget=args.budget, slot=args.slot,
                                   available_subagents=args.available_subagents, level=args.level)
    else:
        from .store import Memory
        memory = Memory(config)
        if action == "retrieval-start":
            from .retrieval import start_retrieval
            result = start_retrieval(memory, args.request)
        elif action == "behavior-train":
            options = {key: getattr(args, key) for key in ("epsilon", "beta", "strength")
                       if getattr(args, key) is not None}
            result = memory.train_behavior(rank=args.rank, **options)
        elif action == "behavior-compile":
            result = memory.compile_behavior()
        elif action == "behavior-candidates":
            result = memory.behavior_candidates(load_json_file(args.input), limit=args.limit, scope=args.scope)
        elif action == "publish":
            from .publish import publish
            return publish(memory, completed=load_json_file(args.completed) if args.completed else None,
                           output=args.output, frozen=args.frozen, control=args.control,
                           result=args.result, timeout=args.timeout), 0
        elif action == "feedback-report":
            from .feedback import report
            result = report(memory, kind=args.kind, issue=args.issue, target=args.target,
                            observed_revision=args.observed_revision, query=args.query,
                            source=args.source, reporter=args.reporter)
        elif action == "feedback-list":
            from .feedback import list_reports
            result = list_reports(memory, all_reports=args.all)
        elif action == "feedback-resolve":
            from .feedback import resolve
            result = resolve(memory, args.id, outcome=args.outcome, result=args.result,
                             expected_revision=args.expected_revision, control=args.control)
        elif action == "init":
            result = memory.install_schema()
            _activate(config)
        elif action == "sources":
            result = memory.sources()
        elif action == "prepare":
            result = memory.prepare(args.paths, historical_versions=(load_json_file(args.historical_versions)
                                                                    if args.historical_versions else None))
        elif action == "apply":
            result = memory.apply(json.loads(Path(args.batch).read_text(encoding="utf-8")),
                                  control=args.control, timeout=args.timeout)
        elif action == "embed":
            result = memory.embed_members(args.ids, timeout=args.timeout)
        elif action == "search":
            mode = args.mode if args.mode is not None else config.memory_search_mode
            if mode == "vector":
                if args.literal:
                    raise ValueError("--literal requires --mode hybrid; vector mode does not support literal matching.")
                result = memory.vector_search(args.text, scope=args.scope, limit=args.limit, timeout=args.timeout)
            else:
                result = memory.hybrid_search(args.text, scope=args.scope, limit=args.limit,
                                              timeout=args.timeout, literal=args.literal)
        elif action == "read":
            result = memory.read(args.id, knowledge_revision=args.knowledge_revision, source_version=args.source_version,
                                 start_line=args.start_line, end_line=args.end_line,
                                 locator=json.loads(args.locator) if args.locator else None)
        elif action == "neighbors":
            result = memory.neighbors(args.id, knowledge_revision=args.knowledge_revision, include_stale=args.include_stale)
        elif action == "knowledge":
            result = memory.knowledge(args.id, knowledge_revision=args.knowledge_revision)
        elif action == "history":
            result = memory.history(args.id)
        elif action == "access-hints":
            result = memory.access_hints(load_json_file(args.input))
        elif action == "delivery":
            receipt = load_json_file(args.input)
            result = memory.record_delivery(receipt["delivery_id"], receipt["items"], context=receipt.get("context"))
        elif action == "brief":
            result = memory.brief(task=args.task, limit=args.limit)
        elif action == "changes":
            result = memory.changes(args.scope, deep=args.deep)
    return _output(result, args.output), 0


def _output(result, output):
    if output:
        path = Path(output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"output": str(path)}
    return result


def _maintain(config, args, claim):
    """Consume selected originals; collection has its own outcome and no owner."""
    from .collection import load_collection, retained_snapshots
    from .discovery import discover_sources
    from .maintenance import check
    from .prompts import maintenance_layout, prompt_dispatch
    from .store import Memory

    control = claim["owner"]["control"]
    check(control)
    discovery = discover_sources(config, args.scope)
    binding = config.raw["memory"].get("codex", {})
    if args.collection:
        codex = load_collection(config, args.collection)
    elif args.retained:
        codex = retained_snapshots(config, binding.get("project_id"))
    elif binding.get("project_id"):
        raise ValueError("Select --collection <receipt> or --retained for this Codex-bound project")
    else:
        codex = {"status": "not_configured", "project_id": None, "paths": []}
    discovered_paths = discovery["paths"]
    if args.scope:
        from .query import normalize_scope
        prefixes = [normalize_scope(value) for value in args.scope]
        captured_paths = [path for path in codex["paths"]
                          if any(not prefix or path == prefix or path.startswith(prefix + "/") for prefix in prefixes)]
    else:
        captured_paths = codex["paths"]
    memory = Memory(config)
    registered_paths = ([row["path"] for row in memory.sources()
                         if any(not prefix or row["path"] == prefix or row["path"].startswith(prefix + "/")
                                for prefix in prefixes)] if args.scope else [])
    scope = list(dict.fromkeys([*discovered_paths, *captured_paths, *registered_paths]))
    result = memory.maintain(scope, control=control, timeout=args.timeout,
                             include_registered=args.scope is None)
    layout = maintenance_layout(config, mode=args.mode, available_subagents=args.available_subagents,
                                work_items=max(result["semantic_sources"], result["pending_relations"],
                                               result["feedback"]),
                                run_id=claim["owner"]["run_id"])
    codex_info = {key: value for key, value in codex.items() if key not in ("paths", "snapshots", "capture")}
    result.update(codex=codex_info, control=control, owner=claim["owner"], acquired=True, layout=layout,
                  discovery={"mode": discovery["mode"], "sources": len(scope), "gaps": discovery["gaps"]})
    receipt = Path(result["receipt"])
    material = json.loads(receipt.read_text(encoding="utf-8"))
    material.update(layout=layout, owner_run_id=claim["owner"]["run_id"],
                    codex={**codex_info, "capture_dir": str(config.memory_dir / "codex"),
                           "attachment_dir": str(config.memory_dir / "codex-attachments")},
                    discovery=result["discovery"])
    receipt.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding="utf-8")
    if result["needs_semantic"] and layout["teams"]:
        result["worker"] = prompt_dispatch(config, result["receipt"], control, layout=layout)
    elif result["needs_semantic"]:
        result["dispatch_blocked"] = "A coordinator, reader and reserved recovery seat are required; semantic work remains pending."
    return result


def _activate(config):
    from basepack.project.init import refresh_project_entry
    refresh_project_entry(config.root, config.path, config.python,
                          memory_enabled=True, memory_dir=config.memory_dir)
