"""Independent Codex capture and verified receipts for maintenance inputs."""

from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4

from .content import _read_bytes
from .discovery import retained_codex_paths
from .maintenance import _locked, check


def _inside(root, path):
    root = Path(root).resolve()
    path = Path(path)
    target = (path if path.is_absolute() else root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Collection path leaves project: {path}")
    return target


def _write_receipt(path, receipt, *, checkpoint=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.close()
            if checkpoint is not None:
                checkpoint()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _trial_path(memory_dir):
    return Path(memory_dir) / "codex-trials.json"


def _trial_state(memory_dir, project_id):
    path = _trial_path(memory_dir)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"project_id": project_id, "pending": None, "registered": {}}
    if state["project_id"] != project_id:
        raise ValueError(f"Codex trial registry belongs to another project: {path}")
    return state


def codex_trial(config, action, *, reservation=None, thread_id=None):
    """Serialize a durable creation reservation with formal capture."""
    project_id = config.raw["memory"].get("codex", {}).get("project_id")
    if not project_id:
        raise ValueError("Codex trial registration requires a configured Codex project ID")
    memory_dir = Path(config.memory_dir)
    path = _trial_path(memory_dir)
    with _locked(memory_dir / "collection.lock"):
        state = _trial_state(memory_dir, project_id)
        pending = state["pending"]
        registered = state["registered"]
        if action == "begin":
            if pending:
                raise ValueError("A Codex trial creation reservation is already pending")
            state["pending"] = uuid4().hex
        elif action == "register":
            thread_id = str(UUID(thread_id))
            if thread_id not in registered or registered[thread_id] != reservation:
                if pending is None or pending != reservation:
                    raise ValueError("Codex trial creation reservation does not match")
                if thread_id in registered:
                    raise ValueError(f"Codex trial thread is already registered: {thread_id}")
                registered[thread_id] = reservation
                state["pending"] = None
        elif action == "cancel":
            if pending is None or pending != reservation:
                raise ValueError("Codex trial creation reservation does not match")
            state["pending"] = None
        elif action != "status":
            raise ValueError(f"Unknown Codex trial operation: {action}")
        if action != "status":
            _write_receipt(path, state)
    return {"project_id": project_id, "registry": str(path),
            "pending_reservation": state["pending"], "excluded_root_thread_ids": list(registered)}


def trial_exclusion(roots, threads):
    """Classify known and unverified trial ancestry before reading items."""
    from .codex import thread_parent

    by_id = {thread["id"]: thread for thread in threads}

    def reason(thread):
        pending = [thread]
        seen = set()
        unknown = False
        while pending:
            current = pending.pop()
            identity = current["id"]
            if identity in roots:
                return "registered_codex_trial"
            if identity in seen:
                continue
            seen.add(identity)
            parent = thread_parent(current)
            source = current.get("source")
            if (isinstance(source, dict) and "subAgent" in source and not parent):
                unknown = True
            for ancestor in (parent, current.get("forkedFromId"), current.get("attachedToThreadId")):
                if ancestor in roots:
                    return "registered_codex_trial"
                if ancestor:
                    if ancestor in by_id:
                        pending.append(by_id[ancestor])
                    else:
                        unknown = True
        if unknown:
            return "codex_trial_ancestry_unavailable"
        return None

    return reason


def collect(config, registry_path=None, *, control=None, output=None, attempt_id=None,
            thread_ids=None):
    """Capture assigned chats and record the hashes of the captured bytes.

    Explicit thread IDs limit the project-matched roots. The project lock covers
    capture and receipt publication. Later readers verify the receipt against
    the source files independently.
    """
    from . import owner
    from .codex import AppServer, collect_codex, list_threads
    from .codex_binding import classify_threads, discover_binding

    root = Path(config.root).resolve()
    memory_dir = Path(config.memory_dir).resolve()
    path = _inside(root, output or (memory_dir / "maintenance" / f"collection-{uuid4().hex}.json"))
    if path in (_trial_path(memory_dir), memory_dir / "collection.lock"):
        raise ValueError(f"Collection output is reserved: {path}")
    result = {"status": "started", "root": str(root), "project_id": None,
              "memory_dir": str(memory_dir),
              "paths": [], "snapshots": [], "receipt": str(path),
              "snapshot_policy": "verify_on_load"}

    def checkpoint():
        if attempt_id is not None:
            owner.check_attempt(memory_dir, attempt_id)
        if control:
            check(control)

    failure_path = None
    with ExitStack() as locks:
        try:
            try:
                locks.enter_context(_locked(memory_dir / "collection.lock"))
            except TimeoutError as error:
                raise TimeoutError(f"Another Codex collection is active for {root}") from error
            if attempt_id is not None and path.exists():
                raise FileExistsError(f"Collection receipt already exists for this attempt: {path}")
            failure_path = path
            checkpoint()
            selected_roots = (None if thread_ids is None
                              else list(dict.fromkeys(str(UUID(thread_id)) for thread_id in thread_ids)))
            configured = config.raw["memory"].get("codex", {})
            binding = (json.loads(Path(registry_path).read_text(encoding="utf-8"))
                       if registry_path else configured)
            result["project_id"] = project_id = binding.get("project_id")
            if registry_path and configured.get("project_id") and project_id != configured["project_id"]:
                raise ValueError("Collection registry project ID does not match the configured Codex project ID")
            trials = _trial_state(memory_dir, project_id)
            if trials["pending"]:
                raise RuntimeError("Codex collection is paused while a trial creation reservation is pending")
            if not project_id or not binding.get("registry_complete"):
                if selected_roots is not None:
                    raise ValueError("Selecting Codex threads requires a complete project binding")
                result.update(status="binding_unavailable",
                              gap="Host project ID and complete registered project roots are required.")
                _write_receipt(path, result)
                return result
            resolved = discover_binding(root, project_id, binding["other_project_roots"])
            checkpoint()
            client = AppServer(os.environ.get("CODEX_APP_RUNTIME_CLI_PATH", "codex"))
            try:
                threads = list_threads(client, checkpoint=checkpoint)
                discovered = classify_threads(resolved, threads)
                options = {}
                matched_roots = []
                if trials["registered"]:
                    options["exclusion_reason"] = trial_exclusion(trials["registered"], threads)
                for thread in discovered["matched"]:
                    reason = options["exclusion_reason"](thread) if options else None
                    if reason:
                        category = "excluded" if reason == "registered_codex_trial" else "unresolved"
                        discovered[category].append({"thread": thread, "reason": reason})
                    else:
                        matched_roots.append(thread["id"])
                capture_roots = matched_roots
                if selected_roots is not None:
                    matched_ids = set(matched_roots)
                    unmatched = [thread_id for thread_id in selected_roots if thread_id not in matched_ids]
                    if unmatched:
                        raise ValueError(f"Codex threads do not match this project: {', '.join(unmatched)}")
                    capture_roots = selected_roots
                    result["selected_root_thread_ids"] = selected_roots
                captured = collect_codex(project_id, capture_roots, memory_dir / "codex", client=client,
                                         project_binding=resolved, checkpoint=checkpoint, **options)
            finally:
                client.close()
            hashes = captured.pop("snapshot_hashes")
            snapshots = [{"path": _inside(root, name).relative_to(root).as_posix(),
                          "sha256": hashes[name]} for name in captured["paths"]]

            def identifiers(rows):
                return [{"thread_id": row["thread"]["id"], "reason": row["reason"]} for row in rows]

            completed = dict(result, status="captured", discovered=len(discovered["matched"]),
                             unresolved=len(discovered["unresolved"]),
                             gaps=len(discovered["gaps"]) + len(captured["gaps"]),
                             paths=[item["path"] for item in snapshots], snapshots=snapshots,
                             binding=resolved, unresolved_threads=identifiers(discovered["unresolved"]),
                             excluded=identifiers(discovered["excluded"]),
                             discovery_gaps=discovered["gaps"], capture=captured)
            _write_receipt(path, completed, checkpoint=checkpoint)
            return completed
        except Exception as error:
            if failure_path is None:
                failure_path = path.with_name(f"{path.stem}-failed-{uuid4().hex}{path.suffix}")
            result.update(status="failed", receipt=str(failure_path),
                          error={"type": type(error).__name__, "message": str(error)})
            try:
                _write_receipt(failure_path, result)
            except Exception as receipt_error:
                error.add_note(f"Writing collection failure receipt {failure_path} also failed: {receipt_error}")
            else:
                error.add_note(f"Collection failure receipt: {failure_path}")
            raise


def load_collection(config, path):
    """Load a receipt only if its project and exact captured bytes still match."""
    root = Path(config.root).resolve()
    receipt = json.loads(_inside(root, path).read_text(encoding="utf-8"))
    if Path(receipt["root"]).resolve() != root:
        raise ValueError("Collection receipt belongs to another project root")
    if receipt["status"] != "captured":
        raise ValueError(f"Collection did not capture a snapshot: {receipt['status']}")
    project_id = receipt["project_id"]
    configured = config.raw["memory"].get("codex", {}).get("project_id")
    if not project_id or (configured and configured != project_id):
        raise ValueError("Collection receipt belongs to another project")
    memory_dir = Path(config.memory_dir).resolve()
    if "memory_dir" in receipt and Path(receipt["memory_dir"]).resolve() != memory_dir:
        raise ValueError("Collection receipt belongs to another memory directory")
    snapshots = receipt["snapshots"]
    if receipt["paths"] != [item["path"] for item in snapshots]:
        raise ValueError("Collection paths do not match its snapshot manifest")
    for item in snapshots:
        source = _inside(root, item["path"])
        if source.parent not in (memory_dir / "codex", memory_dir / "codex-attachments"):
            raise ValueError(f"Collection snapshot belongs to another memory directory: {item['path']}")
        data, _ = _read_bytes(source)
        if sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Collection snapshot changed: {item['path']}")
    return receipt


def retained_snapshots(config, project_id):
    """Explicitly select owned retained captures without claiming fresh collection."""
    retained = retained_codex_paths(config, project_id)
    return {"status": "retained", "project_id": project_id, **retained,
            "freshness": "unknown"}
