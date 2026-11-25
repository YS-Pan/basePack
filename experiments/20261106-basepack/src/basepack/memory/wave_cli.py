"""Host-driven finite maintenance waves over the existing publication chain."""

import json
from functools import partial
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from . import graph_review, waves
from .prompts import MAINTENANCE_BOOTSTRAP, _wave_layout, memory_command, render_template
from .stages import _read_reference, load_stage


def register(parser):
    commands = parser.add_subparsers(dest="wave_action", required=True)
    names = ("create", "started", "worker-failed", "initialized", "seal", "claim", "worker-prompt", "task-prompt",
             "submit", "notification-pending", "notification-result", "notification-recover", "inspect", "finish", "publish", "publication-failed", "close")
    actions = {name: commands.add_parser(name) for name in names}
    for name, action in actions.items():
        action.add_argument("--control", required=True)
        action.add_argument("--run-id", required=True)
        if name != "create":
            action.add_argument("--wave-id", required=True)
    create = actions["create"]
    create.add_argument("--receipt", required=True)
    work = create.add_mutually_exclusive_group(required=True)
    work.add_argument("--tasks", help="JSON array of finite independent task objects")
    work.add_argument("--inventory", help="Fixed inventory report to use for grouped tasks")
    create.add_argument("--groups", nargs="+", help="Inventory group IDs selected for this wave")
    create.add_argument("--read-paths", nargs="+", help="Additional read-only files in the selected groups")
    create.add_argument("--coordinator", required=True, help="Canonical non-root coordinator task path")
    create.add_argument("--readers", type=int, required=True, help="Fixed reader pool size chosen for this wave")
    create.add_argument("--stage", help="Fixed continuation stage, if any")
    create.add_argument("--stage-sha256", help="Expected stage package hash")
    for name in ("started", "worker-failed", "claim", "worker-prompt", "task-prompt", "submit",
                 "notification-pending", "notification-result"):
        actions[name].add_argument("--worker", required=True)
    actions["started"].add_argument("--handle", required=True)
    actions["worker-failed"].add_argument("--error", required=True, help="Original host error")
    for name in ("task-prompt", "submit"):
        actions[name].add_argument("--task-id", required=True)
    actions["submit"].add_argument("--drafts", nargs="*", default=[])
    actions["submit"].add_argument("--coverage", required=True)
    actions["submit"].add_argument("--errors", required=True)
    actions["submit"].add_argument("--failed", action="store_true")
    status = actions["notification-result"].add_mutually_exclusive_group(required=True)
    status.add_argument("--accepted", action="store_true")
    status.add_argument("--failed", action="store_true")
    actions["notification-result"].add_argument("--result", required=True, help="JSON file containing actual host response or error")
    recovery = actions["notification-recover"]
    recovered = recovery.add_mutually_exclusive_group(required=True)
    recovered.add_argument("--accepted", action="store_true")
    recovered.add_argument("--failed", action="store_true")
    recovery.add_argument("--evidence", required=True, help="Actual host lifecycle evidence; no new followup is sent")
    recovery.add_argument("--worker-ended", action="store_true", required=True)
    recovery.add_argument("--host-verified", action="store_true", required=True)
    pub = actions["publish"]
    pub.add_argument("--completed", required=True, help="Ordered completed draft references as JSON")
    pub.add_argument("--frozen", required=True, help="Stable new frozen batch path")
    pub.add_argument("--result", required=True, help="Stable publication result path")
    pub.add_argument("--timeout", type=float, default=600)
    failed = actions["publication-failed"]
    failed.add_argument("--error", required=True, help="Original definite publication error")
    failed.add_argument("--publisher-ended", action="store_true", required=True,
                        help="Host confirms that the publisher ended")
    failed.add_argument("--no-commit", action="store_true", required=True,
                        help="Host confirms that the publication did not commit; never use for unknown outcome")
    actions["close"].add_argument("--no-publication", action="store_true")


def _command(config, action, control, run_id, wave_id, *args):
    return memory_command(config, "wave", action, "--control", control, "--run-id", run_id,
                          "--wave-id", wave_id, *args)


