"""Independent Codex capture and verified receipts for maintenance inputs."""

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from .content import _read_bytes
from .discovery import retained_codex_paths


def _inside(root, path):
    root = Path(root).resolve()
    path = Path(path)
    target = (path if path.is_absolute() else root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Collection path leaves project: {path}")
    return target


def _write_receipt(path, receipt):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def collect(config, registry_path=None, *, control=None, output=None):
    """Capture assigned chats and record the observed project-local input hashes.

    This observation is not a lock on the files. Later preparation independently
    records its own source revision, and publication verifies that revision.
    """
    from .codex import AppServer, collect_codex, list_threads
    from .codex_binding import classify_threads, discover_binding

    root = Path(config.root).resolve()
    path = _inside(root, output or (Path(config.memory_dir) / "maintenance" /
                                    f"collection-{uuid4().hex}.json"))
    result = {"status": "started", "root": str(root), "project_id": None,
              "paths": [], "snapshots": [], "receipt": str(path),
              "snapshot_policy": "verify_on_load"}
    try:
        binding = (json.loads(Path(registry_path).read_text(encoding="utf-8")) if registry_path
                   else config.raw["memory"].get("codex", {}))
        result["project_id"] = binding.get("project_id")
        if not binding.get("project_id") or not binding.get("registry_complete"):
            result.update(status="binding_unavailable",
                          gap="Host project ID and complete registered project roots are required.")
        else:
            resolved = discover_binding(root, binding["project_id"], binding["other_project_roots"])
            client = AppServer(os.environ.get("CODEX_APP_RUNTIME_CLI_PATH", "codex"))
            try:
                discovered = classify_threads(resolved, list_threads(client, control=control))
                captured = collect_codex(binding["project_id"], [row["id"] for row in discovered["matched"]],
                                         Path(config.memory_dir) / "codex", control=control,
                                         client=client, project_binding=resolved)
            finally:
                client.close()
            snapshots = []
            for name in dict.fromkeys(captured["paths"]):
                target = _inside(root, name)
                data, _ = _read_bytes(target)
                snapshots.append({"path": target.relative_to(root).as_posix(),
                                  "sha256": sha256(data).hexdigest()})

            def identifiers(rows):
                return [{"thread_id": row["thread"]["id"], "reason": row["reason"]} for row in rows]

            result.update(status="captured", discovered=len(discovered["matched"]),
                          unresolved=len(discovered["unresolved"]),
                          gaps=len(discovered["gaps"]) + len(captured["gaps"]),
                          paths=[item["path"] for item in snapshots], snapshots=snapshots,
                          binding=resolved, unresolved_threads=identifiers(discovered["unresolved"]),
                          excluded=identifiers(discovered["excluded"]),
                          discovery_gaps=discovered["gaps"], capture=captured)
    except Exception as error:
        result.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
        try:
            _write_receipt(path, result)
        except Exception as receipt_error:
            error.add_note(f"Writing collection failure receipt {path} also failed: {receipt_error}")
        else:
            error.add_note(f"Collection failure receipt: {path}")
        raise
    _write_receipt(path, result)
    return result


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
    snapshots = receipt["snapshots"]
    if receipt["paths"] != [item["path"] for item in snapshots]:
        raise ValueError("Collection paths do not match its snapshot manifest")
    for item in snapshots:
        _inside(root, item["path"])
        data, _ = _read_bytes(_inside(root, item["path"]))
        if sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Collection snapshot changed: {item['path']}")
    return receipt


def retained_snapshots(config, project_id):
    """Explicitly select owned retained captures without claiming fresh collection."""
    retained = retained_codex_paths(config, project_id)
    return {"status": "retained", "project_id": project_id, **retained,
            "freshness": "unknown"}
