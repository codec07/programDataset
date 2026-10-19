"""An asyncio worker pool with bounded queues, graceful shutdown, and errors.

The pool accepts synchronous or asynchronous callables, runs at most
``workers`` of them at once, and returns one future per submission. Failures
are delivered through the future rather than killing the worker, so the pool
keeps making progress. Shutdown drains queued work and always joins tasks.

``asyncio.gather`` is used instead of ``TaskGroup`` so the module runs on
Python 3.10 as well as newer versions.

Usage:
    python asyncio_worker_pool.py --workers 4 --jobs 20
    python asyncio_worker_pool.py --workers 2 --jobs 6 --cancel

The demo finishes in a fraction of a second and reports peak concurrency.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

_STOP = object()


@dataclass(slots=True)
class Job:
    name: str
    function: Callable[..., Any]
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    future: asyncio.Future[Any] = field(default=None)  # type: ignore[assignment]


class WorkerPool:
    """A fixed-size pool of asyncio worker tasks."""

    def __init__(self, workers: int = 4, *, max_queue: int = 0) -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        if max_queue < 0:
            raise ValueError("max_queue must not be negative")
        self.workers = workers
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_queue)
        self._tasks: list[asyncio.Task[None]] = []
        self._started = False
        self._closed = False
        self._active = 0
        self._max_active = 0
        self._processed = 0
        self._failed = 0

    async def start(self) -> None:
        """Launch worker tasks; safe to call more than once."""
        if self._started:
            return
        self._started = True
        self._tasks = [
            asyncio.create_task(self._worker(index), name=f"worker-{index}")
            for index in range(self.workers)
        ]

    async def submit(
        self, function: Callable[..., Any], *args: Any, name: str | None = None, **kwargs: Any
    ) -> asyncio.Future[Any]:
        """Queue a callable and return a future for its result."""
        if self._closed:
            raise RuntimeError("WorkerPool is closed")
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        job = Job(
            name=name or getattr(function, "__name__", "job"),
            function=function,
            args=args,
            kwargs=kwargs,
            future=future,
        )
        await self._queue.put(job)
        return future

    async def _worker(self, index: int) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item is _STOP:
                    return
                job: Job = item
                if job.future.cancelled():
                    continue
                self._active += 1
                self._max_active = max(self._max_active, self._active)
                try:
                    result = job.function(*job.args, **job.kwargs)
                    if inspect.isawaitable(result):
                        result = await result
                    if not job.future.done():
                        job.future.set_result(result)
                    self._processed += 1
                except asyncio.CancelledError:
                    if not job.future.done():
                        job.future.cancel()
                    raise
                except Exception as exc:
                    self._failed += 1
                    if not job.future.done():
                        job.future.set_exception(exc)
                finally:
                    self._active -= 1
            finally:
                self._queue.task_done()

    async def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        """Stop accepting work and join workers, cancelling them on timeout."""
        if self._closed:
            return
        self._closed = True
        if not self._started:
            return
        if not wait:
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
        else:
            for _ in self._tasks:
                await self._queue.put(_STOP)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                for task in self._tasks:
                    task.cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
        self._fail_pending(RuntimeError("WorkerPool shut down before job ran"))
        self._tasks.clear()

    def _fail_pending(self, error: BaseException) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if item is not _STOP and not item.future.done():
                item.future.set_exception(error)
            self._queue.task_done()

    @property
    def stats(self) -> dict[str, int]:
        return {
            "workers": self.workers,
            "active": self._active,
            "max_active": self._max_active,
            "processed": self._processed,
            "failed": self._failed,
            "queued": self._queue.qsize(),
        }

    async def __aenter__(self) -> "WorkerPool":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.shutdown(wait=True, timeout=10.0)


async def sample_job(index: int, delay: float, *, fail: bool = False) -> int:
    """Simulate async I/O; ``fail=True`` raises after the delay."""
    await asyncio.sleep(delay)
    if fail:
        raise ValueError(f"job {index} failed on purpose")
    return index * index


async def _demo(workers: int, jobs: int, cancel_demo: bool) -> None:
    async with WorkerPool(workers, max_queue=max(1, workers)) as pool:
        futures = [
            await pool.submit(
                sample_job,
                index,
                0.01 + (index % 4) * 0.008,
                fail=(index == 4),
                name=f"job-{index}",
            )
            for index in range(jobs)
        ]
        results = await asyncio.gather(*futures, return_exceptions=True)
        successes = sum(1 for result in results if not isinstance(result, BaseException))
        failures = [result for result in results if isinstance(result, BaseException)]
        print(f"completed: {successes} ok, {len(failures)} failed")
        if failures:
            print(f"  first failure: {type(failures[0]).__name__}: {failures[0]}")
        print(
            "stats:",
            {key: value for key, value in pool.stats.items() if key != "queued"},
        )

    if cancel_demo:
        pool = WorkerPool(2, max_queue=8)
        await pool.start()
        futures = [
            await pool.submit(sample_job, index, 0.05, name=f"slow-{index}")
            for index in range(6)
        ]
        await asyncio.sleep(0)
        futures[5].cancel()
        outcomes = await asyncio.gather(*futures, return_exceptions=True)
        cancelled = sum(
            1
            for outcome in outcomes
            if isinstance(outcome, asyncio.CancelledError)
        )
        print(f"cancellation demo: {cancelled} job cancelled, {len(outcomes)} total")
        await pool.shutdown(wait=True, timeout=5.0)
        print("cancellation demo: shutdown complete")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Asyncio worker pool demonstration.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--cancel", action="store_true", help="also run the cancellation demo")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.jobs < 1:
        parser.error("workers and jobs must be positive")
    started = time.perf_counter()
    asyncio.run(_demo(args.workers, args.jobs, args.cancel))
    print(f"demo finished in {time.perf_counter() - started:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
