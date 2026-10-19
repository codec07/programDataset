"""LRU + TTL memoization decorators for synchronous and async functions.

The cache is thread-safe, has bounded size, supports expiring entries, and
reports hits, misses, evictions, and current size. Async calls use a per-key
lock so concurrent requests for the same arguments compute only once.

Usage:
    @cached(maxsize=256, ttl=30)
    def expensive(x):
        ...

    @cached(maxsize=64)
    async def fetch(url):
        ...

Run the file for a demo of FIFO/LRU behavior, TTL expiry, and async dedupe.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Hashable, NamedTuple, ParamSpec, Sequence, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
Key = tuple[Any, ...]


class CacheInfo(NamedTuple):
    hits: int
    misses: int
    maxsize: int
    currsize: int
    evictions: int


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float | None
    created_at: float


_MISSING = object()


class _Core:
    """Ordered LRU store with optional per-entry expiry."""

    def __init__(self, maxsize: int, ttl: float | None) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be positive when provided")
        self.maxsize = maxsize
        self.ttl = ttl
        self.data: OrderedDict[Key, _Entry] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: Key) -> Any:
        with self.lock:
            entry = self.data.get(key)
            if entry is None:
                self.misses += 1
                return _MISSING
            if entry.expires_at is not None and entry.expires_at <= time.monotonic():
                del self.data[key]
                self.misses += 1
                return _MISSING
            self.data.move_to_end(key)
            self.hits += 1
            return entry.value

    def put(self, key: Key, value: Any) -> None:
        with self.lock:
            now = time.monotonic()
            expires_at = now + self.ttl if self.ttl is not None else None
            if key in self.data:
                self.data[key] = _Entry(value, expires_at, now)
                self.data.move_to_end(key)
                return
            while len(self.data) >= self.maxsize:
                self.data.popitem(last=False)
                self.evictions += 1
            self.data[key] = _Entry(value, expires_at, now)

    def clear(self) -> None:
        with self.lock:
            self.data.clear()

    def info(self) -> CacheInfo:
        with self.lock:
            return CacheInfo(self.hits, self.misses, self.maxsize, len(self.data), self.evictions)


def _make_key(args: tuple[Any, ...], kwargs: dict[str, Any], typed: bool) -> Key:
    key: Key = args
    if kwargs:
        key += (tuple(sorted(kwargs.items())),)
    if typed:
        key += (tuple(type(value) for value in args),)
        if kwargs:
            key += (tuple(type(value) for _, value in sorted(kwargs.items())),)
    try:
        hash(key)
    except TypeError as exc:
        raise TypeError("cached arguments must be hashable") from exc
    return key


def cached(
    maxsize: int = 128, ttl: float | None = None, *, typed: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function with a bounded least-recently-used cache."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        core = _Core(maxsize, ttl)
        async_locks: dict[Hashable, asyncio.Lock] = {}

        def make_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Key:
            return _make_key(args, kwargs, typed)

        if inspect.iscoroutinefunction(function):
            async_function = function

            @wraps(async_function)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                key = make_key(args, kwargs)
                cached_value = core.get(key)
                if cached_value is not _MISSING:
                    return cached_value
                lock = async_locks.setdefault(key, asyncio.Lock())
                async with lock:
                    cached_value = core.get(key)
                    if cached_value is not _MISSING:
                        return cached_value
                    result = await async_function(*args, **kwargs)
                    core.put(key, result)
                    return result

            async_wrapper.cache_info = core.info  # type: ignore[attr-defined]
            async_wrapper.cache_clear = core.clear  # type: ignore[attr-defined]
            return async_wrapper  # type: ignore[return-value]

        @wraps(function)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            key = make_key(args, kwargs)
            cached_value = core.get(key)
            if cached_value is not _MISSING:
                return cached_value
            result = function(*args, **kwargs)
            core.put(key, result)
            return result

        sync_wrapper.cache_info = core.info  # type: ignore[attr-defined]
        sync_wrapper.cache_clear = core.clear  # type: ignore[attr-defined]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _demo() -> None:
    calls = 0

    @cached(maxsize=3)
    def slow_square(value: int) -> int:
        nonlocal calls
        calls += 1
        time.sleep(0.01)
        return value * value

    for number in (2, 4, 3, 2, 4):
        print(f"slow_square({number}) = {slow_square(number)}")
    print(f"  function calls: {calls}, cache: {slow_square.cache_info()}")

    short_lived_calls = 0

    @cached(maxsize=8, ttl=0.05)
    def short_lived() -> float:
        nonlocal short_lived_calls
        short_lived_calls += 1
        return time.monotonic()

    first = short_lived()
    second = short_lived()
    time.sleep(0.07)
    third = short_lived()
    print(
        f"ttl: hit={first == second}, expired={third != first}, "
        f"loads={short_lived_calls}"
    )

    async def async_demo() -> None:
        async_calls = 0

        @cached(maxsize=16)
        async def fetch(key: str) -> str:
            nonlocal async_calls
            async_calls += 1
            await asyncio.sleep(0.03)
            return f"value-for-{key}"

        results = await asyncio.gather(*(fetch("same-key") for _ in range(6)))
        print(f"async dedupe: {len(set(results))} unique result, {async_calls} load")
        print("  async cache:", fetch.cache_info())

    asyncio.run(async_demo())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thread-safe LRU/TTL cache decorator demo.")
    parser.add_argument("--demo", action="store_true", help="run the built-in examples")
    parser.parse_args(argv)
    _demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
