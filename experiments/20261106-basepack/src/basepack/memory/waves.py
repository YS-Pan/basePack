"""A finite local wave; host lifecycle and publication remain host responsibilities."""

import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .maintenance import MaintenanceStopped, _locked, begin_commit
from .owner import _control, _owned, _paths, _read, _write
from .query import normalize_scope
from .stages import _read_reference, fixed_reference


def _state_path(memory_dir):
    return Path(memory_dir) / "maintenance" / "wave.json"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _live(memory_dir, control, run_id):
    _, owner_path = _paths(memory_dir)
    owner = _owned(owner_path, control)
    if owner["run_id"] != run_id:
        raise PermissionError("Wave belongs to a different maintenance owner")
    if owner["stopped"]:
        raise MaintenanceStopped("Maintenance stopped")
    begin_commit(control)


def _load(memory_dir, control, run_id, wave_id):
    _live(memory_dir, control, run_id)
    state = _read(_state_path(memory_dir))
    if state is None or state["run_id"] != run_id or state["wave_id"] != wave_id:
        raise PermissionError("Wave is not current for this maintenance owner")
    return state


def _worker(state, name):
    return state["workers"][name]


def _source_path(path):
    path = Path(normalize_scope(path)).as_posix()
    if path == ".":
        raise ValueError("Source path cannot be empty")
    return path


def _path_key(path):
    return os.path.normcase(_source_path(path))


def create(memory_dir, control, run_id, receipt, tasks, workers, *, wave_id=None, coordinator=None,
           receipt_sha256=None, stage=None):
    """Pre-register all tasks and workers; a fresh wave starts unsealed."""
    lock, owner_path = _paths(memory_dir)
    with _locked(lock, timeout=5):
        _live(memory_dir, control, run_id)
        owner_stage = _owned(owner_path, control).get("stage")
        previous = _read(_state_path(memory_dir))
        if previous and previous["run_id"] == run_id and (not previous["closed"] or
                (previous["notification"] and previous["notification"]["status"] in ("eligible", "pending"))):
            raise RuntimeError("Current wave or its notification has not finished")
        source_receipt = fixed_reference(receipt)
        if receipt_sha256 is not None and source_receipt["file_sha256"] != receipt_sha256.lower():
            raise ValueError("Maintenance receipt changed during wave creation")
        material = _read_reference(source_receipt)
        if material["owner_run_id"] != run_id:
            raise PermissionError("Receipt belongs to a different maintenance owner")
        if material.get("layout", {}).get("organization") != "finite-wave-v1":
            raise ValueError("Old maintenance organization: close the old run and start a fresh maintain")
        if stage is not None:
            stage = {"path": str(Path(stage["path"]).resolve()), "file_sha256": stage["file_sha256"].lower()}
            package = _read_reference(stage)
            if (package["receipt"] != source_receipt or package["control"] != _control(control)
                    or package["owner_run_id"] != run_id):
                raise PermissionError("Stage receipt, control or owner does not match this wave")
            if package["layout"].get("organization") != "finite-wave-v1":
                raise ValueError("Old stage organization: close the old run and start a fresh maintain")
            if owner_stage is None or any(owner_stage[key] != stage[key] for key in ("path", "file_sha256")):
                raise PermissionError("Stage is not the current owner stage")
        elif owner_stage is not None:
            raise PermissionError("Current owner stage must be supplied")
        scope = package["remaining"]["paths"] if stage is not None else material["workset"]["included"]
        scope = [_source_path(path) for path in scope]
        scope_by_key = {_path_key(path): path for path in scope}
        if len(scope_by_key) != len(scope):
            raise ValueError("Wave source scope has duplicate paths")
        task_ids = [task["id"] for task in tasks]
        if not tasks or not workers or len(set(task_ids)) != len(tasks) or len(set(workers)) != len(workers):
            raise ValueError("Wave needs uniquely identified tasks and workers")
        graph_targets = [target for task in tasks for target in task["write_targets"]]
        if len(set(graph_targets)) != len(graph_targets):
            raise ValueError("Each graph write target must belong to one task")
        normalized_tasks = []
        owned_sources = set()
        for task in tasks:
            if not task["goal"] or not task["outputs"] or not isinstance(task["paths"], list):
                raise ValueError("Each task needs a goal, source path list and outputs")
            paths = [_source_path(path) for path in task["paths"]]
            keys = [_path_key(path) for path in paths]
            if any(key not in scope_by_key for key in keys):
                raise ValueError("Task write sources must belong to the fixed wave scope")
            if len(set(keys)) != len(keys) or owned_sources.intersection(keys):
                raise ValueError("Each write source must belong to one task")
            owned_sources.update(keys)
            task = {**task, "paths": [scope_by_key[key] for key in keys]}
            if "read_paths" in task:
                if not isinstance(task["read_paths"], list):
                    raise ValueError("read_paths must be a list")
                task["read_paths"] = [_source_path(path) for path in task["read_paths"]]
            normalized_tasks.append(task)
        wave_id = wave_id or uuid4().hex
        if not wave_id.isascii() or not wave_id.isalnum():
            raise ValueError("Wave identifier must contain only ASCII letters and digits")
        if ((previous and previous["wave_id"] == wave_id) or
                (Path(memory_dir) / "maintenance" / f"wave-{wave_id}-receipt.json").exists()):
            raise ValueError("Wave identifier has already been used")
        history = []
        if previous:
            previous_record = previous["closure"]
            if previous_record is None:
                path = Path(memory_dir) / "maintenance" / f"wave-{previous['wave_id']}-recovery.json"
                previous_record = _fixed_json(path, previous)
            history = [*previous["history"], previous_record]
        state = {"wave_id": wave_id, "run_id": run_id, "coordinator": coordinator,
                 "control": _control(control), "source_receipt": source_receipt, "stage": stage, "write_scope": scope,
                 "created_at": _utc_now(), "sealed_at": None, "execution_ended_at": None,
                 "sealed": False, "finished": False, "closed": False, "publication": None, "unpublished": None,
                 "history": history, "closure": None, "initialization": None,
                 "tasks": [{**task, "status": "unclaimed", "worker": None, "result": None,
                            "claimed_at": None, "submitted_at": None} for task in normalized_tasks],
                 "workers": {name: {"status": "registered", "handle": None, "error": None,
                                     "retired_at": None, "failed_at": None} for name in workers},
                 "receipt": None, "notification": None}
        _write(_state_path(memory_dir), state)
        return state


