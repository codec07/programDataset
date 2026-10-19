"""A small thread-safe event emitter with async support and wildcard listeners.

Handlers receive an immutable :class:`Event` containing the event name,
payload, and monotonic timestamp. ``once`` handlers remove themselves before
being called, ``"*"`` listeners observe every event, and handler failures are
aggregated into :class:`EventError` after all listeners have run.

Usage:
    emitter = EventEmitter()
    emitter.on("tick", lambda event: print(event.payload))
    emitter.emit("tick", 1)

    @emitter.on("ready")          # the decorator returns the handler
    def ready(event): ...

    await emitter.emit_async("ready")

Run this file for synchronous, wildcard, error, and async demonstrations.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import threading
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

Handler = Callable[["Event"], Awaitable[Any] | Any]


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    payload: Any = None
    timestamp: float = 0.0


class EventError(RuntimeError):
    """Raised after one or more handlers fail during an emit."""

    def __init__(self, event: str, errors: Sequence[BaseException]) -> None:
        self.event = event
        self.errors = tuple(errors)
        first = self.errors[0] if self.errors else None
        detail = f": {type(first).__name__}: {first}" if first else ""
        super().__init__(f"{len(self.errors)} handler(s) failed for {event!r}{detail}")
        if first is not None:
            self.__cause__ = first


@dataclass(slots=True)
class _Subscription:
    handler: Handler
    once: bool


class EventEmitter:
    """Synchronous/async pub-sub dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[_Subscription]] = {}
        self._lock = threading.RLock()

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """Subscribe ``handler`` to ``event``; usable directly or as a decorator."""
        if handler is None:
            def decorator(function: Handler) -> Handler:
                self.on(event, function)
                return function
            return decorator
        with self._lock:
            self._handlers.setdefault(event, []).append(_Subscription(handler, False))
        return handler

    def once(self, event: str, handler: Handler) -> Handler:
        """Subscribe a handler that is removed before its first invocation."""
        with self._lock:
            self._handlers.setdefault(event, []).append(_Subscription(handler, True))
        return handler

    def off(self, event: str, handler: Handler | None = None) -> int:
        """Remove matching handlers and return how many subscriptions were removed."""
        with self._lock:
            if event not in self._handlers:
                return 0
            if handler is None:
                removed = len(self._handlers.pop(event))
                return removed
            current = self._handlers[event]
            kept = [sub for sub in current if sub.handler is not handler]
            removed = len(current) - len(kept)
            if kept:
                self._handlers[event] = kept
            else:
                del self._handlers[event]
            return removed

    def listener_count(self, event: str | None = None) -> int:
        with self._lock:
            if event is None:
                return sum(len(items) for items in self._handlers.values())
            return len(self._handlers.get(event, ()))

    def _take(self, event: str) -> list[_Subscription]:
        """Snapshot listeners and remove any that are one-shot."""
        with self._lock:
            subscriptions = list(self._handlers.get(event, ()))
            if event != "*":
                subscriptions.extend(self._handlers.get("*", ()))
            for name in {event, "*"}:
                if name in self._handlers:
                    remaining = [sub for sub in self._handlers[name] if not sub.once]
                    if remaining:
                        self._handlers[name] = remaining
                    else:
                        del self._handlers[name]
            return subscriptions

    def emit(self, event: str, payload: Any = None) -> int:
        """Invoke synchronous listeners; async callables are rejected.

        All listeners run even when some fail. If any failed, an
        :class:`EventError` is raised containing every exception.
        """
        subscriptions = self._take(event)
        record = Event(event, payload, time.monotonic())
        errors: list[Exception] = []
        for subscription in subscriptions:
            try:
                result = subscription.handler(record)
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result):
                        result.close()
                    raise TypeError("async handler used with emit(); use emit_async()")
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise EventError(event, errors)
        return len(subscriptions)

    async def emit_async(self, event: str, payload: Any = None) -> int:
        """Invoke sync and async listeners concurrently, aggregating failures."""
        subscriptions = self._take(event)
        record = Event(event, payload, time.monotonic())

        async def invoke(subscription: _Subscription) -> None:
            result = subscription.handler(record)
            if inspect.isawaitable(result):
                await result

        results = await asyncio.gather(
            *(invoke(subscription) for subscription in subscriptions),
            return_exceptions=True,
        )
        errors = [result for result in results if isinstance(result, BaseException)]
        if errors:
            raise EventError(event, errors)
        return len(subscriptions)

    def clear(self, event: str | None = None) -> None:
        with self._lock:
            if event is None:
                self._handlers.clear()
            else:
                self._handlers.pop(event, None)


def _demo() -> None:
    emitter = EventEmitter()
    log: list[str] = []

    def greet(event: Event) -> None:
        log.append(f"greet:{event.payload}")

    def audit(event: Event) -> None:
        log.append(f"audit:{event.name}")

    emitter.on("greet", greet)
    emitter.once("greet", lambda event: log.append(f"once:{event.payload}"))
    emitter.on("*", audit)

    print("delivered:", emitter.emit("greet", "Ada"))
    print("delivered:", emitter.emit("greet", "Grace"))
    print("log:", log)
    print("listeners after once:", emitter.listener_count("greet"))
    emitter.off("greet", greet)
    print("after off:", emitter.listener_count("greet"))

    def broken(event: Event) -> None:
        raise ValueError("handler exploded")

    emitter.on("broken", broken)
    emitter.on("broken", lambda event: log.append("still ran"))
    try:
        emitter.emit("broken")
    except EventError as exc:
        print(f"aggregated error: {exc} (causes={len(exc.errors)})")

    async def async_demo() -> None:
        awaitables: list[str] = []

        def sync_handler(event: Event) -> None:
            awaitables.append("sync")

        async def async_handler(event: Event) -> None:
            await asyncio.sleep(0.01)
            awaitables.append("async")

        emitter.on("ready", sync_handler)
        emitter.on("ready", async_handler)
        count = await emitter.emit_async("ready", {"id": 7})
        print(f"async delivered: {count}, handlers={sorted(awaitables)}")

    asyncio.run(async_demo())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thread-safe event emitter demonstration.")
    parser.add_argument("--demo", action="store_true", help="run the built-in examples")
    parser.parse_args(argv)
    _demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
