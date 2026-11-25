"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import argparse
import json
from pathlib import Path


_LOCAL_ACTIONS = frozenset({
    "guide", "rank", "freeze", "stop", "owner", "release", "recover-owner",
    "prompt", "stage", "maintain-start", "collect-prompt", "collect", "check-codex-capture", "codex-trial", "dialogue-register",
    "retrieve", "retrieval-dispatch", "retrieval-prompt", "retrieval-receipt",
})

_COMMAND_GROUPS = (
    ("Everyday queries", (
        ("brief", "Read published startup knowledge and known gaps."),
        ("search", "Search published knowledge."),
        ("retrieve", "Prepare a retrieval assignment for the host to launch."),
        ("graph-query", "Find versioned evidence and relationships in a bounded graph round."),
        ("read", "Read member evidence or a verified Codex dialogue location."),
        ("read-source", "Read a retained original snapshot at its exact location."),
        ("knowledge", "Inspect an accepted knowledge record."),
        ("history", "List retained knowledge versions."),
        ("neighbors", "Follow evidence and relationships."),
        ("graph-coverage", "Count fresh knowledge vertices touched by business relationships."),
        ("basis-dependents", "Find current knowledge that cites exact member versions."),
        ("guide", "Locate the installed memory guide."),
    )),
    ("Sources", (
        ("check-codex-capture", "Compare active and archived project Codex chats with capture records."),
        ("dialogue-register", "Register one verified current-project dialogue as private."),
        ("dialogue-coverage", "Report authorized dialogue indexing coverage without original text."),
        ("dialogue-locations", "List indexed message locations for an authorized dialogue node."),
        ("check-file-changes", "Compare selected files with registered source versions."),
        ("inventory", "Inspect project originals and suggest source groups without starting maintenance."),
        ("sources", "List registered project sources."),
        ("collect", "Capture Codex originals."),
        ("codex-trial", "Reserve trial creation and exclude registered trial chats from collection."),
        ("prepare", "Prepare fixed source evidence and observed knowledge versions."),
    )),
    ("Maintenance and publication", (
        ("maintain-start", "Prepare a coordinator assignment for the host to launch."),
        ("maintain", "Run maintenance preflight and prepare work for the coordinator."),
        ("publish", "Publish completed drafts or resume the same frozen batch."),
        ("freeze", "Compile drafts into a fixed batch."),
        ("apply", "Apply a frozen batch."),
        ("embed", "Index current knowledge representations."),
        ("feedback-report", "Record a knowledge or retrieval issue."),
        ("feedback-list", "List memory feedback."),
        ("feedback-resolve", "Record the owner's result for a feedback report."),
    )),
    ("Host protocol", (
        ("wave", "Manage a host-driven finite maintenance wave."),
        ("stage", "Prepare a maintenance handoff."),
        ("prompt", "Render the maintenance coordinator prompt."),
        ("collect-prompt", "Render the delegated collection prompt."),
        ("retrieval-dispatch", "Plan execution of a prepared retrieval request."),
        ("retrieval-prompt", "Render the retrieval worker prompt."),
        ("retrieval-start", "Fix the base retrieval results for a request."),
        ("retrieval-receipt", "Prepare a delivery receipt."),
        ("rank", "Select scored results within a content budget."),
        ("delivery", "Record host-confirmed delivery."),
        ("access-hints", "Read access hints for observed knowledge versions."),
        ("behavior-train", "Train the retrieval behavior model."),
        ("behavior-compile", "Compile retrieval behavior state."),
        ("behavior-candidates", "Expand candidates from fixed retrieval anchors."),
    )),
    ("Setup and recovery", (
        ("init", "Initialize or verify project memory."),
        ("owner", "Inspect the current maintenance owner."),
        ("stop", "Stop a maintenance attempt or owner."),
        ("release", "Release a stopped maintenance owner."),
        ("recover-owner", "Recover ownership after verifying host and publication outcomes."),
    )),
)