def started(memory_dir, control, run_id, wave_id, worker, handle):
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        entry = _worker(state, worker)
        if state["sealed"] or entry["status"] != "registered" or not handle:
            raise ValueError("Worker cannot be started")
        entry.update(status="started", handle=handle)
        _write(_state_path(memory_dir), state)
        return entry


def worker_failed(memory_dir, control, run_id, wave_id, worker, error):
    """Record host-observed failure without reclaiming any claimed task."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        entry = _worker(state, worker)
        if entry["status"] not in ("registered", "started"):
            raise ValueError("Worker is already terminal")
        entry.update(status="failed", error=error, failed_at=_utc_now())
        if state["sealed"] and not any(item["status"] in ("registered", "started")
                                       for item in state["workers"].values()):
            _receipt(memory_dir, state, None)
        _write(_state_path(memory_dir), state)
        return entry


def seal(memory_dir, control, run_id, wave_id):
    """Host seals only after confirming the coordinator's first turn ended."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        if state["sealed"]:
            raise ValueError("Wave is already sealed")
        if state["initialization"] is None:
            raise ValueError("Wave initialization receipt is required before seal")
        if fixed_reference(state["initialization"]["path"]) != state["initialization"]:
            raise ValueError("Wave initialization receipt changed")
        if any(worker["status"] == "registered" for worker in state["workers"].values()):
            raise ValueError("Every registered worker must have started or failed before seal")
        state["sealed"] = True
        state["sealed_at"] = _utc_now()
        if not any(worker["status"] == "started" for worker in state["workers"].values()):
            _receipt(memory_dir, state, None)
        _write(_state_path(memory_dir), state)
        return state


