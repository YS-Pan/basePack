"""Describe a host recovery action for a managed request refused before admission."""

from errno import ECONNREFUSED
from urllib.error import HTTPError, URLError


EMBEDDING_DRAINING_HEADER = "X-Basepack-Embedding-Draining"


class RuntimeStartRequired(RuntimeError):
    def __init__(self, result: dict):
        self._result = result
        super().__init__(result["error"])

    @property
    def result(self) -> dict:
        notes = getattr(self, "__notes__", None)
        return self._result | {"notes": notes} if notes else self._result


def refused(error: OSError) -> bool:
    reason = error.reason if isinstance(error, URLError) else error
    return isinstance(reason, ConnectionRefusedError) or (
        isinstance(reason, OSError)
        and (reason.errno == ECONNREFUSED or getattr(reason, "winerror", None) == 10061)
    )


def managed(config, component: str) -> bool:
    return config.raw.get(component, {}).get("windows_task") is True


def embedding_draining(error: OSError) -> bool:
    return (isinstance(error, HTTPError) and error.code == 503
            and error.headers is not None and error.headers.get(EMBEDDING_DRAINING_HEADER) == "1")


def raise_if_managed_refusal(error: OSError, component: str, config) -> None:
    draining = component == "embedding" and embedding_draining(error)
    if not (refused(error) or draining) or not managed(config, component):
        return
    if draining:
        error.close()
    from .control import start_command

    try:
        command = start_command(config, component)
    except (OSError, ValueError) as binding_error:
        raise RuntimeStartRequired({
            "status": "runtime_unavailable",
            "component": component,
            "error": str(error),
            "binding_error": str(binding_error),
        }) from error
    raise RuntimeStartRequired({
        "status": "runtime_start_required",
        "component": component,
        "error": str(error),
        **command,
    }) from error