def create(config, args, tasks):
    from .content import _project_path

    receipt_path = Path(args.receipt).resolve()
    receipt_bytes = receipt_path.read_bytes()
    receipt_hash = sha256(receipt_bytes).hexdigest()
    material = json.loads(receipt_bytes.decode("utf-8"))
    if material["owner_run_id"] != args.run_id:
        raise PermissionError("Receipt belongs to a different maintenance owner")
    if bool(args.stage) != bool(args.stage_sha256):
        raise ValueError("A stage and its fixed SHA256 must be supplied together")
    stage = (load_stage(args.receipt, args.control, args.stage, file_sha256=args.stage_sha256)
             if args.stage else None)
    layout = _wave_layout((stage or material)["layout"])

    grouped = None
    if getattr(args, "inventory", None):
        from .inventory_work import grouped_tasks
        from .query import load_json_file
        if not args.groups:
            raise ValueError("Select at least one inventory group using --groups")
        tasks, grouped = grouped_tasks(config, load_json_file(args.inventory), material, args.groups,
                                       read_paths=args.read_paths or (), stage=stage)
    elif getattr(args, "groups", None) or getattr(args, "read_paths", None):
        raise ValueError("--groups and --read-paths require --inventory")

    root = Path(config.root).resolve()
    for task in tasks:
        for key in ("paths", "read_paths"):
            if key == "read_paths" and "graph_candidate" in task:
                continue
            values = task.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"Task {task['id']} {key} must be a list of project-relative files")
            normalized = []
            for value in values:
                path = _project_path(root, value)
                if path == root or path.is_dir():
                    raise ValueError(f"Task paths must identify files: {value}")
                normalized.append(path.relative_to(root).as_posix())
            task[key] = list(dict.fromkeys(normalized))
    if not layout["teams"] or not layout["teams"][0]["reader_task_names"]:
        raise ValueError("A wave requires at least one reader and a reserved coordinator recovery seat")
    if not args.coordinator.startswith("/") or args.coordinator == "/root":
        raise ValueError("Wave coordinator must be the canonical non-root host task path")
    if args.coordinator.rsplit("/", 1)[-1] != layout["teams"][0]["task_name"]:
        raise ValueError("Wave coordinator identity must match the fixed layout")
    count = args.readers
    if count < 1 or count > min(len(tasks), len(layout["teams"][0]["reader_task_names"])):
        raise ValueError("Reader count must be between one and the smaller of task count and saved reader capacity")
    wave_id = uuid4().hex
    workers = [f"bp_w_{wave_id[:12]}_r{index}" for index in range(count)]
    stage_ref = ({"path": str(Path(args.stage).resolve()), "file_sha256": args.stage_sha256.lower()}
                 if args.stage else None)
    state = waves.create(config.memory_dir, args.control, args.run_id, args.receipt, tasks, workers,
                         wave_id=wave_id, coordinator=args.coordinator, receipt_sha256=receipt_hash, stage=stage_ref)
    ai = layout["teams"][0]["reader_ai"]
    dispatches = []
    for worker in workers:
        command = _command(config, "worker-prompt", args.control, args.run_id, wave_id, "--worker", worker)
        dispatches.append({"task_name": worker, "fork_turns": "none", "model": ai["model"],
                           "reasoning_effort": ai["reasoning_effort"],
                           "message": f"{MAINTENANCE_BOOTSTRAP}\n{command}"})
    result = {"wave_id": wave_id, "run_id": args.run_id, "control": state["control"],
            "receipt": state["source_receipt"], "coordinator": state["coordinator"],
            "workers": [{"task_name": worker, "spawn_arguments": dispatch}
                        for worker, dispatch in zip(workers, dispatches)],
            "parent_actions": {"seal_command": _command(config, "seal", args.control, args.run_id, wave_id),
                               "go_message": f"go {wave_id}",
                               "close_command": _command(config, "close", args.control, args.run_id, wave_id)},
            "startup": "Spawn and register each worker, report initialization, then end this turn. Parent seals only after observing this coordinator idle."}
    if grouped is not None:
        result["grouping"] = grouped
    return result


def worker_prompt(config, control, run_id, wave_id, worker):
    state = waves.inspect(config.memory_dir, control, run_id, wave_id)
    if worker not in state["workers"]:
        raise PermissionError("Worker is not registered in this wave")
    commands = {name.replace("-", "_"): _command(config, name, control, run_id, wave_id,
                  "--worker", worker) for name in
                ("claim", "task-prompt", "submit", "notification-pending", "notification-result")}
    return {"prompt": render_template("wave-worker", worker=worker, wave_id=wave_id, coordinator=state["coordinator"],
                                      skill=str(Path(__file__).with_name("SKILL.md")), **commands)}


