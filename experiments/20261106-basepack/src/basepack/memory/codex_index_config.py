"""Explicit authorization and project scope for metadata-only Codex indexing."""

from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
from uuid import UUID

from .privacy import privacy_rules, source_private
from .query import load_json_file, normalize_scope


def configured(config):
    return "chat_index" in config.raw["memory"]


def legacy_capture_prefixes(config):
    if not configured(config):
        return ()
    project = config.root.resolve()
    directories = [base / name for base in (config.memory_dir, project / ".basepack" / "memory")
                   for name in ("codex", "codex-attachments")]
    roots = dict.fromkeys([*directories, *(directory.resolve() for directory in directories)])
    return tuple(path.relative_to(project).as_posix().casefold() + "/"
                 for path in roots if path.is_relative_to(project))


def legacy_capture_path(config, path):
    from .content import _project_path

    prefixes = legacy_capture_prefixes(config)
    if not prefixes:
        return False
    project = config.root.resolve()
    path = _project_path(project, path.replace("\\", "/")).relative_to(project).as_posix().casefold()
    return any(path == prefix.rstrip("/") or path.startswith(prefix)
               for prefix in prefixes)


def _thread_id(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Codex index thread IDs must use canonical UUID spelling")
    return value


def _root(config, value):
    path = config.root if value == "." else Path(value)
    if not path.is_absolute():
        raise ValueError("Codex index binding roots must be absolute or '.' for this project")
    return str(path.resolve())


def _current_bindings(config, bindings):
    root = str(config.root.resolve())
    project = config.raw["memory"].get("codex", {}).get("project_id")
    return {key: row for key, row in bindings.items()
            if row["root"] == root and (not project or row["project_id"] == project)}


def _manifest_path(config):
    options = config.raw["memory"]["chat_index"]
    if not isinstance(options, dict) or set(options) != {"manifest"}:
        raise ValueError("[memory.chat_index] requires exactly one manifest path")
    source = (config.root / options["manifest"]).resolve()
    if not source.is_relative_to(config.root / ".basepack"):
        raise ValueError("Codex index manifest must be inside the project's .basepack directory")
    return source


def load_manifest(config):
    if not configured(config):
        return None
    return _manifest(config, load_json_file(_manifest_path(config)))


def _excluded_threads(config, bindings, explicit):
    excluded = {_thread_id(value) for value in explicit}
    project = config.raw["memory"].get("codex", {}).get("project_id")
    if not project:
        current_ids = {row["project_id"] for row in _current_bindings(config, bindings).values()}
        if len(current_ids) > 1:
            raise ValueError("Codex index bindings disagree on the current host project ID")
        project = next(iter(current_ids), None)
    if project:
        from .collection import _trial_state

        trial = _trial_state(config.memory_dir, project)
        if trial["pending"]:
            raise RuntimeError("Codex index access is paused while a trial creation reservation is pending")
        excluded.update(trial["registered"])
    return sorted(excluded)


def _manifest(config, data):
    if data["schema_version"] != 1:
        raise ValueError("Unsupported Codex index manifest schema")

    bindings = {}
    for key, value in data["bindings"].items():
        project_id = value["project_id"]
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("Codex index bindings require a verified host project ID")
        other_roots = value["other_project_roots"]
        if not isinstance(other_roots, list) or any(not Path(root).is_absolute() for root in other_roots):
            raise ValueError("Codex index bindings require the other registered absolute project roots")
        bindings[key] = {"root": _root(config, value["root"]), "project_id": project_id,
                         "other_project_roots": [str(Path(root).resolve()) for root in other_roots]}

    threads = {}
    private_scope = privacy_rules(config)["private_scope"]
    for row in data["threads"]:
        thread_id = _thread_id(row["thread_id"])
        if thread_id in threads:
            raise ValueError(f"Duplicate Codex index thread: {thread_id}")
        if row["binding"] not in bindings:
            raise ValueError(f"Unknown Codex index project binding for thread: {thread_id}")
        path = normalize_scope(row["path"])
        if (path in {"", "."} or path != PurePosixPath(path).as_posix()
                or path.casefold().split("/", 1)[0] == ".basepack"):
            raise ValueError(f"Invalid Codex index project path for thread: {thread_id}")
        if type(row["private"]) is not bool:
            raise ValueError(f"Explicit privacy classification is required for thread: {thread_id}")
        threads[thread_id] = {"thread_id": thread_id, "binding": row["binding"],
                              "path": path, "private": row["private"] or source_private(path, private_scope)}

    return {"schema_version": 1, "bindings": bindings, "threads": threads,
            "excluded_thread_ids": _excluded_threads(config, bindings, data.get("excluded_thread_ids", []))}


def register_thread(config, thread_id, *, binding=None):
    """Verify and admit one explicitly named current-project dialogue as private."""
    from .collection import _write_receipt
    from .maintenance import _locked

    if not configured(config):
        raise PermissionError("Codex dialogue index is disabled for this project")
    thread_id = _thread_id(thread_id)
    source = _manifest_path(config)
    with _locked(source.with_name(source.name + ".lock"), timeout=5):
        data = load_json_file(source)
        manifest = _manifest(config, data)
        if thread_id in manifest["excluded_thread_ids"]:
            raise PermissionError("Excluded Codex threads cannot be registered for dialogue indexing")
        current = _current_bindings(config, manifest["bindings"])
        if binding is None and len(current) == 1:
            binding = next(iter(current))
        if binding not in current:
            raise ValueError("Select the verified current-project binding with --binding")
        registered = next((row for row in data["threads"] if row["thread_id"] == thread_id), None)
        if registered is not None:
            if registered["binding"] != binding or not registered["private"]:
                raise PermissionError("Existing Codex dialogue approval has a different binding or privacy classification")
            return {"status": "already_registered", "manifest": str(source), **manifest["threads"][thread_id]}

        row = {"thread_id": thread_id, "binding": binding, "path": f"dialogues/current/{thread_id}", "private": True}
        if any(existing["path"] == row["path"] for existing in manifest["threads"].values()):
            raise ValueError("The default dialogue path already belongs to another authorized thread")
        candidate = {**manifest, "threads": {thread_id: row}}
        with open_host(config, manifest=candidate) as host:
            host.verify_registration(thread_id)
        with _locked(config.memory_dir / "collection.lock", timeout=5):
            if load_json_file(source) != data:
                raise RuntimeError("Codex dialogue manifest changed during host verification")
            if thread_id in _excluded_threads(config, manifest["bindings"], data.get("excluded_thread_ids", [])):
                raise PermissionError("Excluded Codex threads cannot be registered for dialogue indexing")
            data["threads"].append(row)
            _write_receipt(source, data)
        return {"status": "registered", "manifest": str(source), **row}


def visible_threads(config, *, scope="", allow_private=False):
    scope = normalize_scope(scope)
    manifest = load_manifest(config)
    if manifest is None:
        return {}
    excluded = set(manifest["excluded_thread_ids"])
    return {key: row for key, row in manifest["threads"].items()
            if key not in excluded and row["path"].startswith(scope)
            and (allow_private or not row["private"])}


@contextmanager
def open_host(config, *, checkpoint=None, manifest=None):
    """Open the registered read-only host path with a fixed authorization manifest."""
    from .codex import AppServer
    from .codex_binding import discover_binding
    from .codex_index_host import CodexDialogueHost

    manifest = load_manifest(config) if manifest is None else manifest
    if manifest is None:
        raise PermissionError("Codex dialogue index is disabled for this project")
    keys = {row["binding"] for row in manifest["threads"].values()}
    bindings = {key: discover_binding(row["root"], row["project_id"], row["other_project_roots"])
                for key, row in manifest["bindings"].items() if key in keys}
    authorized = {key: row["binding"] for key, row in manifest["threads"].items()}
    private = {key for key, row in manifest["threads"].items() if row["private"]}
    client = AppServer(os.environ.get("CODEX_APP_RUNTIME_CLI_PATH", "codex"))
    try:
        yield CodexDialogueHost(client, bindings, authorized,
                                excluded_thread_ids=manifest["excluded_thread_ids"],
                                private_thread_ids=private, checkpoint=checkpoint)
    finally:
        client.close()