def _fixed_json(path, value):
    material = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if path.exists():
        if path.read_bytes() != material:
            raise FileExistsError(f"Wave receipt already exists with different contents: {path}")
    else:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as file:
                file.write(material)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return fixed_reference(path)


def _receipt(memory_dir, state, worker):
    path = Path(memory_dir) / "maintenance" / f"wave-{state['wave_id']}-receipt.json"
    if path.exists():
        # A prior receipt may have been saved just before the atomic state write failed.
        saved = json.loads(path.read_text(encoding="utf-8"))
        state["sealed_at"] = saved["sealed_at"]
        state["execution_ended_at"] = saved["execution_ended_at"]
        for name, entry in state["workers"].items():
            if entry["status"] == saved["workers"][name]["status"]:
                for key in ("retired_at", "failed_at"):
                    entry[key] = saved["workers"][name][key]
    else:
        state["execution_ended_at"] = _utc_now()
    state["receipt"] = _fixed_json(path, {key: state[key] for key in
                                          ("wave_id", "run_id", "coordinator", "source_receipt", "stage", "write_scope",
                                           "created_at", "sealed_at", "execution_ended_at", "initialization", "tasks", "workers")})
    if worker is not None:
        state["notification"] = {"worker": worker, "status": "eligible", "result": None}


def initialization_receipt(memory_dir, control, run_id, wave_id):
    """Fix actual startup outcomes; the host separately confirms Terra is idle."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        if state["sealed"]:
            raise ValueError("Wave startup is already sealed")
        if state["initialization"] is not None:
            if fixed_reference(state["initialization"]["path"]) != state["initialization"]:
                raise ValueError("Wave initialization receipt changed")
            return state["initialization"]
        if any(worker["status"] == "registered" for worker in state["workers"].values()):
            raise ValueError("Every registered worker must have started or failed before initialization")
        path = Path(memory_dir) / "maintenance" / f"wave-{wave_id}-initialization.json"
        state["initialization"] = _fixed_json(path, {key: state[key] for key in
                                       ("wave_id", "run_id", "coordinator", "source_receipt", "stage", "workers")}
                                       | {"tasks": [task["id"] for task in state["tasks"]]})
        _write(_state_path(memory_dir), state)
        return state["initialization"]


def claim(memory_dir, control, run_id, wave_id, worker):
    """Claim one task, or atomically retire and award the last normal notifier."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        entry = _worker(state, worker)
        if state["finished"] or entry["status"] != "started":
            raise ValueError("Worker is not active")
        if not state["sealed"]:
            return {"startup_pending": True, "task": None, "retired": False}
        if any(task["worker"] == worker and task["status"] == "claimed" for task in state["tasks"]):
            raise ValueError("Worker still owns a claimed task")
        task = next((task for task in state["tasks"] if task["status"] == "unclaimed"), None)
        if task is not None:
            task.update(status="claimed", worker=worker, claimed_at=_utc_now())
            result = {"startup_pending": False, "task": task, "retired": False}
        else:
            entry.update(status="retired", retired_at=_utc_now())
            if not any(item["status"] in ("registered", "started") for item in state["workers"].values()):
                _receipt(memory_dir, state, worker)
            result = {"startup_pending": False, "task": None, "retired": True, "receipt": state["receipt"],
                      "notification": state["notification"]}
        _write(_state_path(memory_dir), state)
        return result