def task_prompt(config, control, run_id, wave_id, worker, task_id):
    from .prompts import _reader_hints
    state = waves.inspect(config.memory_dir, control, run_id, wave_id)
    task = next(task for task in state["tasks"] if task["id"] == task_id)
    if not state["sealed"] or task["worker"] != worker or task["status"] != "claimed":
        raise PermissionError("Task is not claimed by this worker")
    material = _read_reference(state["source_receipt"])
    work = config.root / "tmp" / "basepack-waves" / wave_id / sha256(task_id.encode("utf-8")).hexdigest()[:20]
    paths = list(dict.fromkeys([*task["paths"], *task.get("read_paths", [])]))
    preparation = []
    if "expected_revisions" in task:
        preparation = ["--expected-revisions", json.dumps(task["expected_revisions"], ensure_ascii=False)]
    values = {"task": json.dumps(task, ensure_ascii=False), "hints": json.dumps(_reader_hints(material, paths), ensure_ascii=False),
              "receipt": json.dumps(state["source_receipt"], ensure_ascii=False),
              "work": str(work), "skill": str(Path(__file__).with_name("SKILL.md")),
              "prepare_command": memory_command(config, "prepare", "--paths", *(paths or ["<identified-project-relative-file>"]),
                                                *preparation,
                                                "--output", work / "reading.json"),
              "read_command": memory_command(config, "read", "<member-id>"),
              "search_command": memory_command(config, "search", "--text", "<query>"),
              "neighbors_command": memory_command(config, "neighbors", "<record-id>", "--include-stale"),
              "prepare_inspection": (Path(__file__).with_name("prompts") / "prepare-inspection.md").read_text(encoding="utf-8").strip()}
    return {"task": task, "work": str(work), "prompt": render_template("wave-task", **values)}


def publish(config, args, completed):
    from .graph_outcomes import reject_current_duplicates
    from .publish import publish as publish_batch
    from .store import Memory
    frozen, result = str(Path(args.frozen).resolve()), str(Path(args.result).resolve())
    intent = waves.publication_intent(config.memory_dir, args.control, args.run_id, args.wave_id,
                                      drafts=completed, frozen=frozen, result=result)
    if intent["status"] == "committed":
        return waves.publication_committed(config.memory_dir, args.control, args.run_id, args.wave_id)
    options = {}
    if "graph_tasks" in intent:
        options["batch_validator"] = partial(graph_review.frozen_edges, intent)
    if Path(frozen).exists():
        outcome = publish_batch(Memory(config), frozen=frozen, control=args.control, result=result,
                                timeout=args.timeout, **options)
    else:
        if "graph_tasks" in intent:
            graph_review.validate_publication(intent)
        memory = Memory(config)
        if "outcome_assignment" in intent:
            reference = next(ref for ref in completed if ref["assignment"] == intent["outcome_assignment"])
            reject_current_duplicates(memory, reference)
        outcome = publish_batch(memory, completed=completed, output=frozen, control=args.control,
                                result=result, timeout=args.timeout, use_draft_context=False, **options)
    waves.publication_committed(config.memory_dir, args.control, args.run_id, args.wave_id)
    return outcome


def dispatch(config, args):
    from .query import load_json_file
    action = args.wave_action
    common = (config.memory_dir, args.control, args.run_id)
    if action == "create":
        return create(config, args, load_json_file(args.tasks) if args.tasks else None)
    common += (args.wave_id,)
    if action == "started":
        return waves.started(*common, args.worker, args.handle)
    if action == "worker-failed":
        return waves.worker_failed(*common, args.worker, args.error)
    if action == "initialized":
        return waves.initialization_receipt(*common)
    if action == "seal":
        return waves.seal(*common)
    if action == "claim":
        return waves.claim(*common, args.worker)
    if action == "worker-prompt":
        return worker_prompt(config, args.control, args.run_id, args.wave_id, args.worker)
    if action == "task-prompt":
        return task_prompt(config, args.control, args.run_id, args.wave_id, args.worker, args.task_id)
    if action == "submit":
        return waves.submit(*common, args.worker, args.task_id, drafts=args.drafts,
                            coverage=args.coverage, errors=args.errors, failed=args.failed)
    if action == "notification-pending":
        return waves.notification_pending(*common, args.worker)
    if action == "notification-result":
        return waves.notification_result(*common, args.worker, accepted=args.accepted, result=load_json_file(args.result))
    if action == "notification-recover":
        return waves.notification_recover(*common, accepted=args.accepted, evidence=args.evidence,
                                          worker_ended=args.worker_ended, host_verified=args.host_verified)
    if action == "inspect":
        return waves.inspect(*common)
    if action == "finish":
        return waves.finish(*common)
    if action == "publish":
        return publish(config, args, load_json_file(args.completed))
    if action == "publication-failed":
        return waves.publication_failed(*common, error=args.error, publisher_ended=args.publisher_ended,
                                        no_commit=args.no_commit)
    if action == "close":
        return waves.close(*common, no_publication=args.no_publication)
    raise ValueError(f"Unknown wave action: {action}")