_ALIASES = {"check-codex-capture": ("freshness",), "check-file-changes": ("changes",)}


def register_commands(subparsers):
    overview = "\n\n".join(
        f"{heading}:\n" + "\n".join(f"  {name:<21} {summary}" for name, summary in group)
        for heading, group in _COMMAND_GROUPS
    )
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory",
                                  formatter_class=argparse.RawDescriptionHelpFormatter,
                                  epilog=overview)
    commands = memory.add_subparsers(dest="memory_action", metavar="COMMAND", required=True)
    actions = {}
    for _, group in _COMMAND_GROUPS:
        for name, summary in group:
            command = commands.add_parser(name, aliases=_ALIASES.get(name, ()), description=summary)
            if name in _ALIASES:
                command.set_defaults(memory_action=name)
            actions[name] = command
    from .wave_cli import register as register_waves
    register_waves(actions.pop("wave"))
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
    actions["collect"].add_argument("--thread", action="append",
                                    help="Collect this project-owned chat and its verified descendants; repeat as needed")
    actions["collect"].add_argument("--attempt", help="Parent's delegated maintenance attempt ID")
    trials = actions["codex-trial"].add_subparsers(dest="trial_action", required=True)
    trials.add_parser("status", help="Inspect the formal collection trial registry")
    trials.add_parser("begin", help="Pause fresh formal collection before creating a trial chat")
    registered = trials.add_parser("register", help="Exclude the created trial root and resume formal collection")
    registered.add_argument("--reservation", required=True, help="Pending token returned by begin")
    registered.add_argument("--thread", required=True, help="Confirmed Codex trial chat UUID")
    cancelled = trials.add_parser("cancel", help="Resume formal collection after verifying no chat was created")
    cancelled.add_argument("--reservation", required=True, help="Pending token returned by begin")
    actions["init"].add_argument("--no-project-entry", action="store_true",
                                 help="Install the schema without refreshing project instructions")
    actions["collect-prompt"].add_argument("--attempt", required=True, help="Attempt ID returned by maintain-start")
    actions["prepare"].add_argument("--paths", nargs="+", required=True,
                                    help="Project-relative files; enumerate directories first")
    actions["prepare"].add_argument("--historical-versions", help="JSON array of explicitly observed historical {id, knowledge_revision}")
    actions["prepare"].add_argument("--expected-revisions", help="JSON object of fixed project paths and raw revisions, or null for a missing original")
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
    stopping = actions["stop"].add_mutually_exclusive_group(required=True)
    stopping.add_argument("--control", help="The task's unique control file")
    stopping.add_argument("--attempt", help="Cancel a delegated attempt, even before it acquires ownership")
    actions["release"].add_argument("--control", required=True, help="Stopped owner control file")
    actions["recover-owner"].add_argument("--run-id", required=True)
    actions["recover-owner"].add_argument("--owner-ended", action="store_true", required=True, help="Attest that the previous owner and workers have ended")
    actions["recover-owner"].add_argument("--publication-resolved", action="store_true", required=True, help="Attest that each publication result has been verified")
    actions["search"].add_argument("--text", required=True)
    actions["search"].add_argument("--scope", default="", help="Project-relative path prefix; empty searches the whole project. Put business constraints in --text")
    actions["search"].add_argument("--limit", type=int, default=12)
    actions["search"].add_argument("--literal", action="store_true", help="With hybrid: prioritize case-insensitive path/title/text substring matches")
    actions["search"].add_argument("--public-only", action="store_true", help="Search and report only explicitly public material")
    actions["search"].add_argument("--mode", choices=["hybrid", "vector"],
                                 help="Override memory.search_mode from the project config")
    actions["search"].add_argument("--timeout", type=float, default=600)
    actions["embed"].add_argument("--ids", nargs="+", help="Member IDs; otherwise index current representations")
    actions["embed"].add_argument("--timeout", type=float, default=600)
    actions["read"].add_argument("id", help="Member ID or codex_chunk ID")
    actions["read"].add_argument("--knowledge-revision", help="Read the observed knowledge version, including its original evidence")
    actions["read"].add_argument("--source-version", help="Read an original evidence snapshot; use --knowledge-revision for the old accepted representation")
    actions["read"].add_argument("--start-line", type=int, help="Evidence start line (inclusive)")
    actions["read"].add_argument("--end-line", type=int, help="Evidence end line (inclusive)")
    actions["read"].add_argument("--locator", help="Text-column or image evidence locator as a JSON object")
    actions["read"].add_argument("--include-private", action="store_true",
                                 help="Include explicitly authorized private dialogue evidence")
    actions["read"].add_argument("--context", type=int, default=1, help="Nearby Codex message parts to read")
    registration = actions["dialogue-register"]
    registration.add_argument("thread_id", help="Canonical UUID of an ordinary current-project dialogue")
    registration.add_argument("--binding", help="Current-project manifest key when more than one key matches")
    dialogue = actions["dialogue-locations"]
    dialogue.add_argument("id", help="Observed dialogue node ID")
    dialogue.add_argument("--knowledge-revision", help="Observed dialogue node revision")
    dialogue.add_argument("--limit", type=int, default=30)
    dialogue.add_argument("--offset", type=int, default=0)
    for name in ("dialogue-coverage", "dialogue-locations"):
        actions[name].add_argument("--scope", default="", help="Project-relative scope prefix")
        actions[name].add_argument("--include-private", action="store_true",
                                   help="Include explicitly authorized private dialogue metadata")
    graph = actions["graph-query"]
    graph.add_argument("--request", help="Reuse a prepared retrieval request and record this round's observations")
    graph.add_argument("--text", help="This round's question or search terms")
    graph.add_argument("--seed", action="append", default=[], help="Named logical or exact record ID; repeat as needed")
    graph.add_argument("--seed-versions", help="UTF-8 JSON array of {id, knowledge_revision} for explicitly observed versions")
    graph.add_argument("--branch", action="append", default=[], help="Follow in:TYPE or out:TYPE; repeat as needed")
    graph.add_argument("--conditions", help="Known conditions as a JSON object to exclude conflicting structured values")
    graph.add_argument("--scope", help="Graph round's project-relative path prefix")
    graph.add_argument("--include-private", action="store_true", help="Include private evidence when authorized")
    graph.add_argument("--include-stale", action="store_true", help="Follow non-current edges for historical inspection")
    graph.add_argument("--literal", action="store_true", help="Prioritize literal matches when selecting hybrid-search seeds")
    original = actions["read-source"]
    original.add_argument("id", help="Exact source_version ID")
    original.add_argument("--start-line", type=int, help="Evidence start line (inclusive)")
    original.add_argument("--end-line", type=int, help="Evidence end line (inclusive)")
    original.add_argument("--locator", help="Text-column or image evidence locator as a JSON object")
    original.add_argument("--scope", default="", help="Project-relative path prefix")
    original.add_argument("--include-private", action="store_true", help="Include private evidence when authorized")
    actions["neighbors"].add_argument("id")
    actions["neighbors"].add_argument("--knowledge-revision", help="Expand the observed knowledge version")
    actions["neighbors"].add_argument("--include-stale", action="store_true", help="Explicit historical inspection")
    actions["neighbors"].add_argument("--direction", choices=["in", "out", "both"], default="both")
    actions["neighbors"].add_argument("--type", action="append", default=[], help="Published edge type; repeat as needed")
    actions["neighbors"].add_argument("--conditions", help="Known conditions as a JSON object to exclude conflicting structured values")
    actions["neighbors"].add_argument("--scope", default="", help="Project-relative path prefix")
    actions["neighbors"].add_argument("--include-private", action="store_true", help="Include private evidence when authorized")
    actions["basis-dependents"].add_argument("--anchors", required=True,
                                             help="UTF-8 JSON array of observed {id, knowledge_revision, source_version} member records")
    actions["basis-dependents"].add_argument("--scope", default="", help="Scope anchors, dependents and evidence to this project-relative path prefix")
    actions["basis-dependents"].add_argument("--public-only", action="store_true", help="Require explicitly public anchors, dependents and evidence")
    actions["knowledge"].add_argument("id", help="Member, node or semantic relation ID")
    actions["knowledge"].add_argument("--knowledge-revision", help="Observed knowledge version; default is current")
    for name in ("read", "knowledge"):
        actions[name].add_argument("--scope", default="", help="Require the exact version to match this project-relative path prefix")
        actions[name].add_argument("--public-only", action="store_true", help="Require the exact version to be explicitly public")
    actions["history"].add_argument("id", help="List retained knowledge versions and actual history coverage")
    actions["delivery"].add_argument("--input", required=True, help="Host-confirmed final receipt: delivery_id, items [{id, knowledge_revision}], optional context")
    actions["access-hints"].add_argument("--input", required=True, help="UTF-8 JSON array of observed {id, knowledge_revision} records")
    actions["brief"].add_argument("--task", default="", help="Task label only; brief directly reads published startup knowledge without search or embedding")
    actions["brief"].add_argument("--limit", type=int, default=6)
    file_check = actions["check-file-changes"]
    file_check.add_argument("--scope", nargs="+", required=True, help="Project-relative files or directories")
    file_check.add_argument("--deep", action="store_true", help="Verify file content hashes")
    actions["inventory"].add_argument("--collection", help="Existing verified collection receipt; otherwise inspect retained originals")
    actions["inventory"].add_argument("--group-map", help="Project-relative source grouping manifest")
    for name in ("maintain", "maintain-start"):
        maintain = actions[name]
        maintain.add_argument("--scope", nargs="+", help="Restrict the actual workset to these project-relative paths")
        captured = maintain.add_mutually_exclusive_group()
        captured.add_argument("--collection", help="Verified receipt from independent memory collect")
        captured.add_argument("--retained", action="store_true", help="Explicitly consume retained chat snapshots; freshness remains unknown")
        if name == "maintain-start":
            captured.add_argument("--allow-retained", action="store_true",
                                  help="Permit the coordinator to use retained originals if fresh collection is unavailable")
        maintain.add_argument("--holder", required=True, help="Original parent's host thread identity")
        maintain.add_argument("--mode", choices=["automatic", "manual"], default="manual",
                              help="Both modes reserve one coordinator recovery seat; default is manual")
        maintain.add_argument("--available-subagents", type=int,
                              help="Host raw subagent seats before counting the maintenance coordinator and recovery reserve")
    actions["maintain"].add_argument("--control", required=True, help="Fresh, never-used task control file")
    actions["maintain"].add_argument("--attempt", help="Attempt ID for an already-started coordinator")
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
    retrieve.add_argument("--include-private", action="store_true", help="Authorize private evidence within this retrieval")
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
    capture_check = actions["check-codex-capture"]
    capture_check.add_argument("--codex-registry", help="Host project binding and complete registered roots as UTF-8 JSON")
    capture_check.add_argument("--thread", help="Read and compare the text of one project-owned chat by ID")
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for name, command in actions.items():
        if name in ("collect-prompt", "prompt", "retrieval-dispatch", "retrieval-prompt"):
            command.set_defaults(output=None)
        else:
            command.add_argument("--output", help=("New frozen batch path (requires --completed)" if name == "publish"
                                                  else "Write JSON here and return its location"))


