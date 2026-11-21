"""Foreground launcher referenced by installed Windows scheduled tasks."""

from contextlib import redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path
from secrets import token_hex
import subprocess
import sys
from time import monotonic, sleep
import traceback
from urllib.error import HTTPError
from urllib.parse import urlsplit

from .activity import DYNAMIC_MEMORY_ENDPOINT, DYNAMIC_MEMORY_ORIGIN, uses_activity
from .control import _binding_path, _launcher_python, _target
from .http import managed_opener
from .job import install_process_job
from .recovery import refused


def _memory(binding: dict, path: Path, log) -> int:
    target = binding["target"]
    endpoint = urlsplit(target["endpoint"])
    origin = DYNAMIC_MEMORY_ORIGIN if target["endpoint"] == DYNAMIC_MEMORY_ENDPOINT else target["endpoint"]
    store = Path(binding["store"])
    fresh = not (store / "manifest").exists()
    guarded = uses_activity(binding)
    if fresh:
        if store.exists() and any(store.iterdir()):
            raise ValueError(f"Expected a SurrealKV manifest in {store}")
        path.with_suffix(".create").unlink()
    password = Path(target["password_file"]).read_bytes().decode("utf-8-sig")
    environment = os.environ | {"SURREAL_USER": target["username"], "SURREAL_PASS": password}
    if fresh and guarded:
        # A fresh guarded store can receive a native restore or explicit memory init.
        environment["SURREAL_NO_DEFAULTS"] = "true"
    argv = [
        binding["surreal_exe"], "start", "--bind", endpoint.netloc, "--allow-origin", origin,
        "surrealkv://" + store.as_posix(),
    ]
    if not guarded:
        return subprocess.run(argv, env=environment, stdout=log, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW).returncode

    import asyncio

    from .activity_server import run_activity
    from .listener_owner import process_creation_filetime
    from .surreal_process import launch_surreal

    process = launch_surreal(argv, env=environment, log=log)
    created = process_creation_filetime(process._handle)
    resolved = _wait_owned_ready(target["endpoint"], process)
    instance = dict(endpoint=resolved, origin=origin, generation=token_hex(16),
                    pid=process.pid, created_filetime=created)
    memory_dir = Path(target["memory_dir"])

    def pending_publications():
        from ..memory.owner import status

        if not (memory_dir / "maintenance" / "owner.json").exists():
            return []
        owner = status(memory_dir)
        return owner["publications"] if owner is not None else []

    return asyncio.run(run_activity(path, process, instance=instance, idle_seconds=binding.get("idle_seconds"),
                                    pending_publications=pending_publications))


def _wait_owned_ready(endpoint: str, process) -> str:
    from .listener_owner import listener_ports, owns_listener

    def resolve():
        if endpoint != DYNAMIC_MEMORY_ENDPOINT:
            return endpoint if owns_listener(endpoint, process.pid) else None
        ports = listener_ports("127.0.0.1", process.pid)
        if not ports:
            return None
        if len(ports) != 1:
            raise RuntimeError(f"Expected one SurrealDB listener for PID {process.pid}, found {ports}")
        return f"{DYNAMIC_MEMORY_ORIGIN}:{ports[0]}"

    deadline = monotonic() + 40
    opener = managed_opener()
    while True:
        if (code := process.poll()) is not None:
            raise RuntimeError(f"SurrealDB exited before becoming ready ({code})")
        if address := resolve():
            try:
                with opener.open(address + "/ready", timeout=3) as response:
                    if response.status == 200 and resolve() == address and process.poll() is None:
                        return address
            except OSError as error:
                if not refused(error) and not (isinstance(error, HTTPError) and error.code == 503):
                    raise
        if monotonic() >= deadline:
            raise TimeoutError(f"SurrealDB did not become ready at {endpoint}")
        sleep(0.1)


def _embedding(binding: dict, log_path: Path) -> None:
    from ..embedding.identity import embedding_identity
    from ..embedding.service import serve
    from ..project.config import load_machine_config

    target = binding["target"]
    machine = load_machine_config(target["config"])
    if _target(machine, "embedding") != target:
        raise ValueError("Embedding config differs from its registered task binding")
    identity = embedding_identity(target["settings"] | {"model_root": target["model_root"]})
    if identity != binding["embedding_identity"]:
        raise ValueError("Embedding identity differs from its registered task binding")
    serve(machine, worker_log=log_path, managed=True)


def main(path: Path, *, embedding_worker: bool) -> int:
    with path.open(encoding="utf-8") as stream:
        binding = json.load(stream)
    target = binding["target"]
    python = _launcher_python(binding)
    if path != _binding_path(target) or Path(sys.executable) != python:
        raise ValueError("The task must use its bound interpreter and binding path")
    log_path = path.with_suffix(".log")
    if embedding_worker:
        if target["component"] != "embedding":
            raise ValueError("Only embedding uses the encoder worker entry")
        _embedding(binding, log_path)
        return 0
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                install_process_job()
                if target["component"] == "memory":
                    return _memory(binding, path, log)
                return subprocess.run(
                    [str(python), "-I", "-B", "-u", "-m", "basepack.runtime.launcher",
                     str(path), "--embedding-worker"],
                    stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                ).returncode
            except Exception:
                traceback.print_exc()
                raise


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[1:] not in ([], ["--embedding-worker"]):
        raise SystemExit("Expected a registered binding path")
    raise SystemExit(main(Path(args[0]), embedding_worker=len(args) == 2))
