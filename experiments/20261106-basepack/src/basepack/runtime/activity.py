"""Authenticated admission and endpoint discovery for registered memory runtimes."""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from hmac import compare_digest, digest
import json
from secrets import token_hex
from socket import create_connection
from urllib.parse import urlsplit

from ..project.config import DYNAMIC_MEMORY_ENDPOINT
from .recovery import managed, raise_if_managed_refusal

DYNAMIC_MEMORY_ORIGIN = "http://127.0.0.1"


class ActivityUnavailable(ConnectionRefusedError):
    """The registered launcher cannot admit an operation in this generation."""


def contact_path(binding_path):
    return binding_path.with_suffix(".activity.json")


def uses_activity(binding):
    return "idle_seconds" in binding or binding["target"]["endpoint"] == DYNAMIC_MEMORY_ENDPOINT


def proof(secret, message):
    return digest(secret, message, "sha256").hex().encode("ascii")


class _Session:
    def __init__(self, connection, reader, instance):
        self.connection = connection
        self.reader = reader
        self.database_instance = instance

    @property
    def endpoint(self):
        return self.database_instance["endpoint"]

    @property
    def origin(self):
        return self.database_instance["origin"]

    def request(self, line):
        self.connection.sendall(line.encode("ascii") + b"\n")
        return json.loads(self.read())

    def read(self):
        response = self.reader.readline(16384)
        if not response:
            raise ActivityUnavailable("Memory runtime closed its activity connection")
        return response.rstrip(b"\n")

    def hold(self, marker):
        self.request(f"hold {marker}")

    def clear(self, marker):
        self.request(f"clear {marker}")


@contextmanager
def contact(binding_path, action):
    try:
        data = json.loads(contact_path(binding_path).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ActivityUnavailable("Memory runtime has no active launcher") from error
    try:
        connection = create_connection(("127.0.0.1", data["port"]), timeout=3)
    except (ConnectionError, TimeoutError) as error:
        raise ActivityUnavailable("Memory runtime activity endpoint is unavailable") from error
    with connection, connection.makefile("rb") as reader:
        session = _Session(connection, reader, data["database_instance"])
        secret = bytes.fromhex(data["token"])
        request = f"{token_hex(16)} {action}".encode("ascii")
        try:
            connection.sendall(proof(secret, b"request " + request) + b" " + request + b"\n")
            received, _, payload = session.read().partition(b" ")
        except (ConnectionError, TimeoutError) as error:
            raise ActivityUnavailable("Memory runtime did not accept the activity connection") from error
        if not compare_digest(received, proof(secret, b"response " + request + b" " + payload)):
            raise ActivityUnavailable("Memory runtime activity response did not authenticate")
        response = json.loads(payload)
        if response["database_instance"] != session.database_instance:
            raise ActivityUnavailable("Memory runtime activity belongs to a different database generation")
        yield session, response


def _activity_binding(config):
    if not managed(config, "memory"):
        return None
    from .control import _load, _target

    target = _target(config, "memory")
    try:
        path, binding = _load(target)
    except FileNotFoundError as error:
        if target["endpoint"] == DYNAMIC_MEMORY_ENDPOINT:
            raise ActivityUnavailable("Dynamic memory requires a registered Windows runtime") from error
        # Existing managed configurations may still use an external launcher.
        return None
    return (path, target["endpoint"]) if uses_activity(binding) else None


def verify_endpoint(configured, actual, origin):
    if configured == DYNAMIC_MEMORY_ENDPOINT:
        port = urlsplit(actual).port
        if port and actual == f"{DYNAMIC_MEMORY_ORIGIN}:{port}" and origin == DYNAMIC_MEMORY_ORIGIN:
            return
    elif actual == origin == configured:
        return
    raise ValueError(f"Unexpected registered memory endpoint or origin: {actual!r}, {origin!r}")


_current = ContextVar("basepack_memory_activity", default=None)


@contextmanager
def memory_operation(config):
    """Hold launcher admission across a command, nested queries, and transactions."""
    current = _current.get()
    if current is not None and current[0] is config:
        yield current[1]
        return
    with ExitStack() as stack:
        session = None
        try:
            if binding := _activity_binding(config):
                path, endpoint = binding
                session, response = stack.enter_context(contact(path, "operation"))
                if response["status"] != "admitted":
                    message = response.get("shutdown_error", "Memory runtime is draining for shutdown")
                    raise ActivityUnavailable(message)
                verify_endpoint(endpoint, session.endpoint, session.origin)
        except ActivityUnavailable as error:
            raise_if_managed_refusal(error, "memory", config)
            raise
        token = _current.set((config, session))
        try:
            yield session
        finally:
            _current.reset(token)
