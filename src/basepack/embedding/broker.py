"""Explicit machine launcher: start this outside every Condor job tree."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import threading
import time

from basepack.project.config import load_machine_config
from .owned import OwnedJob, process_alive
from .transport import (atomic_json, directory, instance_key, make_server, marker_path,
                        read_marker, registry_lock, rpc)


def serve(machine):
    if "_CONDOR_JOB_AD" in os.environ or "_CONDOR_SCRATCH_DIR" in os.environ:
        raise RuntimeError("start the embedding broker outside the Condor job process tree")
    home = directory(machine)
    home.mkdir(parents=True, exist_ok=True)
    child = None
    mutex = threading.Lock()
    stopping = threading.Event()
    starts = 0
    owned = None
    worker_marker = None
    worker_path = marker_path(machine, "worker")
    broker_path = marker_path(machine, "broker")

    def await_endpoint(deadline):
        while not worker_path.exists():
            if child.poll() is not None:
                raise RuntimeError(f"embedding worker exited {child.returncode}; stderr: {home / 'worker.stderr.log'}")
            if time.time() >= deadline:
                raise TimeoutError(f"embedding worker endpoint startup expired; pid={child.pid}; stderr: {home / 'worker.stderr.log'}")
            time.sleep(0.05)
        return read_marker(machine, "worker")

    def ensure(deadline):
        nonlocal child, starts, owned, worker_marker
        with mutex:
            if stopping.is_set():
                raise RuntimeError("embedding broker is stopping")
            if child is not None and child.poll() is None:
                if worker_marker is None:
                    worker_marker = await_endpoint(deadline)
                try:
                    touched = rpc(worker_marker, "touch", timeout=5)
                except OSError:
                    # A just-crashed worker may still have an unsignalled process handle.
                    child.wait(timeout=min(5, max(0.1, deadline - time.time())))
                else:
                    if not touched["stopping"]:
                        return worker_marker
                    child.wait(timeout=max(0.1, deadline - time.time()))
            if worker_path.exists():
                previous = json.loads(worker_path.read_text(encoding="utf-8"))
                if process_alive(previous["pid"]):
                    raise RuntimeError(f"existing embedding worker pid={previous['pid']}; stop it before creating another")
                worker_path.unlink()
            if owned is not None:
                owned.close()
            worker_marker = None
            log = home / "worker.stderr.log"
            environment = os.environ.copy()
            environment.update({"PYTHONUTF8": "1", "OMP_NUM_THREADS": str(machine.raw["embedding"]["cpu_threads"]),
                "MKL_NUM_THREADS": str(machine.raw["embedding"]["cpu_threads"]), "TOKENIZERS_PARALLELISM": "false"})
            with log.open("ab") as output:
                child = subprocess.Popen([sys.executable, "-u", "-m", "basepack.embedding.worker",
                    "--machine-config", str(machine.path)], stdin=subprocess.DEVNULL,
                    stdout=output, stderr=output, env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            starts += 1
            try:
                owned = OwnedJob(child)
            except OSError:
                child.terminate()
                child.wait()
                raise
            worker_marker = await_endpoint(deadline)
            return worker_marker

    def dispatch(action, payload):
        if action == "ensure":
            return ensure(payload["deadline"])
        if action == "status":
            with mutex:
                live = child is not None and child.poll() is None
                worker = None
                if live and worker_marker is not None:
                    try:
                        worker = rpc(worker_marker, "status", timeout=5)
                    except OSError:
                        # The worker may finish its idle shutdown between poll and RPC.
                        child.wait(timeout=1)
                        live = False
            return {"broker_pid": os.getpid(), "worker_pid": child.pid if live else None,
                    "worker_starts": starts, "service_key": instance_key(machine),
                    "worker": worker}
        if action == "stop":
            stopping.set()
            return {"broker_pid": os.getpid(), "stopping": True}
        raise ValueError(f"unknown broker action: {action}")

    with registry_lock(home / "broker.lock"):
        auth = secrets.token_hex(32)
        server = make_server(auth, dispatch)
        marker = {"pid": os.getpid(), "port": server.server_address[1], "auth": auth,
                  "service_key": instance_key(machine), "created_at": time.time()}
        atomic_json(broker_path, marker)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            stopping.wait()
            with mutex:
                if child is not None and child.poll() is None:
                    if worker_marker is None:
                        child.terminate()
                    else:
                        rpc(worker_marker, "stop", timeout=10)
                    child.wait(timeout=120)
        finally:
            if owned is not None:
                owned.close()
            server.shutdown()
            server.server_close()
            broker_path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine-config", required=True)
    args = parser.parse_args()
    serve(load_machine_config(args.machine_config))


if __name__ == "__main__":
    main()
