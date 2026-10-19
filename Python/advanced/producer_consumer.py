"""A bounded producer/consumer pipeline using ``queue.Queue`` and sentinels.

Producers block when the queue is full (backpressure), consumers process work
until they receive one ``None`` sentinel each, and exceptions raised while
handling an item are recorded instead of killing the worker thread. A stop
event lets the whole pipeline shut down cleanly on interruption.

Usage:
    python producer_consumer.py
    python producer_consumer.py --producers 4 --consumers 2 --items 20 --queue-size 4
    python producer_consumer.py --strict      # re-raise the first item error

The demo intentionally makes values divisible by seven fail so error
propagation is visible.
"""

from __future__ import annotations

import argparse
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Sequence

SENTINEL = None
WorkItem = tuple[str, int, int, float]  # producer name, sequence, value, delay


@dataclass(slots=True)
class PipelineResult:
    produced: int = 0
    consumed: int = 0
    errors: list[tuple[str, BaseException]] = field(default_factory=list)
    max_queue_depth: int = 0
    elapsed: float = 0.0

    def raise_for_errors(self) -> None:
        """Raise a RuntimeError chained to the first handler failure."""
        if self.errors:
            name, error = self.errors[0]
            raise RuntimeError(f"{len(self.errors)} item(s) failed, first at {name}") from error


def process_item(item: WorkItem) -> int:
    """Square a value; multiples of seven simulate a poisoned payload."""
    _, _, value, delay = item
    time.sleep(delay)
    if value % 7 == 0:
        raise ValueError(f"cannot process poisoned value {value}")
    return value * value


def _producer(
    name: str,
    count: int,
    work: "queue.Queue[WorkItem | None]",
    stop: threading.Event,
    result: PipelineResult,
    lock: threading.Lock,
    delay: float,
) -> None:
    for sequence in range(count):
        if stop.is_set():
            return
        value = sequence + 1 + (len(name) % 5)
        item: WorkItem = (name, sequence, value, delay)
        while not stop.is_set():
            try:
                work.put(item, timeout=0.1)
                break
            except queue.Full:
                continue
        else:
            return
        with lock:
            result.produced += 1
            result.max_queue_depth = max(result.max_queue_depth, work.qsize())
    time.sleep(delay)


def _consumer(
    name: str,
    work: "queue.Queue[WorkItem | None]",
    stop: threading.Event,
    result: PipelineResult,
    lock: threading.Lock,
) -> None:
    while True:
        try:
            item = work.get(timeout=0.1)
        except queue.Empty:
            if stop.is_set() and work.empty():
                return
            continue
        if item is SENTINEL:
            work.task_done()
            return
        try:
            process_item(item)
        except Exception as exc:  # Record and continue with the next item.
            with lock:
                result.errors.append((name, exc))
        else:
            with lock:
                result.consumed += 1
        finally:
            work.task_done()


def run_pipeline(
    *,
    producers: int = 3,
    consumers: int = 3,
    items_per_producer: int = 11,
    queue_size: int = 6,
    strict: bool = False,
) -> PipelineResult:
    """Run the full pipeline to completion and return aggregate statistics."""
    if min(producers, consumers, items_per_producer, queue_size) < 1:
        raise ValueError("producers, consumers, items, and queue size must be positive")
    work: "queue.Queue[WorkItem | None]" = queue.Queue(maxsize=queue_size)
    stop = threading.Event()
    lock = threading.Lock()
    result = PipelineResult()
    producer_threads = [
        threading.Thread(
            target=_producer,
            name=f"producer-{index}",
            args=(
                f"P{index}",
                items_per_producer,
                work,
                stop,
                result,
                lock,
                0.001 + index * 0.0007,
            ),
            daemon=True,
        )
        for index in range(producers)
    ]
    consumer_threads = [
        threading.Thread(
            target=_consumer,
            name=f"consumer-{index}",
            args=(f"C{index}", work, stop, result, lock),
            daemon=True,
        )
        for index in range(consumers)
    ]

    started = time.perf_counter()
    for thread in consumer_threads:
        thread.start()
    for thread in producer_threads:
        thread.start()
    try:
        for thread in producer_threads:
            thread.join(timeout=10)
        if any(thread.is_alive() for thread in producer_threads):
            raise RuntimeError("producers did not finish within the timeout")
        for _ in consumer_threads:
            while True:
                try:
                    work.put(SENTINEL, timeout=0.1)
                    break
                except queue.Full:
                    if stop.is_set():
                        break
        for thread in consumer_threads:
            thread.join(timeout=10)
        if any(thread.is_alive() for thread in consumer_threads):
            raise RuntimeError("consumers did not finish within the timeout")
    finally:
        stop.set()
        result.elapsed = time.perf_counter() - started
    if strict:
        result.raise_for_errors()
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded producer/consumer demo.")
    parser.add_argument("--producers", type=int, default=3)
    parser.add_argument("--consumers", type=int, default=3)
    parser.add_argument("--items", type=int, default=11, dest="items_per_producer")
    parser.add_argument("--queue-size", type=int, default=6)
    parser.add_argument("--strict", action="store_true", help="raise after the run if any items failed")
    args = parser.parse_args(argv)
    try:
        result = run_pipeline(
            producers=args.producers,
            consumers=args.consumers,
            items_per_producer=args.items_per_producer,
            queue_size=args.queue_size,
            strict=False,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(
        f"produced={result.produced}, consumed={result.consumed}, "
        f"errors={len(result.errors)}, max_queue_depth={result.max_queue_depth}, "
        f"elapsed={result.elapsed:.3f}s"
    )
    for name, error in result.errors[:5]:
        print(f"  {name}: {type(error).__name__}: {error}")
    if args.strict:
        try:
            result.raise_for_errors()
        except RuntimeError as exc:
            print(f"strict mode propagated: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