def dispatch(args, config):
    action = args.memory_action
    if (action in {"dialogue-register", "dialogue-coverage", "dialogue-locations"}
            or (action == "read" and args.id.startswith("codex_chunk:"))):
        from .codex_index_config import configured

        if not configured(config):
            raise PermissionError("Codex dialogue index is disabled for this project")
    if action == "maintain":
        return _dispatch_maintain(args, config)
    if action in _LOCAL_ACTIONS or (action == "wave" and args.wave_action != "publish"):
        return _dispatch(args, config)
    from ..runtime.activity import memory_operation

    with memory_operation(config):
        return _dispatch(args, config)


def _dispatch_maintain(args, config):
    from ..runtime.activity import memory_operation
    from ..runtime.recovery import managed
    from .owner import acquire, check_attempt, release_failed_startup, status

    is_managed = managed(config, "memory")
    if is_managed:
        if args.attempt is not None:
            check_attempt(config.memory_dir, args.attempt)
        current = status(config.memory_dir)
        if current is not None:
            return _output({"acquired": False, "owner": current}, args.output), 0

    with memory_operation(config):
        memory = None
        if is_managed:
            from .store import Memory

            memory = Memory(config)
            memory.verify_project()

        claim = acquire(config.memory_dir, config.raw["memory"]["project_id"], args.holder, args.control,
                        attempt_id=args.attempt)
        if not claim["acquired"]:
            return _output(claim, args.output), 0
        try:
            result = _maintain(config, args, claim, memory=memory)
            return _output(result, args.output), 0
        except Exception as error:
            try:
                release_failed_startup(config.memory_dir, args.control, claim["owner"]["run_id"])
            except Exception as cleanup_error:
                raise ExceptionGroup("Maintenance startup and ownership cleanup failed",
                                     [error, cleanup_error]) from error
            raise


