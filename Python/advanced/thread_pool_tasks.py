"""Run, monitor, time out, and cancel tasks with ``concurrent.futures``.

``TaskPool`` wraps a ``ThreadPoolExecutor`` with named submissions, structured
outcomes, per-batch timeouts, cancellation, and predictable shutdown. It is
suited to blocking I/O such as file access or HTTP clients; CPU-bound work
should use processes instead.

Usage:
    python thread_pool_tasks.py --workers 4 --tasks 12
    python thread_pool_tasks.py --timeout 0.05     # demonstrate cancellation

The demo simulates I/O with ``time.sleep``, includes one intentional failure,
and finishes in well under a second with the default arguments.
"""

from __future__ import annotations

import argparse
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

OutcomeStatus = str


@dataclass(frozen=True, slots=True)
class Outcome:
    name: str
    status: OutcomeStatus  # "ok", "error", "cancelled", or "timeout"
    value: Any = None
    error: BaseException | None = None


class TaskPool:
    """A small, named-task facade over ``ThreadPoolExecutor``."""

    def __init__(self, max_workers: int = 4, *, name_prefix: str = "task") -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=name_prefix
        )
        self._lock = threading.Lock()
        self._closed = False
        self._submitted = 0
        self._completed = 0
        self._failed = 0

    def submit(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Future[Any]:
        """Submit a callable with a human-readable name."""
        with self._lock:
            if self._closed:
                raise RuntimeError("TaskPool is shut down")
            self._submitted += 1
        future = self._executor.submit(function, *args, **kwargs)
        future.add_done_callback(self._finished)
        return future

    def _finished(self, future: Future[Any]) -> None:
        with self._lock:
            if future.cancelled():
                return
            if future.exception() is not None:
                self._failed += 1
            else:
                self._completed += 1

    def collect(
        self, futures: Mapping[str, Future[Any]], timeout: float | None = None
    ) -> list[Outcome]:
        """Wait for named futures and return one outcome per task.

        If the overall timeout expires, unfinished tasks are cancelled where
        possible. Tasks already running cannot be interrupted by threads and
        are reported as ``"timeout"``; the caller should still shut the pool
        down to wait for their cooperative completion.
        """
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        pending = dict(futures)
        outcomes: dict[str, Outcome] = {}
        try:
            for future in as_completed(pending.values(), timeout=timeout):
                name = next(key for key, value in pending.items() if value is future)
                if future.cancelled():
                    outcomes[name] = Outcome(name, "cancelled")
                else:
                    try:
                        outcomes[name] = Outcome(name, "ok", value=future.result())
                    except BaseException as exc:  # Preserve task failures as data.
                        outcomes[name] = Outcome(name, "error", error=exc)
                del pending[name]
        except FutureTimeoutError:
            for name, future in pending.items():
                if future.cancel():
                    outcomes[name] = Outcome(name, "cancelled")
                else:
                    outcomes[name] = Outcome(name, "timeout")
        return [outcomes[name] for name in futures]

    def cancel(self, futures: Mapping[str, Future[Any]]) -> int:
        """Cancel every future that has not started, returning the count."""
        return sum(1 for future in futures.values() if future.cancel())

    @property
    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "submitted": self._submitted,
                "completed": self._completed,
                "failed": self._failed,
                "workers": self.max_workers,
            }

    def shutdown(self, *, wait: bool = True) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def __enter__(self) -> "TaskPool":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.shutdown(wait=True)


def simulated_io(index: int, delay: float) -> int:
    """A deterministic I/O-like task; index 5 intentionally raises."""
    time.sleep(delay)
    if index == 5:
        raise RuntimeError("simulated backend failure")
    return index * index


def _demo(workers: int, tasks: int, timeout: float) -> None:
    pool = TaskPool(workers, name_prefix="demo-worker")
    futures: dict[str, Future[Any]] = {}
    try:
        for index in range(tasks):
            delay = 0.008 + (index % 4) * 0.006
            futures[f"job-{index:02d}"] = pool.submit(
                f"job-{index:02d}", simulated_io, index, delay
            )
        outcomes = pool.collect(futures, timeout=timeout)
        print(f"workers={workers}, tasks={tasks}, timeout={timeout:g}s")
        for outcome in outcomes:
            if outcome.status == "ok":
                print(f"  {outcome.name}: ok -> {outcome.value}")
            elif outcome.status == "error":
                print(f"  {outcome.name}: error -> {outcome.error}")
            else:
                print(f"  {outcome.name}: {outcome.status}")
        print("stats:", pool.stats)

        # A second batch deliberately exceeds a tiny timeout.
        slow = {
            f"slow-{index}": pool.submit(
                f"slow-{index}", simulated_io, index, 0.12
            )
            for index in range(workers * 2)
        }
        timed_out = pool.collect(slow, timeout=0.01)
        counts: dict[str, int] = {}
        for outcome in timed_out:
            counts[outcome.status] = counts.get(outcome.status, 0) + 1
        print("timeout batch:", counts)
    finally:
        pool.shutdown(wait=True)
    print("shutdown complete; all worker threads joined")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Concurrent futures task-pool demo.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)
    if args.workers < 1 or args.tasks < 1:
        parser.error("workers and tasks must be positive")
    _demo(args.workers, args.tasks, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