def submit(memory_dir, control, run_id, wave_id, worker, task_id, *, drafts, coverage, errors, failed=False,
           draft_hashes=None):
    """Save fixed result references, including explicit coverage and errors."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        task = next(task for task in state["tasks"] if task["id"] == task_id)
        if task["worker"] != worker or task["status"] != "claimed" or _worker(state, worker)["status"] != "started":
            raise PermissionError("Task is not claimed by this active worker")
        draft_refs = [fixed_reference(path) for path in drafts]
        if draft_hashes is not None and ([ref["file_sha256"] for ref in draft_refs] !=
                                         [digest.lower() for digest in draft_hashes]):
            raise ValueError("Draft changed after source ownership validation")
        from .wave_scope import validate_draft
        for ref in draft_refs:
            material = Path(ref["path"]).read_bytes()
            if sha256(material).hexdigest() != ref["file_sha256"]:
                raise ValueError("Draft changed while fixing its source ownership")
            validate_draft(task, material)
        task["result"] = {"drafts": draft_refs,
                          "coverage": fixed_reference(coverage), "errors": fixed_reference(errors)}
        task["status"] = "failed" if failed else "submitted"
        task["submitted_at"] = _utc_now()
        _write(_state_path(memory_dir), state)
        return task


def notification_pending(memory_dir, control, run_id, wave_id, worker):
    """Record intent before the host call; an interrupted call is uncertain."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        notice = state["notification"]
        if not notice or notice["worker"] != worker or notice["status"] != "eligible":
            raise PermissionError("Worker has no unused notification eligibility")
        notice["status"] = "pending"
        _write(_state_path(memory_dir), state)
        return {"receipt": state["receipt"], "notification": notice}


def notification_result(memory_dir, control, run_id, wave_id, worker, *, accepted, result):
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        notice = state["notification"]
        if not notice or notice["worker"] != worker or notice["status"] != "pending":
            raise PermissionError("No pending notification for this worker")
        notice.update(status="accepted" if accepted else "failed", result=result)
        _write(_state_path(memory_dir), state)
        return notice


def notification_recover(memory_dir, control, run_id, wave_id, *, accepted, evidence, worker_ended, host_verified):
    """Record parent-observed facts after the original notifier has ended."""
    if not worker_ended or not host_verified or not evidence:
        raise ValueError("Confirm the worker ended and the host outcome, and preserve its evidence")
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        notice = state["notification"]
        if not notice or notice["status"] not in ("eligible", "pending"):
            raise ValueError("Notification is not awaiting recovery")
        if notice["status"] == "eligible" and accepted:
            raise ValueError("An unattempted notification cannot have been accepted")
        notice.update(status="accepted" if accepted else "failed", result=evidence,
                      recovery={"worker_ended": True, "host_verified": True})
        _write(_state_path(memory_dir), state)
        return notice


def inspect(memory_dir, control, run_id, wave_id):
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        return _load(memory_dir, control, run_id, wave_id)


def finish(memory_dir, control, run_id, wave_id):
    """Admit a callback idempotently; publication still uses its existing owner lock."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        if not state["receipt"]:
            raise ValueError("Wave has no fixed receipt")
        refs = [state["source_receipt"], state["initialization"], state["receipt"]]
        if state["stage"] is not None:
            refs.append(state["stage"])
        for task in state["tasks"]:
            if task["result"]:
                refs.extend(task["result"]["drafts"])
                refs.extend([task["result"]["coverage"], task["result"]["errors"]])
        for ref in refs:
            if fixed_reference(ref["path"]) != ref:
                raise ValueError(f"Fixed reference changed: {ref['path']}")
        already_finished = state["finished"]
        state["finished"] = True
        if not already_finished:
            _write(_state_path(memory_dir), state)
        return {"already_finished": already_finished, "receipt": state["receipt"], "closed": state["closed"],
                "publication": state["publication"], "closure": state["closure"]}


def publication_intent(memory_dir, control, run_id, wave_id, *, drafts, frozen, result):
    """Fix publication inputs and destinations before freeze or publish."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        if not state["finished"] or state["closed"]:
            raise ValueError("Wave callback must be admitted and remain open")
        available = [{**ref, "assignment": task["id"]} for task in state["tasks"] if task["status"] == "submitted"
                     for ref in task["result"]["drafts"]]
        if not drafts or len({ref["path"] for ref in drafts}) != len(drafts) or any(ref not in available for ref in drafts):
            raise ValueError("Publication drafts must be unique submitted wave references")
        for ref in drafts:
            if fixed_reference(ref["path"]) != {key: ref[key] for key in ("path", "file_sha256")}:
                raise ValueError(f"Fixed reference changed: {ref['path']}")
        intent = {"drafts": drafts, "frozen": str(Path(frozen).resolve()),
                  "result": str(Path(result).resolve())}
        publication = state["publication"]
        if publication is not None:
            if publication["intent"] != intent:
                raise ValueError("Publication intent cannot be changed")
            if publication["status"] == "failed":
                raise ValueError("Publication intent was definitively failed; start a repair wave")
            return publication
        if intent["frozen"] == intent["result"]:
            raise ValueError("Frozen and result paths must differ")
        if Path(intent["frozen"]).exists() or Path(intent["result"]).exists():
            raise FileExistsError("New publication destinations must not exist")
        state["publication"] = {"status": "intent", "intent": intent, "frozen": None, "result": None}
        _write(_state_path(memory_dir), state)
        return state["publication"]