def _dispatch(args, config):
    from .query import load_json_file

    action = args.memory_action
    if action in {"collect", "collect-prompt", "check-codex-capture"}:
        from .codex_index_config import configured

        if configured(config):
            raise ValueError("Legacy Codex capture is unavailable in dialogue-index mode")
    if action == "wave":
        from .wave_cli import dispatch as dispatch_wave
        return dispatch_wave(config, args), 0
    if action == "freeze":
        from .draft import freeze_file, read_author_draft
        if not args.output:
            raise ValueError('memory freeze requires --output for the frozen batch')
        path = Path(args.output).resolve()
        batch = freeze_file([read_author_draft(draft) for draft in args.drafts], path, config=config)
        return {"output": str(path), "batch_id": batch['batch_id']}, 0
    if action == "guide":
        result = {"skill": str(Path(__file__).with_name("SKILL.md"))}
    elif action == "stop":
        from .owner import cancel_attempt, stop_owned
        result = (cancel_attempt(config.memory_dir, args.attempt) if args.attempt is not None else
                  {"stopped": True, "owner": stop_owned(config.memory_dir, args.control)})
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
    elif action == "maintain-start":
        from .prompts import maintenance_start
        result = maintenance_start(config, holder=args.holder, mode=args.mode,
                                   available_subagents=args.available_subagents, scope=args.scope,
                                   collection=args.collection, retained=args.retained,
                                   allow_retained=args.allow_retained)
    elif action == "collect-prompt":
        from .prompts import render_collection_prompt
        result = render_collection_prompt(config, args.attempt)
    elif action == "collect":
        from .collection import collect
        options = {"attempt_id": args.attempt} if args.attempt is not None else {}
        if args.thread is not None:
            options["thread_ids"] = args.thread
        result = collect(config, args.codex_registry, output=args.output, **options)
        return ({"output": result["receipt"], "status": result["status"]} if args.output else result), 0
    elif action == "codex-trial":
        from .collection import codex_trial
        return codex_trial(config, args.trial_action, reservation=getattr(args, "reservation", None),
                           thread_id=getattr(args, "thread", None)), 0
    elif action == "dialogue-register":
        from .codex_index_config import register_thread
        if args.output is not None:
            raise ValueError("Dialogue registration writes its receipt to standard output")
        return register_thread(config, args.thread_id, binding=args.binding), 0
    elif action == "retrieval-receipt":
        from .retrieval import make_delivery_receipt
        result = make_delivery_receipt(config, args.request, load_json_file(args.ranked),
                                       load_json_file(args.candidates))
    elif action == "check-codex-capture":
        from .freshness import inspect_codex
        result = inspect_codex(config, registry_path=args.codex_registry, thread_id=args.thread)
    elif action == "retrieve":
        from .retrieval import prepare_retrieval
        result = prepare_retrieval(config, question=args.question, request_path=args.request,
                                   scope=args.scope, budget=args.budget, slot=args.slot,
                                   available_subagents=args.available_subagents, level=args.level,
                                   allow_private=args.include_private)
    else:
        from .store import Memory
        memory = Memory(config)
        if action == "retrieval-start":
            from .retrieval import start_retrieval
            result = start_retrieval(memory, args.request)
        elif action == "graph-query":
            from .graph_retrieval import graph_query
            from .retrieval import retrieval_graph_round
            versions = load_json_file(args.seed_versions) if args.seed_versions else []
            if not isinstance(versions, list):
                raise ValueError("--seed-versions must contain a JSON array")
            options = {"seeds": [*args.seed, *versions], "branches": args.branch, "literal": args.literal,
                       "include_stale": args.include_stale, "allow_private": args.include_private,
                       "conditions": json.loads(args.conditions) if args.conditions is not None else None}
            result = (retrieval_graph_round(memory, args.request, text=args.text, scope=args.scope, **options)
                      if args.request else graph_query(memory, args.text or "", scope=args.scope or "", **options))
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
            if not args.no_project_entry:
                _activate(config)
        elif action == "sources":
            result = memory.sources()
        elif action == "inventory":
            from .inventory_work import inventory_report
            result = inventory_report(config, memory, collection=args.collection, group_map_path=args.group_map)
        elif action == "dialogue-coverage":
            from .codex_index import coverage
            from .codex_index_config import visible_threads
            from .dialogue_query import authorized_ancestry

            allowed = visible_threads(config, scope=args.scope, allow_private=args.include_private)
            result = coverage(memory, list(allowed))
            result["threads"] = [row for row in result["threads"]
                                 if (args.include_private or not row.get("private", False))
                                 and row.get("path", allowed[row["thread_id"]]["path"]) == allowed[row["thread_id"]]["path"]
                                 and (row["status"] == "not_indexed"
                                      or authorized_ancestry(config, row["thread_id"], row.get("ancestor_thread_ids")))]
        elif action == "dialogue-locations":
            from .dialogue_query import dialogue_locations

            result = dialogue_locations(memory, args.id, knowledge_revision=args.knowledge_revision,
                                        scope=args.scope, allow_private=args.include_private,
                                        limit=args.limit, offset=args.offset)
        elif action == "prepare":
            options = {}
            if args.expected_revisions is not None:
                options["expected_revisions"] = json.loads(args.expected_revisions)
            result = memory.prepare(args.paths, historical_versions=(load_json_file(args.historical_versions)
                                                                    if args.historical_versions else None),
                                    **options)
        elif action == "apply":
            result = memory.apply(json.loads(Path(args.batch).read_text(encoding="utf-8")),
                                  control=args.control, timeout=args.timeout)
        elif action == "embed":
            result = memory.embed_members(args.ids, timeout=args.timeout)
        elif action == "search":
            mode = args.mode if args.mode is not None else config.memory_search_mode
            visibility = {"allow_private": False} if args.public_only else {}
            if mode == "vector":
                if args.literal:
                    raise ValueError("--literal requires --mode hybrid; vector mode does not support literal matching.")
                result = memory.vector_search(args.text, scope=args.scope, limit=args.limit, timeout=args.timeout,
                                              **visibility)
            else:
                result = memory.hybrid_search(args.text, scope=args.scope, limit=args.limit,
                                              timeout=args.timeout, literal=args.literal, **visibility)
        elif action == "read" and args.id.startswith("codex_chunk:"):
            from types import SimpleNamespace
            from .codex_index_route import read_host
            from .dialogue_query import read_chunk

            if args.output:
                raise ValueError("Codex original text is only available on standard output")
            if any(value is not None for value in (args.knowledge_revision, args.source_version,
                                                   args.start_line, args.end_line, args.locator)):
                raise ValueError("A Codex chunk ID already fixes the exact original location")
            if args.public_only and args.include_private:
                raise ValueError("Choose either --public-only or --include-private")
            host = SimpleNamespace(read=lambda bookmark, *, context: read_host(config, bookmark, context=context))
            result = read_chunk(memory, args.id, host=host, scope=args.scope,
                                allow_private=args.include_private, context=args.context)
        elif action == "read":
            revision = args.knowledge_revision
            record_id = args.id
            if args.scope or args.public_only:
                row = _visible_record(memory, args.id, revision, scope=args.scope, public_only=args.public_only)
                if row["record_type"] != "member":
                    raise ValueError("read requires a member ID")
                record_id, revision = row["id"], row["knowledge_revision"]
                _visible_record(memory, args.source_version or row["source_version"], None,
                                scope=args.scope, public_only=args.public_only)
            result = memory.read(record_id, knowledge_revision=revision, source_version=args.source_version,
                                 start_line=args.start_line, end_line=args.end_line,
                                 locator=json.loads(args.locator) if args.locator else None)
            if args.scope or args.public_only:
                from .graph_query_store import filter_record_details
                result["member"] = filter_record_details(memory, result["member"], scope=args.scope,
                                                         allow_private=not args.public_only)
        elif action == "read-source":
            from .graph_query_store import read_source_version
            result = read_source_version(memory, args.id, scope=args.scope, allow_private=args.include_private,
                                         start_line=args.start_line, end_line=args.end_line,
                                         locator=json.loads(args.locator) if args.locator else None)
        elif action == "neighbors":
            result = memory.neighbors(args.id, knowledge_revision=args.knowledge_revision, include_stale=args.include_stale,
                                      direction=args.direction, types=args.type, scope=args.scope,
                                      allow_private=args.include_private,
                                      conditions=json.loads(args.conditions) if args.conditions is not None else None)
        elif action == "graph-coverage":
            from .graph_coverage import coverage
            result = coverage(memory)
        elif action == "basis-dependents":
            result = memory.basis_dependents(load_json_file(args.anchors), scope=args.scope,
                                             allow_private=not args.public_only)
        elif action == "knowledge":
            revision = args.knowledge_revision
            record_id = args.id
            if args.scope or args.public_only:
                row = _visible_record(memory, args.id, revision, scope=args.scope, public_only=args.public_only)
                if args.id.startswith(("member:", "node:", "semantic:")):
                    revision = row["knowledge_revision"]
                else:
                    record_id = row["exact_id"]
            result = memory.knowledge(record_id, knowledge_revision=revision)
            if args.scope or args.public_only:
                from .graph_query_store import filter_record_details
                result = filter_record_details(memory, result, scope=args.scope, allow_private=not args.public_only)
        elif action == "history":
            result = memory.history(args.id)
        elif action == "access-hints":
            result = memory.access_hints(load_json_file(args.input))
        elif action == "delivery":
            receipt = load_json_file(args.input)
            result = memory.record_delivery(receipt["delivery_id"], receipt["items"], context=receipt.get("context"))
        elif action == "brief":
            result = memory.brief(task=args.task, limit=args.limit)
        elif action == "check-file-changes":
            result = memory.changes(args.scope, deep=args.deep)
    return _output(result, args.output), 0


