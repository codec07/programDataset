"""An asyncio token-bucket rate limiter with timeouts and burst capacity.

``AsyncRateLimiter`` refills tokens at a fixed rate, allows bursts up to its
capacity, and queues waiters fairly through an ``asyncio.Lock``. It supports
``async with`` acquisition and optional per-call timeouts.

Usage:
    limiter = AsyncRateLimiter(capacity=5, rate=10)   # 10 requests/second
    async with limiter:
        await do_request()

    await limiter.acquire(timeout=0.25)

Run this file to see sixteen tasks spread over roughly a second, plus a
timeout example that raises ``TimeoutError``.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from typing import Callable, Sequence


class AsyncRateLimiter:
    """Token bucket suitable for limiting coroutines in one event loop."""

    def __init__(
        self,
        capacity: float = 5.0,
        rate: float = 10.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.capacity = float(capacity)
        self.rate = float(rate)
        self.clock = clock
        self._tokens = float(capacity)
        self._updated = clock()
        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self._updated)
        if elapsed:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._updated = now

    @property
    def available(self) -> float:
        """Approximate number of tokens available without refilling."""
        return self._tokens

    async def acquire(self, tokens: float = 1.0, timeout: float | None = None) -> float:
        """Wait for ``tokens`` and consume them, returning the wait time.

        Raises:
            ValueError: If ``tokens`` is larger than the bucket capacity.
            TimeoutError: If a timeout was supplied and expired first.
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        if tokens > self.capacity:
            raise ValueError("cannot acquire more tokens than the bucket capacity")
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        deadline = None if timeout is None else self.clock() + timeout
        total_waited = 0.0
        while True:
            async with self._lock:
                now = self.clock()
                self._refill(now)
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return total_waited
                missing = tokens - self._tokens
                wait = missing / self.rate
            if deadline is not None:
                remaining = deadline - self.clock()
                if remaining <= 0:
                    raise TimeoutError(
                        f"could not acquire {tokens:g} token(s) within {timeout:g}s"
                    )
                wait = min(wait, remaining)
            # A tiny floor prevents a tight loop if the clock granularity is coarse.
            sleep_for = max(0.0005, wait)
            await asyncio.sleep(sleep_for)
            total_waited += sleep_for

    async def __aenter__(self) -> "AsyncRateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


async def _run_tasks(limiter: AsyncRateLimiter, count: int) -> list[float]:
    stamps: list[float] = []
    waits: list[float] = []

    async def worker() -> None:
        waits.append(await limiter.acquire())
        stamps.append(time.monotonic())
        await asyncio.sleep(0.001)

    started = time.monotonic()
    await asyncio.gather(*(worker() for _ in range(count)))
    stamps.sort()
    elapsed = time.monotonic() - started
    print(
        f"{count} acquisitions in {elapsed:.2f}s "
        f"(bucket capacity={limiter.capacity:g}, rate={limiter.rate:g}/s)"
    )
    if len(stamps) > 1:
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        average = sum(gaps) / len(gaps)
        print(f"  average spacing between completions: {average * 1000:.1f} ms")
    if waits:
        print(f"  average requested wait: {sum(waits) / len(waits) * 1000:.1f} ms")
    return stamps


async def _demo(tasks: int, capacity: float, rate: float) -> None:
    limiter = AsyncRateLimiter(capacity=capacity, rate=rate)
    await _run_tasks(limiter, tasks)

    strict = AsyncRateLimiter(capacity=1, rate=1)
    await strict.acquire()
    try:
        await strict.acquire(timeout=0.05)
    except TimeoutError as exc:
        print(f"timeout example: {exc}")
    else:
        print("timeout example: unexpectedly acquired a token")
    print(f"strict bucket available tokens after timeout: {strict.available:.3f}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Asyncio token-bucket rate limiter demo.")
    parser.add_argument("--tasks", type=int, default=16)
    parser.add_argument("--capacity", type=float, default=5.0)
    parser.add_argument("--rate", type=float, default=10.0, help="tokens per second")
    args = parser.parse_args(argv)
    if args.tasks < 1:
        parser.error("tasks must be positive")
    try:
        asyncio.run(_demo(args.tasks, args.capacity, args.rate))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
