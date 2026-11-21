"""Native transfers for a registered project memory database."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import mkstemp
from urllib.error import HTTPError
from urllib.request import Request

from .activity import memory_operation
from .control import _load, _target
from .http import managed_opener
from ..memory.store import Memory


def _claim_restore_target(memory: Memory) -> None:
    if memory._execute("INFO FOR ROOT;", check_project=False)[0]["namespaces"]:
        raise ValueError("Restore requires a fresh, independent store with no namespaces. Do not run memory init first.")
    namespace, database = (
        "`" + memory.connection[key].replace("\\", "\\\\").replace("`", "\\`") + "`"
        for key in ("namespace", "database")
    )
    # A competing import of the same project must fail the namespace definition.
    memory._execute(
        f"BEGIN; DEFINE NAMESPACE {namespace}; USE NS {namespace}; DEFINE DATABASE {database}; COMMIT;",
        check_project=False,
    )


def _native_export(executable, endpoint, memory, file):
    environment = os.environ | {
        "SURREAL_USER": memory.connection["username"],
        "SURREAL_PASS": memory.config.memory_password_file.read_bytes().decode("utf-8-sig"),
        "NO_PROXY": "*",
    }
    environment.pop("SURREAL_TOKEN", None)
    subprocess.run(
        [executable, "export", "--endpoint", endpoint, "--auth-level", "root",
         "--namespace", memory.connection["namespace"], "--database", memory.connection["database"],
         "--", str(file)],
        check=True, env=environment, stdout=sys.stderr,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _native_import(endpoint: str, memory: Memory, file: Path) -> None:
    # The 4.0 Windows CLI's file upload can disconnect before completing.
    with file.open("rb") as stream:
        request = Request(endpoint + "/import", stream, {
            "Authorization": memory._authorization,
            "surreal-ns": memory.connection["namespace"],
            "surreal-db": memory.connection["database"],
            "Content-Type": "application/octet-stream",
            "Content-Length": str(os.fstat(stream.fileno()).st_size),
            "Accept": "application/json",
        })
        try:
            with managed_opener().open(request) as response:
                failures = json.load(response)
        except HTTPError as error:
            error.add_note(error.read().decode("utf-8", errors="replace"))
            raise
    if failures != []:
        raise ValueError(f"SurrealDB import reported failed statements: {failures}")


def transfer(config, action: str, file: str) -> dict:
    """Keep the same instance admitted while verifying and running the native command."""
    if action not in ("export", "import"):
        raise ValueError(f"Unknown native transfer: {action}")
    file = Path(file).absolute()
    if action == "import" and not file.is_file():
        raise FileNotFoundError(f"No backup file at {file}")
    with memory_operation(config) as lease:
        memory = Memory(config)
        endpoint = lease.endpoint if lease is not None else memory.connection["endpoint"].rstrip("/")
        if action == "import":
            if lease is None:
                raise ValueError("Managed restore requires a dynamic endpoint or a registered idle timeout.")
            _claim_restore_target(memory)
            _native_import(endpoint, memory, file)
            memory.verify_project()
        else:
            _, binding = _load(_target(config, "memory"))
            memory.verify_project()
            fd, temporary = mkstemp(prefix=".backup-", suffix=".surql", dir=file.parent)
            os.close(fd)
            temporary = Path(temporary)
            try:
                _native_export(binding["surreal_exe"], endpoint, memory, temporary)
                temporary.replace(file)
            finally:
                temporary.unlink(missing_ok=True)
    return {"status": "exported" if action == "export" else "imported", "endpoint": endpoint, "file": str(file)}
