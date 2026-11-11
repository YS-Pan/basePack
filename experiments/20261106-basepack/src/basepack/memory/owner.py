"""Durable project maintenance ownership and publication admission."""

import json
import os
from pathlib import Path
from uuid import uuid4

from .maintenance import _locked, begin_commit, stop


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


def acquire(memory_dir, project_id, holder, control):
    """Atomically claim the project before preflight; return the current holder if busy.

    A control path is a capability and is created exclusively. Never reuse or
    remove it: old workers must not acquire authority over a later run.
    """
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _read(state)
        if owner is not None:
            return {"acquired": False, "owner": _public(owner)}
        control = Path(_control(control))
        control.parent.mkdir(parents=True, exist_ok=True)
        with control.open("xb") as file:
            file.flush()
            os.fsync(file.fileno())
        owner = {"project_id": project_id, "holder": holder, "control": str(control),
                 "run_id": uuid4().hex, "stopped": False, "publications": []}
        _write(state, owner)
        return {"acquired": True, "owner": owner}


def status(memory_dir):
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        return _public(_read(state))


def check_owned(memory_dir, control):
    """Require the live owner before starting maintenance preflight."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        if owner["stopped"]:
            from .maintenance import MaintenanceStopped
            raise MaintenanceStopped("Maintenance stopped")
        begin_commit(control)
        return owner


def stop_owned(memory_dir, control):
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        stop(control)
        owner["stopped"] = True
        _write(state, owner)
        return owner


def begin_publication(memory_dir, control, publication=None):
    """Persist admission before transaction I/O; stop and release share this lock."""
    lock, state = _paths(memory_dir)
    with _locked(lock, timeout=5):
        owner = _owned(state, control)
        if owner["stopped"]:
            from .maintenance import MaintenanceStopped
            raise MaintenanceStopped("Maintenance stopped before publication")
        begin_commit(control)
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
