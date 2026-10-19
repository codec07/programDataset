"""A priority-aware asyncio scheduler for delayed sync or async jobs.

Jobs are stored in a heap keyed by due time, priority, and insertion order.
A dispatcher waits efficiently for the next deadline and hands due jobs to a
fixed pool of workers. Each ``schedule`` call returns a future, so callers can
await results, cancel pending jobs, and observe failures without crashing the
scheduler.

Usage:
    python async_task_scheduler.py --workers 3 --jobs 10
    python async_task_scheduler.py --workers 2 --jobs 6 --timeout 5

The demo schedules work at staggered delays, cancels one job, includes one
intentional failure, and exits automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import heapq
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

_STOP = object()


@dataclass(order=True, slots=True)
class _Scheduled:
    when: float
    priority: int
    sequence: int
    name: str = field(compare=False)
    function: Callable[..., Any] = field(compare=False)
    args: tuple[Any, ...] = field(compare=False)
    kwargs: dict[str, Any] = field(compare=False)
    future: asyncio.Future[Any] = field(compare=False)


class AsyncScheduler:
    """Delayed task execution with bounded worker concurrency."""

    def __init__(self, workers: int = 3, queue_size: int = 0) -> None:
        if workers < 1:
            raise ValueError("workers must be positive")
        if queue_size < 0:
            raise ValueError("queue_size must not be negative")
        self.workers = workers
        self._jobs: asyncio.Queue[Any] = asyncio.Queue(maxsize=queue_size)
        self._heap: list[_Scheduled] = []
        self._heap_lock = asyncio.Lock()
        self._wake = asyncio.Event()
        self._sequence = 0
        self._dispatcher_task: asyncio.Task[None] | None = None
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._started = False
        self._closed = False
        self._completed = 0
        self._failed = 0
        self._cancelled = 0

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._dispatcher_task = asyncio.create_task(
            self._dispatcher(), name="scheduler-dispatcher"
        )
        self._worker_tasks = [
            asyncio.create_task(self._worker(index), name=f"scheduler-worker-{index}")
            for index in range(self.workers)
        ]

    async def schedule(
        self,
        delay: float,
        function: Callable[..., Any],
        *args: Any,
        priority: int = 5,
        name: str | None = None,
        **kwargs: Any,
    ) -> asyncio.Future[Any]:
        """Schedule ``function`` after ``delay`` seconds.

        Lower priority numbers run first when multiple jobs share a deadline;
        insertion order breaks any remaining ties.
        """
        if self._closed:
            raise RuntimeError("scheduler is closed")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        async with self._heap_lock:
            self._sequence += 1
            heapq.heappush(
                self._heap,
                _Scheduled(
                    when=loop.time() + delay,
                    priority=priority,
                    sequence=self._sequence,
                    name=name or getattr(function, "__name__", "job"),
                    function=function,
                    args=args,
                    kwargs=kwargs,
                    future=future,
                ),
            )
            self._wake.set()
        return future

    async def _dispatcher(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._closed:
            next_when: float | None = None
            async with self._heap_lock:
                while self._heap and self._heap[0].future.cancelled():
                    self._cancelled += 1
                    heapq.heappop(self._heap)
                if self._heap:
                    next_when = self._heap[0].when
                self._wake.clear()
            if next_when is None:
                await self._wake.wait()
                continue
            delay = next_when - loop.time()
            if delay > 0:
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                # Re-evaluate the heap, even after a wake, to catch new priorities.
                continue
            async with self._heap_lock:
                if not self._heap:
                    continue
                job = heapq.heappop(self._heap)
            if job.future.cancelled():
                self._cancelled += 1
                continue
            await self._jobs.put(job)

    async def _worker(self, index: int) -> None:
        while True:
            item = await self._jobs.get()
            try:
                if item is _STOP:
                    return
                job: _Scheduled = item
                if job.future.cancelled():
                    self._cancelled += 1
                    continue
                try:
                    result = job.function(*job.args, **job.kwargs)
                    if inspect.isawaitable(result):
                        result = await result
                    if not job.future.done():
                        job.future.set_result(result)
                    self._completed += 1
                except asyncio.CancelledError:
                    if not job.future.done():
                        job.future.cancel()
                    raise
                except Exception as exc:
                    self._failed += 1
                    if not job.future.done():
                        job.future.set_exception(exc)
            finally:
                self._jobs.task_done()

    async def shutdown(self, *, wait: bool = True, timeout: float = 5.0) -> None:
        """Stop the dispatcher, cancel unscheduled jobs, and join workers."""
        if self._closed:
            return
        self._closed = True
        self._wake.set()
        if not self._started:
            return
        if self._dispatcher_task is not None:
            try:
                await asyncio.wait_for(self._dispatcher_task, timeout=timeout)
            except asyncio.TimeoutError:
                self._dispatcher_task.cancel()
                await asyncio.gather(self._dispatcher_task, return_exceptions=True)
        async with self._heap_lock:
            for job in self._heap:
                if not job.future.done():
                    job.future.cancel()
                self._cancelled += 1
            self._heap.clear()

        async def drain_and_stop() -> None:
            await self._jobs.join()
            for _ in self._worker_tasks:
                await self._jobs.put(_STOP)
            await asyncio.gather(*self._worker_tasks)

        try:
            if wait:
                await asyncio.wait_for(drain_and_stop(), timeout=timeout)
            else:
                for task in self._worker_tasks:
                    task.cancel()
                await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            for task in self._worker_tasks:
                task.cancel()
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        finally:
            self._worker_tasks.clear()
            self._dispatcher_task = None

    @property
    def stats(self) -> dict[str, int]:
        return {
            "workers": self.workers,
            "pending": len(self._heap),
            "queued": self._jobs.qsize(),
            "completed": self._completed,
            "failed": self._failed,
            "cancelled": self._cancelled,
        }

    async def __aenter__(self) -> "AsyncScheduler":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.shutdown(wait=True, timeout=5.0)


async def task(index: int, fail: bool = False) -> str:
    await asyncio.sleep(0.01 + (index % 3) * 0.01)
    if fail:
        raise RuntimeError(f"scheduled job {index} failed")
    return f"result-{index}"


async def _demo(workers: int, jobs: int) -> None:
    started = time.perf_counter()
    async with AsyncScheduler(workers=workers) as scheduler:
        futures = [
            await scheduler.schedule(
                delay=(index % 5) * 0.03,
                function=task,
                index=index,
                fail=(index == 3),
                priority=index % 3,
                name=f"job-{index}",
            )
            for index in range(jobs)
        ]
        if len(futures) >= 4:
            futures[-1].cancel()
        outcomes = await asyncio.gather(*futures, return_exceptions=True)
        ok = sum(1 for outcome in outcomes if not isinstance(outcome, BaseException))
        cancelled = sum(
            1 for outcome in outcomes if isinstance(outcome, asyncio.CancelledError)
        )
        failures = [
            outcome
            for outcome in outcomes
            if isinstance(outcome, BaseException)
            and not isinstance(outcome, asyncio.CancelledError)
        ]
        print(
            f"scheduled={jobs}, ok={ok}, failures={len(failures)}, "
            f"cancelled={cancelled}"
        )
        if failures:
            print(f"  first failure: {type(failures[0]).__name__}: {failures[0]}")
        print(f"stats: {scheduler.stats}")
    print(f"scheduler demo finished in {time.perf_counter() - started:.3f}s")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Priority asyncio task scheduler demo.")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.workers < 1 or args.jobs < 1:
        parser.error("workers and jobs must be positive")
    try:
        asyncio.run(asyncio.wait_for(_demo(args.workers, args.jobs), timeout=args.timeout))
    except TimeoutError:
        parser.error(f"scheduler demo exceeded {args.timeout:g}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
