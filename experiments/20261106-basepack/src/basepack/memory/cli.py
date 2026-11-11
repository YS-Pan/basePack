"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import json
from pathlib import Path


def register_commands(subparsers):
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory")
    commands = memory.add_subparsers(dest="memory_action", required=True)
    actions = {name: commands.add_parser(name) for name in
               ("init", "guide", "sources", "prepare", "apply", "stop", "owner", "release", "recover-owner", "embed", "search", "read", "neighbors", "brief", "changes", "maintain", "prompt", "rank", "feedback-report", "feedback-list", "feedback-resolve")}
    actions["feedback-report"].add_argument("--kind", choices=["knowledge", "retrieval"], required=True)
    actions["feedback-report"].add_argument("--issue", required=True)
    actions["feedback-report"].add_argument("--target", help="Member, node or semantic edge ID")
    actions["feedback-report"].add_argument("--observed-revision", help="Version returned when the target was observed")
    actions["feedback-report"].add_argument("--query", help="Query, including for missed results")
    actions["feedback-report"].add_argument("--source", help="Original location or source clue")
    actions["feedback-report"].add_argument("--reporter", help="Reporting agent or worker")
    actions["feedback-list"].add_argument("--all", action="store_true", help="Include resolved reports")
    actions["feedback-resolve"].add_argument("id", help="Feedback report ID")
    actions["feedback-resolve"].add_argument("--outcome", choices=["fixed", "invalid", "duplicate", "obsolete"], required=True)
    actions["feedback-resolve"].add_argument("--result", required=True)
    actions["feedback-resolve"].add_argument("--control", required=True, help="Current maintenance owner's control file")
    actions["feedback-resolve"].add_argument("--expected-revision", help="Target version confirmed after handling")
    actions["prepare"].add_argument("--paths", nargs="+", required=True,
                                    help="Project-relative files; enumerate directories first")
    actions["apply"].add_argument("--batch", required=True, help="Agent-produced UTF-8 JSON batch")
    actions["apply"].add_argument("--control", required=True, help="Current owner control file")
    actions["apply"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["stop"].add_argument("--control", required=True, help="The task's unique control file")
    actions["release"].add_argument("--control", required=True, help="Stopped owner control file")
    actions["recover-owner"].add_argument("--run-id", required=True)
    actions["recover-owner"].add_argument("--owner-ended", action="store_true", required=True, help="Attest that the previous owner and workers have ended")
    actions["recover-owner"].add_argument("--publication-resolved", action="store_true", required=True, help="Attest that each publication result has been verified")
    actions["search"].add_argument("--text", required=True)
    actions["search"].add_argument("--scope", default="")
    actions["search"].add_argument("--limit", type=int, default=12)
    actions["search"].add_argument("--literal", action="store_true", help="With hybrid: prioritize case-insensitive path/title/text substring matches")
    actions["search"].add_argument("--mode", choices=["hybrid", "vector"],
                                 help="Override memory.search_mode from the project config")
    actions["search"].add_argument("--timeout", type=float, default=600)
    actions["embed"].add_argument("--ids", nargs="+", help="Member IDs; otherwise index current representations")
    actions["embed"].add_argument("--timeout", type=float, default=600)
    actions["read"].add_argument("id", help="Member ID; follow a knowledge node's evidence via neighbors")
    actions["read"].add_argument("--source-version", help="Read an evidence source_version")
    actions["read"].add_argument("--start-line", type=int, help="Evidence start line (inclusive)")
    actions["read"].add_argument("--end-line", type=int, help="Evidence end line (inclusive)")
    actions["read"].add_argument("--locator", help="Image evidence locator as a JSON object")
    actions["neighbors"].add_argument("id")
    actions["neighbors"].add_argument("--include-stale", action="store_true", help="Explicit historical inspection")
    actions["brief"].add_argument("--task", default="")
    actions["brief"].add_argument("--limit", type=int, default=6)
    actions["changes"].add_argument("--scope", nargs="+", required=True)
    actions["changes"].add_argument("--deep", action="store_true")
    actions["maintain"].add_argument("--scope", nargs="+", help="Override new-file discovery; registered sources and pending relations remain included")
    actions["maintain"].add_argument("--codex-registry", help="Host project binding and complete registered roots as UTF-8 JSON")
    actions["maintain"].add_argument("--control", required=True, help="Fresh, never-used task control file")
    actions["maintain"].add_argument("--holder", required=True, help="Host thread identity")
    actions["maintain"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["prompt"].add_argument("--receipt", required=True, help="Maintenance receipt to render as worker context")
    actions["prompt"].add_argument("--control", required=True, help="The same task control file used by maintain and apply")
    actions["prompt"].add_argument("--role", choices=["coordinator", "reader"], default="coordinator")
    actions["prompt"].add_argument("--tier", choices=["tier1", "tier2", "tier3", "tier4"],
                               help="Override the role's default AI tier")
    actions["prompt"].add_argument("--paths", nargs="+", help="Reader's bounded project-relative source files")
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for name, command in actions.items():
        if name == "prompt":
            command.set_defaults(output=None)
        else:
            command.add_argument("--output", help="Write JSON here and return its location")


def dispatch(args, config):
    action = args.memory_action
    if action == "maintain":
        from .owner import acquire
        claim = acquire(config.memory_dir, config.raw["memory"]["project_id"], args.holder, args.control)
        if not claim["acquired"]:
            if args.output:
                path = Path(args.output).resolve()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(claim, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"output": str(path)}, 0
            return claim, 0
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
        result = select_scored(json.loads(Path(args.input).read_text(encoding="utf-8")), args.budget)
    elif action == "prompt":
        from .prompts import render_prompt
        result = render_prompt(config, args.receipt, args.control,
                               role=args.role, tier=args.tier, paths=args.paths)
    else:
        from .store import Memory
        memory = Memory(config)
        if action == "feedback-report":
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
            result = memory.prepare(args.paths)
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
            result = memory.read(args.id, source_version=args.source_version,
                                 start_line=args.start_line, end_line=args.end_line,
                                 locator=json.loads(args.locator) if args.locator else None)
        elif action == "neighbors":
            result = memory.neighbors(args.id, include_stale=args.include_stale)
        elif action == "brief":
            result = memory.brief(task=args.task, limit=args.limit)
        elif action == "changes":
            result = memory.changes(args.scope, deep=args.deep)
        elif action == "maintain":
            from .discovery import discover_sources, retained_codex_paths
            from .maintenance import check
            from .prompts import prompt_dispatch
            control = claim["owner"]["control"]
            check(control)
            discovery = discover_sources(config, args.scope)
            codex = _collect_codex(config, args.codex_registry, control=control)
            retained = retained_codex_paths(config, codex["project_id"])
            scope = list(dict.fromkeys([*discovery["paths"], *codex.pop("paths", []), *retained["paths"]]))
            codex["retained_sources"] = len(retained["paths"])
            codex["retained_gaps"] = retained["gaps"]
            result = memory.maintain(scope, control=control, timeout=args.timeout)
            result["codex"] = codex
            result["control"] = control
            result["owner"] = claim["owner"]
            result["acquired"] = True
            result["discovery"] = {"mode": discovery["mode"], "sources": len(scope),
                                   "gaps": discovery["gaps"]}
            if result["needs_semantic"]:
                receipt = Path(result["receipt"])
                material = json.loads(receipt.read_text(encoding="utf-8"))
                material["codex"] = {"project_id": codex["project_id"],
                                     "capture_dir": str(config.memory_dir / "codex"),
                                     "attachment_dir": str(config.memory_dir / "codex-attachments")}
                if "receipt" in codex:
                    material["codex"]["receipt"] = codex["receipt"]
                receipt.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding="utf-8")
                result["worker"] = prompt_dispatch(config, result["receipt"], control)
    if args.output:
        path = Path(args.output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"output": str(path)}, 0
    return result, 0


def _collect_codex(config, registry_path, *, control=None):
    """Capture provably assigned threads; leave unavailable binding explicit."""
    import os
    from uuid import uuid4
    from .codex import AppServer, collect_codex, list_threads
    from .codex_binding import classify_threads, discover_binding

    binding = (json.loads(Path(registry_path).read_text(encoding="utf-8")) if registry_path
               else config.raw["memory"].get("codex", {}))
    if not binding.get("project_id") or not binding.get("registry_complete"):
        return {"status": "binding_unavailable", "project_id": binding.get("project_id"), "paths": [],
                "gap": "Host project ID and complete registered project roots are required."}
    resolved = discover_binding(config.root, binding["project_id"], binding["other_project_roots"])
    client = AppServer(os.environ.get("CODEX_APP_RUNTIME_CLI_PATH", "codex"))
    try:
        discovered = classify_threads(resolved, list_threads(client, control=control))
        captured = collect_codex(binding["project_id"], [row["id"] for row in discovered["matched"]],
                                 config.memory_dir / "codex", control=control, client=client,
                                 project_binding=resolved)
    finally:
        client.close()
    root = config.root.resolve()
    paths = [Path(path).relative_to(root).as_posix() for path in captured["paths"]]
    def identifiers(rows):
        return [{"thread_id": row["thread"]["id"], "reason": row["reason"]} for row in rows]
    details = {"binding": resolved, "unresolved": identifiers(discovered["unresolved"]),
               "excluded": identifiers(discovered["excluded"]), "capture": captured}
    directory = config.memory_dir / "maintenance"
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / f"codex-{uuid4().hex}.json"
    receipt.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "captured", "project_id": binding["project_id"], "discovered": len(discovered["matched"]),
            "unresolved": len(discovered["unresolved"]), "gaps": len(discovered["gaps"]) + len(captured["gaps"]),
            "receipt": str(receipt), "paths": paths}


def _activate(config):
    from basepack.project.init import refresh_project_entry
    refresh_project_entry(config.root, config.path, config.python,
                          memory_enabled=True, memory_dir=config.memory_dir)
