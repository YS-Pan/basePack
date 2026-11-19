"""Durable project maintenance ownership and publication admission."""

import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .maintenance import MaintenanceStopped, _locked, begin_commit, stop


def _paths(memory_dir):
    directory = Path(memory_dir) / "maintenance"
    return directory / "owner.lock", directory / "owner.json"


def _read(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path, value):
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _control(control):
    return str(Path(control).resolve())


def _owned(path, control):
    owner = _read(path)
    if owner is None or owner["control"] != _control(control):
        raise PermissionError("Maintenance control is not the current project owner")
    return owner


def _public(owner):
    if owner is None:
        return None
    return {key: value for key, value in owner.items() if key != "control"}


def attempt_control(memory_dir, attempt_id: str) -> Path:
    """Derive the exclusive control path before starting an automatic attempt."""
    if re.fullmatch(r"[0-9a-f]{32}", attempt_id) is None:
        raise ValueError("Maintenance attempt ID must be 32 lowercase hex digits")
    return (Path(memory_dir) / "maintenance").resolve() / f"{attempt_id}.control"


def _cancel_marker(control):
    return control.with_suffix(".cancelled")


def check_attempt(memory_dir, attempt_id):
    """Check durable cancellation without creating a control or taking a lock."""
    control = attempt_control(memory_dir, attempt_id)
    if _cancel_marker(control).exists():
        raise MaintenanceStopped("Maintenance attempt stopped")


def cancel_attempt(memory_dir, attempt_id):
    """Record cancellation and stop the matching owner if it has acquired."""
    control = attempt_control(memory_dir, attempt_id)
    marker = _cancel_marker(control)
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        if not marker.exists():
            _write(marker, True)
        owner = _read(state)
        if owner is not None and owner["run_id"] == attempt_id and owner["control"] == str(control):
            if not owner["stopped"]:
                _stop_owner(state, owner)
        else:
            owner = None
        return {"stopped": True, "attempt_id": attempt_id, "owner": owner}


def acquire(memory_dir, project_id, holder, control, *, attempt_id=None):
    """Atomically claim the project before preflight; return the current holder if busy.

    A control path is a capability and is created exclusively. Never reuse or
    remove it: old workers must not acquire authority over a later run.
    """
    if attempt_id is not None and _control(control) != str(attempt_control(memory_dir, attempt_id)):
        raise ValueError("Maintenance control must match the attempt ID")
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        if attempt_id is not None:
            check_attempt(memory_dir, attempt_id)
        owner = _read(state)
        if owner is not None:
            return {"acquired": False, "owner": _public(owner)}
        control = Path(_control(control))
        control.parent.mkdir(parents=True, exist_ok=True)
        with control.open("xb") as file:
            file.flush()
            os.fsync(file.fileno())
        owner = {"project_id": project_id, "holder": holder, "control": str(control),
                 "run_id": attempt_id if attempt_id is not None else uuid4().hex,
                 "stopped": False, "publications": []}
        _write(state, owner)
        return {"acquired": True, "owner": owner}


def status(memory_dir):
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        return _public(_read(state))


def _begin_owned(memory_dir, owner, message):
    attempt = attempt_control(memory_dir, owner["run_id"])
    if owner["stopped"] or (owner["control"] == str(attempt) and _cancel_marker(attempt).exists()):
        raise MaintenanceStopped(message)
    begin_commit(owner["control"])


def check_owned(memory_dir, control):
    """Require the live owner before starting maintenance preflight."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        _begin_owned(memory_dir, owner, "Maintenance stopped")
        return owner


def _stop_owner(state, owner):
    stop(owner["control"])
    owner["stopped"] = True
    _write(state, owner)
    return owner


def stop_owned(memory_dir, control):
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        return _stop_owner(state, _owned(state, control))


def begin_publication(memory_dir, control, publication=None):
    """Persist admission before transaction I/O; stop and release share this lock."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        _begin_owned(memory_dir, owner, "Maintenance stopped before publication")
        publication = publication or uuid4().hex
        if publication in owner["publications"]:
            raise ValueError("Publication identifier is already in flight")
        owner["publications"].append(publication)
        _write(state, owner)
        return publication


def finish_publication(memory_dir, control, publication):
    """Clear admission only after confirmed completion or confirmed rollback."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        owner["publications"].remove(publication)
        _write(state, owner)


def release(memory_dir, control):
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        if not owner["stopped"]:
            raise RuntimeError("Stop maintenance before releasing ownership")
        if owner["publications"]:
            raise RuntimeError("Publication is in flight or its result is uncertain; retain ownership")
        _write(state, None)
        return owner


def release_failed_startup(memory_dir, control, run_id):
    """Clean up this process's un-dispatched run, retaining uncertain publications."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        if owner["run_id"] != run_id:
            raise PermissionError("Startup cleanup is not for the current maintenance run")
        if owner["publications"]:
            return {"released": False, "owner": _public(owner)}
        stop(control)
        owner["stopped"] = True
        _write(state, None)
        return {"released": True, "owner": _public(owner)}


def save_stage(memory_dir, control, stage, output):
    """Advance the sole current stage after the host confirms the old group ended."""
    from hashlib import sha256

    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        if owner["run_id"] != stage["owner_run_id"]:
            raise PermissionError("Stage receipt does not belong to the current maintenance run")
        _begin_owned(memory_dir, owner, "Maintenance stopped before stage handoff")
        if owner["publications"]:
            raise RuntimeError("Publication is in flight or its result is uncertain; resolve the original batch before handoff")
        if owner.get("stage") != stage["previous_stage"]:
            raise ValueError("Previous stage is not the current owner stage")
        path = Path(output).resolve()
        material = json.dumps(stage, ensure_ascii=False, indent=2).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as file:
            file.write(material)
            file.flush()
            os.fsync(file.fileno())
        reference = {"path": str(path), "file_sha256": sha256(material).hexdigest(), "index": stage["index"]}
        owner["stage"] = reference
        _write(state, owner)
        return reference


def recover(memory_dir, run_id, *, owner_ended, publication_resolved):
    """Explicitly recover an abandoned run after independent verification."""
    if not owner_ended or not publication_resolved:
        raise ValueError("Verify both the owner has ended and publication has resolved")
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _read(state)
        if owner is None or owner["run_id"] != run_id:
            raise ValueError("The specified maintenance run is not the current owner")
        # Prevent any surviving worker from beginning a publication during recovery.
        stop(owner["control"])
        _write(state, None)
        return owner
