"""Bind one installed runtime and its OS task to each managed facility."""

from ipaddress import ip_address
import json
import os
from pathlib import Path
from socket import create_connection
import sys
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from uuid import UUID

from .activity import DYNAMIC_MEMORY_ENDPOINT, uses_activity
from .http import managed_opener
from .recovery import embedding_draining, managed, refused


def _endpoint(url: str, *, allow_dynamic: bool = False) -> str:
    if allow_dynamic and url in (DYNAMIC_MEMORY_ENDPOINT, DYNAMIC_MEMORY_ENDPOINT + "/"):
        return DYNAMIC_MEMORY_ENDPOINT
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or not parsed.port or not ip_address(parsed.hostname or "").is_loopback
            or parsed.username is not None or parsed.password is not None or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("Windows user tasks require an HTTP loopback endpoint with an explicit port")
    return url.rstrip("/")


def _target(config, component: str) -> dict:
    if not managed(config, component):
        raise ValueError(f"Enable [{component}].windows_task for Windows user-task hosting")
    section = config.raw[component]
    data = {"component": component, "config": str(config.path),
            "endpoint": _endpoint(section["endpoint"], allow_dynamic=component == "memory")}
    if component == "embedding":
        python = Path(section["windows_task_python"])
        if not python.is_absolute():
            raise ValueError("embedding.windows_task_python must be absolute")
        return dict(data, task_name="BasePack.User.Embedding", python=str(python),
                    settings=section, model_root=str(config.path_value("embedding", "model_root")))
    project_id = str(UUID(section["project_id"]))
    if project_id != section["project_id"]:
        raise ValueError("memory.project_id must use canonical UUID spelling")
    return dict(data, task_name=f"BasePack.User.Memory.{project_id}", python=str(config.python),
                project_id=project_id, memory_dir=str(config.memory_dir),
                password_file=str(config.memory_password_file), username=section["username"],
                namespace=section["namespace"], database=section["database"])


def _binding_path(target: dict) -> Path:
    return Path(target["python"]).parent.parent / "basepack-runtime" / f"{target['task_name']}.json"


def _load(target: dict) -> tuple[Path, dict]:
    path = _binding_path(target)
    with path.open(encoding="utf-8") as stream:
        binding = json.load(stream)
    if binding["target"] != target:
        raise ValueError(f"Config differs from the installed Windows task binding at {path}; re-register explicitly")
    return path, binding


def _launcher_python(binding: dict) -> Path:
    return Path(binding.get("launcher_python", binding["target"]["python"]))


def _task_action(path: Path, binding: dict) -> tuple[Path, list[str], Path]:
    return (_launcher_python(binding), ["-I", "-B", "-u", "-m", "basepack.runtime.launcher", str(path)],
            path.parent)


def _controller_python() -> Path:
    from ..project.config import installation

    details = installation()
    if (details["mode"] != "wheel" or not Path(details["package_dir"]).is_relative_to(Path(sys.prefix))):
        raise ValueError("Windows runtime control requires an installed basePack wheel")
    return Path(sys.executable)


def _registered_python(config, target: dict) -> None:
    if (os.name != "nt" or not sys.flags.isolated or _controller_python() != Path(target["python"])
            or Path(sys.prefix).is_relative_to(config.root)):
        raise ValueError("Register with the selected user-installed basePack wheel outside the project, "
                         "using its absolute Python executable with -I")


