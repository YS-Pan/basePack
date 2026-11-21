"""Admission and graceful shutdown for one running database generation."""

import asyncio
from hmac import compare_digest
import json
from pathlib import Path
import re
from secrets import token_bytes
from threading import Thread
import traceback

from .activity import contact_path, proof


class _Activity:
    def __init__(self, process, instance, idle_seconds, pending_publications):
        self.loop = asyncio.get_running_loop()
        self.process = process
        self.instance = instance
        self.idle_seconds = idle_seconds
        self.pending_publications = pending_publications
        self.secret = token_bytes(32)
        self.active = 0
        self.timer = None
        self.holds = set()
        self.blocked = None
        self.shutdown = self.loop.create_future()
        self.shutdown_error = None

    def rearm(self):
        if self.idle_seconds is not None and not self.shutdown.done() and not self.active and self.timer is None:
            self.blocked = None
            self.timer = self.loop.call_later(self.idle_seconds, self.expire)

    def clear_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def expire(self):
        if self.loop.time() < self.timer.when():
            # asyncio can dispatch a timer up to one clock tick early.
            self.timer = self.loop.call_at(self.timer.when(), self.expire)
            return
        self.clear_timer()
        self.request_stop("idle")

    def request_stop(self, reason):
        if self.shutdown.done():
            return
        try:
            pending = self.pending_publications()
        except (OSError, ValueError) as error:
            self.blocked = {"publication_state_error": str(error)}
            return
        if pending:
            self.blocked = {"pending_publications": pending}
        elif self.holds and reason == "idle":
            self.blocked = {"unresolved_publications": sorted(self.holds)}
        else:
            self.clear_timer()
            self.shutdown.set_result(reason)

    def status(self):
        result = {"status": "draining" if self.shutdown.done() else "ready", "active_operations": self.active}
        if self.shutdown_error is not None:
            result.update(status="shutdown-failed", shutdown_error=self.shutdown_error)
        if self.blocked is not None:
            result["idle_blocked"] = self.blocked
        if self.timer is not None:
            result["idle_remaining_seconds"] = max(0, self.timer.when() - self.loop.time())
        if self.holds:
            result["publication_markers"] = sorted(self.holds)
        return result

    async def serve(self, reader, writer):
        admitted = False

        async def reply(data, *, request=None):
            payload = json.dumps(data, ensure_ascii=True).encode("ascii")
            if request is not None:
                payload = proof(self.secret, b"response " + request + b" " + payload) + b" " + payload
            writer.write(payload + b"\n")
            await writer.drain()

        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=3)
            signature, _, request = raw.rstrip(b"\n").partition(b" ")
            if not compare_digest(signature, proof(self.secret, b"request " + request)):
                return
            _, _, action = request.partition(b" ")
            if self.process.poll() is not None:
                return
            if self.timer is not None and self.loop.time() >= self.timer.when():
                self.expire()
            if action == b"operation" and not self.shutdown.done():
                self.clear_timer()
                self.active += 1
                admitted = True
                await reply({"status": "admitted", "database_instance": self.instance}, request=request)
                while line := await reader.readline():
                    operation, _, marker = line.rstrip(b"\n").partition(b" ")
                    if re.fullmatch(rb"publication_[0-9a-f]{32}", marker) is None:
                        raise ValueError("Invalid activity publication marker")
                    if operation == b"hold":
                        self.holds.add(marker.decode("ascii"))
                    elif operation == b"clear":
                        self.holds.remove(marker.decode("ascii"))
                    else:
                        raise ValueError("Invalid activity publication operation")
                    await reply({"status": "recorded"})
            else:
                if action == b"stop" and not self.active:
                    self.request_stop("explicit")
                await reply(self.status() | {"database_instance": self.instance}, request=request)
        except (ConnectionError, TimeoutError):
            pass
        finally:
            if admitted:
                self.active -= 1
                self.rearm()
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass


async def run_activity(binding_path: Path, process, *, instance, idle_seconds, pending_publications) -> int:
    activity = _Activity(process, instance, idle_seconds, pending_publications)
    child_exit = activity.loop.create_future()

    def notify_exit():
        result = process.wait()
        activity.loop.call_soon_threadsafe(child_exit.set_result, result)

    server = await asyncio.start_server(activity.serve, "127.0.0.1", 0, limit=512)
    path = contact_path(binding_path)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps({"port": server.sockets[0].getsockname()[1],
                                         "token": activity.secret.hex(), "database_instance": instance}),
                             encoding="utf-8")
        temporary.replace(path)
        Thread(target=notify_exit, daemon=True).start()
        activity.rearm()
        await asyncio.wait((child_exit, activity.shutdown), return_when=asyncio.FIRST_COMPLETED)
        if activity.shutdown.done():
            print(f"Graceful SurrealDB stop requested ({activity.shutdown.result()})")
            try:
                await asyncio.to_thread(process.stop)
            except Exception as error:
                # The signal might already have reached SurrealDB. Keeping the
                # launcher alive avoids killing it via the job or a second signal.
                activity.shutdown_error = str(error)
                traceback.print_exc()
            else:
                print("Graceful SurrealDB stop completed")
        return await child_exit
    finally:
        activity.clear_timer()
        server.close()
        server.close_clients()
        await server.wait_closed()
        temporary.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