def publication_committed(memory_dir, control, run_id, wave_id):
    """Record existing fixed output files after the existing publisher returns."""
    lock, _ = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        publication = state["publication"]
        if publication is None or state["closed"] or publication["status"] == "failed":
            raise ValueError("No open publication intent")
        frozen = fixed_reference(publication["intent"]["frozen"])
        result = fixed_reference(publication["intent"]["result"])
        projection = _read_reference(result)
        batch = _read_reference(frozen)
        if (projection["frozen"] != frozen["path"] or projection["frozen_file_sha256"] != frozen["file_sha256"]
                or projection["batch_id"] != batch["batch_id"]):
            raise ValueError("Publication result does not match its frozen batch")
        if projection.get("completed") is not None and projection["completed"] != publication["intent"]["drafts"]:
            raise ValueError("Publication result does not match its fixed draft order")
        if publication["status"] == "committed":
            if publication["frozen"] != frozen or publication["result"] != result:
                raise ValueError("Committed publication files changed")
            return publication
        publication.update(status="committed", frozen=frozen, result=result)
        _write(_state_path(memory_dir), state)
        return publication


def publication_failed(memory_dir, control, run_id, wave_id, *, error, publisher_ended, no_commit):
    """Record a host-confirmed definite failure, never an uncertain outcome."""
    if not publisher_ended or not no_commit or not error:
        raise ValueError("Confirm the publisher ended, no commit occurred, and preserve the original error")
    lock, owner_path = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        publication = state["publication"]
        if publication is None or state["closed"]:
            raise ValueError("No open publication intent")
        if _owned(owner_path, control)["publications"]:
            raise RuntimeError("Publication is in flight or uncertain")
        if publication["status"] == "failed":
            if publication["error"] != error:
                raise ValueError("Original publication error cannot be changed")
            return publication
        if publication["status"] != "intent":
            raise ValueError("Committed publication cannot be marked failed")
        publication.update(status="failed", error=error)
        _write(_state_path(memory_dir), state)
        return publication


def close(memory_dir, control, run_id, wave_id, *, no_publication=False):
    """Close only a resolved publication or an explicitly empty wave."""
    lock, owner_path = _paths(memory_dir)
    with _locked(lock, timeout=5):
        state = _load(memory_dir, control, run_id, wave_id)
        if not state["finished"]:
            raise ValueError("Wave callback has not been admitted")
        if state["closed"]:
            return state
        if state["notification"] and state["notification"]["status"] in ("eligible", "pending"):
            raise RuntimeError("Wave notification remains unresolved")
        if _owned(owner_path, control)["publications"]:
            raise RuntimeError("Publication is in flight or uncertain")
        publication = state["publication"]
        submitted = [{**ref, "assignment": task["id"]} for task in state["tasks"]
                     if task["status"] == "submitted" for ref in task["result"]["drafts"]]
        if publication is None:
            if not no_publication or submitted:
                raise ValueError("Explicit no-publication requires no submitted drafts")
        elif no_publication or publication["status"] not in ("committed", "failed"):
            raise ValueError("Wave publication has not been resolved")
        published = publication["intent"]["drafts"] if publication and publication["status"] == "committed" else []
        state["unpublished"] = [ref for ref in submitted if ref not in published]
        path = Path(memory_dir) / "maintenance" / f"wave-{wave_id}-closure.json"
        state["closure"] = _fixed_json(path, {key: state[key] for key in
                                           ("wave_id", "run_id", "receipt", "notification", "publication", "unpublished")})
        state["closed"] = True
        _write(_state_path(memory_dir), state)
        return state
