"""A multi-process pipeline that works on Windows with the ``spawn`` start method.

Stage layout::

    producer ─► work queue ─► N transform workers ─► result queue ─► collector

Queues are bounded for backpressure, every worker receives a stop sentinel,
per-item failures are reported on a side channel without killing workers, and
the parent terminates survivors after a deadline so the demo always exits.

Usage:
    python multiprocessing_pipeline.py --items 60 --workers 3
    python multiprocessing_pipeline.py --items 30 --workers 2 --fail-at 9
    python multiprocessing_pipeline.py --items 200 --workers 4 --timeout 20

All process entry points are module-level functions, which the Windows spawn
method requires. The ``if __name__ == "__main__"`` guard prevents child
processes from re-running the demo.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import queue
import time
from dataclasses import dataclass
from typing import Any, Sequence

Item = tuple[str, Any]
STOP: Item = ("stop", None)


def transform(value: int) -> int:
    """CPU-ish stage: square the value and add a fixed offset."""
    total = 0
    for step in range(1, value + 1):
        total += step
    return total + value * value


def _put_stop(target: "mp.Queue[Item]", count: int) -> None:
    for _ in range(count):
        while True:
            try:
                target.put(STOP, timeout=0.5)
                break
            except queue.Full:
                continue


def producer_stage(
    work: "mp.Queue[Item]",
    events: "mp.Queue[tuple[str, str]]",
    workers: int,
    items: int,
    delay: float,
) -> None:
    """Feed numbered items into the pipeline, then one stop per worker."""
    try:
        for value in range(1, items + 1):
            work.put(("item", value))
            if delay:
                time.sleep(delay)
    except BaseException as exc:  # Workers and collector must still terminate.
        events.put(("producer", f"{type(exc).__name__}: {exc}"))
    finally:
        _put_stop(work, workers)


def worker_stage(
    work: "mp.Queue[Item]",
    results: "mp.Queue[Item]",
    events: "mp.Queue[tuple[str, str]]",
    fail_at: int,
) -> None:
    """Transform items until the stop sentinel arrives."""
    completed = 0
    try:
        while True:
            kind, payload = work.get()
            if kind == "stop":
                break
            value = int(payload)
            try:
                if fail_at and value == fail_at:
                    raise ValueError(f"injected failure at item {value}")
                results.put(("result", (value, transform(value))))
                completed += 1
            except Exception as exc:
                events.put(("worker", f"item {value}: {type(exc).__name__}: {exc}"))
    except BaseException as exc:
        events.put(("worker-fatal", f"{type(exc).__name__}: {exc}"))
    finally:
        results.put(("stop", completed))


def collector_stage(
    results: "mp.Queue[Item]",
    output: "mp.Queue[dict[str, Any]]",
    events: "mp.Queue[tuple[str, str]]",
    workers: int,
    idle_timeout: float,
) -> None:
    """Aggregate results until every worker sends its stop sentinel."""
    count = 0
    total = 0
    smallest: int | None = None
    largest: int | None = None
    finished = 0
    deadline = time.monotonic() + idle_timeout
    try:
        while finished < workers:
            try:
                kind, payload = results.get(timeout=0.5)
            except queue.Empty:
                if time.monotonic() > deadline:
                    events.put(("collector", "timed out waiting for results"))
                    break
                continue
            if kind == "stop":
                finished += 1
                continue
            source, value = payload
            count += 1
            total += value
            smallest = value if smallest is None else min(smallest, value)
            largest = value if largest is None else max(largest, value)
        output.put(
            {
                "count": count,
                "total": total,
                "min": smallest,
                "max": largest,
                "workers_done": finished,
            }
        )
    except BaseException as exc:
        events.put(("collector-fatal", f"{type(exc).__name__}: {exc}"))
        output.put({"error": f"{type(exc).__name__}: {exc}"})


def _drain(events: "mp.Queue[tuple[str, str]]") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    while True:
        try:
            found.append(events.get_nowait())
        except queue.Empty:
            return found


@dataclass(slots=True)
class PipelineReport:
    summary: dict[str, Any]
    events: list[tuple[str, str]]
    elapsed: float


def run_pipeline(
    *, items: int = 60, workers: int = 3, fail_at: int = 0, timeout: float = 15.0
) -> PipelineReport:
    """Execute the spawned pipeline and always clean up child processes."""
    if items < 1 or workers < 1:
        raise ValueError("items and workers must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    context = mp.get_context("spawn")
    work: "mp.Queue[Item]" = context.Queue(maxsize=max(4, workers * 2))
    results: "mp.Queue[Item]" = context.Queue(maxsize=max(4, workers * 2))
    events: "mp.Queue[tuple[str, str]]" = context.Queue()
    output: "mp.Queue[dict[str, Any]]" = context.Queue()
    processes = [
        context.Process(
            target=producer_stage,
            name="producer",
            args=(work, events, workers, items, 0.0005),
        )
    ]
    processes.extend(
        context.Process(
            target=worker_stage,
            name=f"worker-{index}",
            args=(work, results, events, fail_at),
        )
        for index in range(workers)
    )
    processes.append(
        context.Process(
            target=collector_stage,
            name="collector",
            args=(results, output, events, workers, timeout),
        )
    )

    started = time.perf_counter()
    for process in processes:
        process.start()
    summary: dict[str, Any] = {}
    reported: list[tuple[str, str]] = []
    try:
        deadline = started + timeout
        for process in processes:
            remaining = max(0.0, deadline - time.monotonic())
            process.join(remaining)
            if process.is_alive():
                raise RuntimeError(f"{process.name} did not exit within {timeout:g}s")
        try:
            summary = output.get(timeout=2.0)
        except queue.Empty:
            raise RuntimeError("collector did not report a summary") from None
        reported = _drain(events)
        time.sleep(0.02)  # Let any final queue feeder messages arrive.
        reported.extend(_drain(events))
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(2.0)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(1.0)
        for queue_object in (work, results, events, output):
            queue_object.close()
            queue_object.join_thread()
    return PipelineReport(summary, reported, time.perf_counter() - started)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multiprocessing pipeline demo (spawn-safe).")
    parser.add_argument("--items", type=int, default=60)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--fail-at", type=int, default=0, help="inject a failure for this item")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        report = run_pipeline(
            items=args.items,
            workers=args.workers,
            fail_at=args.fail_at,
            timeout=args.timeout,
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))

    summary = report.summary
    print(
        f"pipeline finished in {report.elapsed:.2f}s with {args.workers} workers: "
        f"{summary.get('count', 0)}/{args.items} items, "
        f"total={summary.get('total')}, min={summary.get('min')}, max={summary.get('max')}"
    )
    print(f"workers that sent stop sentinels: {summary.get('workers_done')}")
    if report.events:
        print("reported errors (pipeline continued):")
        for stage, message in report.events:
            print(f"  [{stage}] {message}")
    else:
        print("no errors reported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