def register(config, component: str, *, surreal_exe: str | None, store: str | None,
             create_store: bool, at_logon: bool, idle_seconds: int | None = None) -> dict:
    from .windows import register_task

    owner = config if component == "memory" else config.machine
    target = _target(owner, component)
    _registered_python(config, target)
    path = _binding_path(target)
    launcher_python = Path(target["python"]).with_name("pythonw.exe")
    if not launcher_python.is_file():
        raise FileNotFoundError(launcher_python)
    binding = {"target": target, "launcher_python": str(launcher_python)}
    if component == "memory":
        if idle_seconds is not None:
            if type(idle_seconds) is not int or idle_seconds <= 0:
                raise ValueError("Memory idle timeout must be a positive number of seconds")
            binding["idle_seconds"] = idle_seconds
        if not surreal_exe or not store:
            raise ValueError("Memory registration requires --surreal-exe and --store")
        executable = Path(surreal_exe).resolve(strict=True)
        datastore = Path(store).resolve()
        memory_dir = Path(target["memory_dir"])
        if (not Path(surreal_exe).is_absolute() or not executable.is_file()
                or executable.is_relative_to(config.root)):
            raise ValueError("Use the absolute installed SurrealDB executable outside the project")
        if not Path(store).is_absolute() or datastore == memory_dir or not datastore.is_relative_to(memory_dir):
            raise ValueError("Store must be an absolute child path of the project's memory directory")
        if not Path(target["password_file"]).is_file():
            raise FileNotFoundError(target["password_file"])
        if not (datastore / "manifest").exists() and not create_store:
            raise FileNotFoundError(f"No existing SurrealKV store at {datastore}; first setup needs --create-store")
        if create_store and datastore.exists() and any(datastore.iterdir()) and not (datastore / "manifest").exists():
            raise ValueError(f"Refusing to create SurrealKV in a nonempty directory: {datastore}")
        binding.update(surreal_exe=str(executable), store=str(datastore))
    else:
        if surreal_exe or store or create_store or idle_seconds is not None:
            raise ValueError("SurrealDB options apply only to memory")
        from ..embedding.identity import embedding_identity

        binding["embedding_identity"] = embedding_identity(target["settings"] | {"model_root": target["model_root"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(binding, stream, ensure_ascii=False)
    except FileExistsError:
        if _load(target)[1] != binding:
            raise ValueError(f"Installed binding differs at {path}; unregister it explicitly first") from None
    if component == "memory" and create_store and not (datastore / "manifest").exists():
        path.with_suffix(".create").touch()
    result = register_task(target["task_name"], *_task_action(path, binding), at_logon=at_logon)
    if idle_seconds is not None:
        result["idle_seconds"] = idle_seconds
    return {**result, "endpoint": target["endpoint"], "log": str(path.with_suffix(".log"))}


def start_command(config, component: str) -> dict:
    target = _target(config, component)
    _load(target)
    if component == "memory":
        arguments = ["--config", target["config"], "runtime"]
    else:
        arguments = ["runtime", "--machine-config", target["config"]]
    python = _controller_python()
    if component == "memory" and Path(sys.prefix).is_relative_to(config.root):
        raise ValueError("Windows runtime recovery requires a controller installed outside the project")
    return {"task_name": target["task_name"], "endpoint": target["endpoint"],
            "argv": [str(python), "-I", "-B", "-m", "basepack", *arguments, "start", component]}


def _wait_ready(binding: dict, log: Path, result: dict, operate) -> dict:
    target = binding["target"]
    embedding = target["component"] == "embedding"
    opener = managed_opener()
    deadline = monotonic() + (180 if embedding else 40)
    may_replace_retiring = embedding and result["status"] in ("running", "queued")
    while True:
        try:
            with opener.open(target["endpoint"] + ("/health" if embedding else "/ready"), timeout=3) as response:
                health = response.status
            if not embedding:
                return result | {"health": health}
            with opener.open(target["endpoint"] + "/info", timeout=3) as response:
                info = json.load(response)
            if info["model"]["embedding_identity"] != binding["embedding_identity"]:
                raise ValueError("Unexpected embedding identity on the registered endpoint")
            return result | {"health": health, "model": info["model"]}
        except OSError as error:
            reason = error.reason if isinstance(error, URLError) else error
            disconnect = embedding and isinstance(reason, (ConnectionResetError, ConnectionAbortedError))
            unavailable = isinstance(error, HTTPError) and error.code == 503
            if not (disconnect or refused(error) or unavailable):
                raise
            if embedding and embedding_draining(error):
                may_replace_retiring = True
            if isinstance(error, HTTPError):
                error.close()
            if monotonic() >= deadline:
                raise RuntimeError(f"{target['task_name']} did not become ready at {target['endpoint']}; log: {log}") from error
            if may_replace_retiring:
                state = operate("status")
                if state["status"] in ("disabled", "unregistered"):
                    raise RuntimeError(f"{target['task_name']} became {state['status']}; log: {log}") from error
                if state["status"] == "stopped":
                    # The task we joined can stop before its replacement is requested.
                    replacement = _request_start(operate, target["endpoint"], wait_for_release=True)
                    if replacement is not None:
                        result = replacement
                        may_replace_retiring = False
            sleep(1)


def _port_in_use(endpoint: str) -> bool:
    address = urlsplit(endpoint)
    try:
        with create_connection((address.hostname, address.port), timeout=3):
            return True
    except ConnectionRefusedError:
        return False


def _request_start(operate, endpoint: str, *, wait_for_release: bool = False) -> dict | None:
    if endpoint != DYNAMIC_MEMORY_ENDPOINT and operate("status")["status"] == "stopped" and _port_in_use(endpoint):
        if operate("status")["status"] == "stopped":
            if wait_for_release:
                return None
            raise RuntimeError(f"Endpoint already in use for stopped task: {endpoint}")
    return operate("start")


def _activity_task(path, binding, action, operate):
    from .activity import ActivityUnavailable, contact, contact_path, verify_endpoint

    endpoint = binding["target"]["endpoint"]

    def report(session):
        verify_endpoint(endpoint, session.endpoint, session.origin)
        return {"endpoint": session.endpoint, "database_instance": session.database_instance}

    if action == "unregister":
        result = operate(action)
        contact_path(path).unlink(missing_ok=True)
        return result
    if action == "status":
        result = operate(action)
        try:
            with contact(path, "status") as (session, activity):
                result |= report(session)
                activity.pop("database_instance")
                result["activity"] = activity
        except ActivityUnavailable:
            pass
        return result

    log = path.with_suffix(".log")
    deadline = monotonic() + 85  # Includes one graceful drain followed by startup.

    def check_shutdown(activity):
        if activity["status"] == "shutdown-failed":
            raise RuntimeError(f"Graceful memory stop failed: {activity['shutdown_error']}; log: {log}")

    if action == "start":
        result = _request_start(operate, endpoint)
        may_start = result["status"] in ("running", "queued")
        while monotonic() < deadline:
            try:
                with contact(path, "operation") as (session, activity):
                    check_shutdown(activity)
                    if activity["status"] == "admitted":
                        instance = report(session)
                        with managed_opener().open(instance["endpoint"] + "/ready", timeout=3) as response:
                            return result | instance | {"health": response.status}
            except ActivityUnavailable:
                pass
            if may_start and operate("status")["status"] == "stopped":
                result = _request_start(operate, endpoint)
                may_start = False
            sleep(0.2)
        raise RuntimeError(f"Memory runtime did not become ready at {endpoint}; log: {log}")

    draining = False
    while monotonic() < deadline:
        result = operate("status")
        if result["status"] in ("stopped", "disabled", "unregistered"):
            if draining and result["last_task_result"] != 0:
                raise RuntimeError(f"Graceful memory stop failed; log: {log}")
            return result
        try:
            with contact(path, "status" if draining else "stop") as (_, activity):
                check_shutdown(activity)
                if activity["status"] != "draining":
                    raise RuntimeError(f"Memory runtime cannot stop: {activity}")
                draining = True
        except ActivityUnavailable:
            pass
        sleep(0.2)
    raise RuntimeError(f"Memory runtime did not stop at {endpoint}; log: {log}")


def _manage(config, component: str, action: str) -> dict:
    from .windows import task_operation

    target = _target(config, component)
    path, binding = _load(target)
    log = path.with_suffix(".log")
    task = (target["task_name"], *_task_action(path, binding))
    def operate(operation):
        return task_operation(operation, *task)

    if uses_activity(binding):
        result = _activity_task(path, binding, action, operate)
        if "idle_seconds" in binding:
            result["idle_seconds"] = binding["idle_seconds"]
    elif action == "start":
        result = _wait_ready(binding, log, _request_start(operate, target["endpoint"]), operate)
    else:
        result = operate(action)
    if action == "unregister":
        path.unlink()
        path.with_suffix(".create").unlink(missing_ok=True)
    return {"endpoint": target["endpoint"], **result, "log": str(log)}


def manage(config, component: str, action: str) -> dict:
    if component == "embedding":
        return manage_embedding(config.machine, action)
    return _manage(config, component, action)


def manage_embedding(machine, action: str) -> dict:
    return _manage(machine, "embedding", action)