def _visible_record(memory, identifier, revision, *, scope, public_only):
    from .graph_query_store import get_vertex, resolve_seed
    from .query import normalize_scope

    scope = normalize_scope(scope)
    exact = resolve_seed(memory, identifier, knowledge_revision=revision)
    row = get_vertex(memory, exact, scope=scope, allow_private=not public_only) if exact is not None else None
    if row is None:
        raise ValueError("Exact record unavailable within the requested scope and visibility")
    return row


def _output(result, output):
    if output:
        path = Path(output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"output": str(path)}
    return result


def _maintain(config, args, claim, *, memory=None):
    """Consume selected originals; collection has its own outcome and no owner."""
    from .collection import load_collection, retained_snapshots
    from .codex_index_config import configured, legacy_capture_path
    from .discovery import discover_sources
    from .maintenance import check
    from .prompts import maintenance_layout, prompt_dispatch
    from .store import Memory

    control = claim["owner"]["control"]
    check(control)
    discovery = discover_sources(config, args.scope)
    binding = config.raw["memory"].get("codex", {})
    indexed = configured(config)
    if indexed:
        if args.collection is not None or args.retained:
            raise ValueError("Dialogue indexing cannot use --collection or --retained")
        codex = {"status": "indexed", "paths": []}
    elif args.collection:
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
    if memory is None:
        memory = Memory(config)
    registered_paths = ([row["path"] for row in memory.sources()
                         if any(not prefix or row["path"] == prefix or row["path"].startswith(prefix + "/")
                                for prefix in prefixes)] if args.scope else [])
    scope = list(dict.fromkeys([*discovered_paths, *captured_paths, *registered_paths]))
    if indexed:
        scope = [path for path in scope if not legacy_capture_path(config, path)]
    selected_captures = set(captured_paths)
    expected_snapshots = {item["path"]: item["sha256"] for item in codex.get("snapshots", ())
                          if item["path"] in selected_captures}
    options = {"expected_snapshots": expected_snapshots} if expected_snapshots else {}
    if args.scope is None and args.mode == "manual":
        options["discover_graph"] = True
        chat_dir = config.memory_dir.resolve() / "codex"
        holder = str(claim["owner"]["holder"]).rsplit("/", 1)[-1].casefold()
        native_paths = tuple(path for path in captured_paths
                             if (config.root / path).parent == chat_dir
                             and Path(path).suffix == ".txt" and Path(path).stem.casefold() != holder)
        if native_paths:
            options["outcome_sources"] = native_paths
    result = memory.maintain(scope, control=control, timeout=args.timeout,
                             include_registered=args.scope is None, **options)
    if indexed:
        from .codex_index_route import index_workset

        codex.update(index_workset(memory, scope=args.scope, control=control, timeout=args.timeout))
    layout = maintenance_layout(config, mode=args.mode, available_subagents=args.available_subagents,
                                work_items=max(result["semantic_sources"],
                                               result["pending_relations"] + result.get("graph_candidates", 0)
                                               + result.get("outcome_candidates", 0),
                                               result["feedback"]),
                                run_id=claim["owner"]["run_id"])
    codex_info = {key: value for key, value in codex.items() if key not in ("paths", "snapshots", "capture")}
    result.update(codex=codex_info, control=control, owner=claim["owner"], acquired=True, layout=layout,
                  discovery={"mode": discovery["mode"], "sources": len(scope), "gaps": discovery["gaps"]})
    receipt = Path(result["receipt"])
    material = json.loads(receipt.read_text(encoding="utf-8"))
    provenance = codex_info if indexed else {
        **codex_info, "capture_dir": str(config.memory_dir / "codex"),
        "attachment_dir": str(config.memory_dir / "codex-attachments"),
    }
    material.update(layout=layout, owner_run_id=claim["owner"]["run_id"],
                    codex=provenance,
                    discovery=result["discovery"])
    receipt.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding="utf-8")
    if result["needs_semantic"] and layout["teams"]:
        result["worker"] = prompt_dispatch(config, result["receipt"], control, layout=layout)
    elif result["needs_semantic"]:
        result["dispatch_blocked"] = "A coordinator, reader and reserved recovery seat are required; semantic work remains pending."
    return result


def _activate(config):
    from basepack.project.init import refresh_project_entry
    from basepack.runtime.recovery import managed

    refresh_project_entry(config.root, config.path, config.python,
                          memory_enabled=True, memory_dir=config.memory_dir,
                          memory_managed=managed(config, "memory"))
