"""Machine service registration, locking and deployment matching."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path

from .identity import embedding_identity
from .transport import PROTOCOL_VERSION

# The package-relative list is the single source for service code identity.
SERVICE_FILES = (
    "project/config.py",
    "embedding/admin.py",
    "embedding/cli.py",
    "embedding/client.py",
    "embedding/identity.py",
    "embedding/process_owner.py",
    "embedding/qwen3_vl.py",
    "embedding/registry.py",
    "embedding/supervisor.py",
    "embedding/transport.py",
    "embedding/worker.py",
)


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def embedding_settings(machine):
    configured = machine.raw["embedding"]
    return {"model_root": str(machine.path_value("embedding", "model_root")),
            **{key: configured[key] for key in
               ("device", "max_length", "batch_size", "max_pixels", "idle_seconds", "cpu_threads", "gpu_memory_mib")}}


def service_state_dir(machine):
    return machine.state_dir / "embedding"


def deployment_fingerprint(machine):
    package = Path(__file__).resolve().parents[1]
    settings = embedding_settings(machine)
    value = {
        "protocol_version": PROTOCOL_VERSION,
        "embedding_identity": embedding_identity(settings),
        "embedding_settings": settings,
        "service_state_dir": str(service_state_dir(machine)),
        "code": {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
                 for name in SERVICE_FILES},
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def marker_path(machine, kind):
    return service_state_dir(machine) / f"{kind}.json"


def read_marker(machine, kind, *, require_match=True):
    path = marker_path(machine, kind)
    marker = json.loads(path.read_text(encoding="utf-8"))
    if require_match:
        if marker.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeError(f"embedding {kind} uses unsupported protocol version; stop it before restarting: {path}")
        if marker["deployment_fingerprint"] != deployment_fingerprint(machine):
            raise RuntimeError(f"embedding {kind} uses different code/configuration; stop it before restarting: {path}")
    return marker


@contextlib.contextmanager
def registry_lock(path):
    """An OS-held lock, released even when the supervisor crashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
