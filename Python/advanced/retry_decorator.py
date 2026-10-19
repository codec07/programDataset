"""A sync/async retry decorator with exponential backoff and jitter.

Features:
    * selectable exception types,
    * capped exponential backoff with optional jitter,
    * synchronous and ``async def`` functions from the same API,
    * an optional ``on_retry(exception, attempt, delay)`` callback,
    * the original exception is re-raised after the final attempt.

Usage:
    @retry(max_attempts=4, base_delay=0.1, exceptions=(TimeoutError,))
    def fetch():
        ...

    @retry(max_attempts=3, base_delay=0.05)
    async def fetch_async():
        ...

Run this file to see successful, exhausted, and asynchronous examples.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import random
import time
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, Sequence, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
ExceptionTypes = type[BaseException] | tuple[type[BaseException], ...]
RetryCallback = Callable[[BaseException, int, float], Awaitable[Any] | Any]


def _normalize_exceptions(exceptions: ExceptionTypes) -> tuple[type[BaseException], ...]:
    if isinstance(exceptions, type):
        return (exceptions,)
    if not exceptions:
        raise ValueError("exceptions must not be empty")
    return tuple(exceptions)


def retry(
    max_attempts: int = 3,
    *,
    exceptions: ExceptionTypes = (Exception,),
    base_delay: float = 0.05,
    max_delay: float = 2.0,
    jitter: float = 0.0,
    on_retry: RetryCallback | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a callable so failed attempts are retried.

    Args:
        max_attempts: Total attempts, including the first call.
        exceptions: Exception class or tuple of classes that trigger a retry.
        base_delay: Delay before the second attempt, in seconds.
        max_delay: Upper bound for any individual delay.
        jitter: Fractional random variation, e.g. ``0.25`` adds up to 25%.
        on_retry: Optional callback invoked before sleeping.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("delays must be non-negative")
    if jitter < 0:
        raise ValueError("jitter must be non-negative")
    caught = _normalize_exceptions(exceptions)

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        def delay_for(attempt: int) -> float:
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            if jitter and delay:
                delay *= 1.0 + random.uniform(-jitter, jitter)
            return max(0.0, delay)

        if inspect.iscoroutinefunction(function):
            async_function = function

            @wraps(async_function)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await async_function(*args, **kwargs)
                    except caught as exc:
                        if attempt >= max_attempts:
                            raise
                        delay = delay_for(attempt)
                        if on_retry is not None:
                            result = on_retry(exc, attempt, delay)
                            if inspect.isawaitable(result):
                                await result
                        await asyncio.sleep(delay)
                raise AssertionError("retry loop exited unexpectedly")

            async_wrapper.retry_config = {  # type: ignore[attr-defined]
                "max_attempts": max_attempts,
                "base_delay": base_delay,
                "exceptions": caught,
            }
            return async_wrapper  # type: ignore[return-value]

        @wraps(function)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return function(*args, **kwargs)
                except caught as exc:
                    if attempt >= max_attempts:
                        raise
                    delay = delay_for(attempt)
                    if on_retry is not None:
                        result = on_retry(exc, attempt, delay)
                        if inspect.isawaitable(result):
                            asyncio.run(result)  # type: ignore[arg-type]
                    time.sleep(delay)
            raise AssertionError("retry loop exited unexpectedly")

        sync_wrapper.retry_config = {  # type: ignore[attr-defined]
            "max_attempts": max_attempts,
            "base_delay": base_delay,
            "exceptions": caught,
        }
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _demo() -> None:
    events: list[str] = []

    def note(exc: BaseException, attempt: int, delay: float) -> None:
        events.append(f"retry {attempt} after {type(exc).__name__} in {delay:.3f}s")

    @retry(max_attempts=4, base_delay=0.01, jitter=0.1, on_retry=note)
    def eventually_works() -> str:
        if len(events) < 2:
            raise ConnectionError(f"transient failure {len(events) + 1}")
        return "connected"

    print("sync success:", eventually_works())
    print("events:")
    for event in events:
        print(" ", event)

    @retry(max_attempts=3, base_delay=0.005, exceptions=(ValueError,))
    def always_fails() -> None:
        raise ValueError("permanent problem")

    try:
        always_fails()
    except ValueError as exc:
        print(f"exhausted after 3 attempts: {exc}")

    async def async_demo() -> None:
        attempts = 0

        @retry(max_attempts=3, base_delay=0.01)
        async def async_job() -> int:
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.005)
            if attempts < 3:
                raise TimeoutError("not ready")
            return 42

        print("async result:", await async_job(), f"after {attempts} attempts")

    asyncio.run(async_demo())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retry decorator demonstration.")
    parser.add_argument("--demo", action="store_true", help="run the built-in examples")
    parser.parse_args(argv)
    _demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
