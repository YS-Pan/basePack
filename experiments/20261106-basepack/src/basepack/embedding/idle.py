"""Idle deadlines and request admission in the single LitServe HTTP event loop."""

import asyncio
import logging
from math import isfinite
from time import monotonic

from fastapi import HTTPException
from starlette.responses import PlainTextResponse

from basepack.runtime.recovery import EMBEDDING_DRAINING_HEADER


class IdleCacheRequest:
    """Internal queue message. A JSON /predict payload cannot create this type."""


def idle_seconds(settings, managed):
    cache = settings.get("idle_cache_seconds", 60)
    stop = settings.get("idle_stop_seconds", 1800) if managed else None
    intervals = (cache, stop) if managed else (cache,)
    for seconds in intervals:
        if type(seconds) not in (int, float) or not isfinite(seconds) or seconds <= 0:
            raise ValueError("Embedding idle times must be positive finite seconds")
    if stop is not None and stop <= cache:
        raise ValueError("idle_stop_seconds must exceed idle_cache_seconds")
    return cache, stop


class EmbeddingIdle:
    def __init__(self, ready_at, cache_seconds, stop_seconds):
        self.ready_at = ready_at
        self.cache_seconds = cache_seconds
        self.stop_seconds = stop_seconds
        self.last_completion = 0.0
        self.active = 0
        self.draining = False
        self.changed = asyncio.Event()

    async def monitor(self, clear_cache, retire):
        cleared_since = None
        while True:
            self.changed.clear()
            ready = self.ready_at.value
            if self.active:
                delay = None
            elif not ready:
                delay = self.cache_seconds or self.stop_seconds  # A replacement worker is loading.
            else:
                since = max(ready, self.last_completion)
                elapsed = monotonic() - since
                if self.stop_seconds is not None and elapsed >= self.stop_seconds:
                    self.draining = True
                    # Give concurrent callers a marked 503 before Uvicorn closes
                    # its Windows listener. No prediction can enter during this second.
                    await asyncio.sleep(1)
                    retire()
                    return
                if self.cache_seconds is not None and since != cleared_since:
                    delay = self.cache_seconds - elapsed
                    if delay <= 0:
                        cleared_since = since
                        try:
                            # Submission enters the native worker FIFO before yielding.
                            await clear_cache()
                        except HTTPException:
                            logging.getLogger("litserve").exception("Embedding idle cache release failed")
                        continue
                else:
                    delay = None if self.stop_seconds is None else self.stop_seconds - elapsed
                    # A restarted LitServe worker publishes a fresh ready time
                    # even when no client connects. Observe it by its short deadline.
                    if self.cache_seconds is not None and (delay is None or delay > self.cache_seconds):
                        delay = self.cache_seconds
            try:
                async with asyncio.timeout(delay):
                    await self.changed.wait()
            except TimeoutError:
                pass


class AdmissionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        idle = scope["app"].state.embedding_idle
        if idle.draining:
            reply = PlainTextResponse("Embedding runtime is retiring", status_code=503,
                                      headers={EMBEDDING_DRAINING_HEADER: "1"})
            return await reply(scope, receive, send)
        if scope["method"] != "POST" or scope["path"] != "/predict":
            return await self.app(scope, receive, send)
        idle.active += 1
        idle.changed.set()
        try:
            # LitServe's regular handler awaits the worker result even after a
            # client disconnects. Keep admission through queue, inference and send.
            return await self.app(scope, receive, send)
        finally:
            idle.active -= 1
            if not idle.active:
                idle.last_completion = monotonic()
                idle.changed.set()
