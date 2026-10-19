"""A live ANSI terminal dashboard with simulated service metrics.

The dashboard uses the alternate screen, hides the cursor, redraws in place,
and restores the terminal in a ``finally`` block. It works in Windows Terminal,
PowerShell, and modern Unix terminals. When stdout is redirected (for example
in a test harness) it skips escape sequences and prints a concise summary.

Usage:
    python terminal_dashboard.py
    python terminal_dashboard.py --duration 5 --fps 12
    python terminal_dashboard.py --duration 1 --seed 42 --no-alt-screen

No network, GPU, or third-party package is required; all metrics are generated.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import shutil
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Sequence

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
MAGENTA = "\x1b[35m"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
ALT_SCREEN = "\x1b[?1049h"
NORMAL_SCREEN = "\x1b[?1049l"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"


@dataclass(slots=True)
class Sample:
    queue_depth: int
    latency_ms: float
    throughput: float
    errors: int
    cpu: float


class Simulator:
    """Deterministic-ish synthetic metrics for the display."""

    def __init__(self, seed: int = 7) -> None:
        self.random = random.Random(seed)
        self.started = time.monotonic()
        self.queue = 12.0
        self.latency = 42.0
        self.throughput = 620.0
        self.errors = 0

    def next_sample(self, elapsed: float) -> Sample:
        wave = math.sin(elapsed * 1.7) * 0.5 + math.sin(elapsed * 0.43) * 0.5
        self.queue += wave * 2.6 + self.random.uniform(-1.7, 1.7)
        self.queue = max(0.0, min(80.0, self.queue))
        self.latency += (self.queue - 18) * 0.22 + self.random.uniform(-2.5, 2.5)
        self.latency = max(8.0, min(400.0, self.latency))
        self.throughput += wave * 18 + self.random.uniform(-25, 25)
        self.throughput = max(20.0, min(1400.0, self.throughput))
        if self.random.random() < 0.12:
            self.errors += 1
        cpu = 24 + self.queue * 0.55 + wave * 9 + self.random.uniform(-4, 4)
        return Sample(
            queue_depth=int(self.queue),
            latency_ms=self.latency,
            throughput=self.throughput,
            errors=self.errors,
            cpu=max(0.0, min(100.0, cpu)),
        )


def _fit(text: str, width: int) -> str:
    if len(text) > width:
        return text[: max(0, width - 1)] + "~"
    return text.ljust(width)


def _spark(values: Sequence[float], width: int) -> str:
    if not values:
        return " " * width
    levels = " .:-=+*#%@"
    low, high = min(values), max(values)
    span = max(1e-9, high - low)
    recent = list(values)[-width:]
    return "".join(levels[int((value - low) / span * (len(levels) - 1))] for value in recent)


def _bar(value: float, width: int) -> str:
    filled = int(max(0.0, min(1.0, value)) * width + 0.5)
    return "#" * filled + "." * (width - filled)


def render_dashboard(
    sample: Sample,
    history: Sequence[float],
    elapsed: float,
    remaining: float,
    width: int,
    *,
    color: bool,
) -> str:
    """Return one complete frame as an ANSI-decorated string."""
    width = max(58, min(width - 2, 104))
    inner = width - 4
    title = f" OPS DASHBOARD | simulated telemetry | t+{elapsed:05.2f}s "
    top = "+" + title.center(width - 2, "=") + "+"
    divider = "+" + "-" * (width - 2) + "+"
    lines: list[str] = [top]

    def row(text: str) -> None:
        lines.append("| " + _fit(text, inner) + " |")

    queue_ratio = sample.queue_depth / 80
    cpu_ratio = sample.cpu / 100
    row("")
    row(f"  QUEUE   {sample.queue_depth:>3} items   [{_bar(queue_ratio, 28)}]")
    row(f"  CPU     {sample.cpu:>5.1f}%      [{_bar(cpu_ratio, 28)}]")
    row(f"  LATENCY {sample.latency_ms:>7.1f} ms   THROUGHPUT {sample.throughput:>7.0f} req/s")
    row(f"  ERRORS  {sample.errors:>7}       UPTIME {elapsed:>10.1f} s")
    row("")
    row("  THROUGHPUT HISTORY")
    row("  " + _spark(history, inner - 4))
    row("")
    status = "HEALTHY" if sample.latency_ms < 120 and sample.cpu < 80 else "DEGRADED"
    row(f"  STATUS  {status:<10}   NEXT REFRESH {remaining:>5.2f}s")
    row("")
    lines.append(divider)
    footer = f"  Ctrl+C exits | {len(history)} samples | ANSI redraw"
    lines.append("| " + _fit(footer, inner) + " |")
    lines.append("+" + "-" * (width - 2) + "+")
    if not color:
        return "\n".join(lines)
    colored = [BOLD + CYAN + lines[0] + RESET]
    for line in lines[1:]:
        if "HEALTHY" in line:
            colored.append(GREEN + line + RESET)
        elif "DEGRADED" in line:
            colored.append(YELLOW + line + RESET)
        elif "THROUGHPUT HISTORY" in line:
            colored.append(MAGENTA + line + RESET)
        elif line.startswith("|  QUEUE") or line.startswith("|  CPU"):
            colored.append(CYAN + line + RESET)
        else:
            colored.append(line)
    return "\n".join(colored)


def _summary(samples: Sequence[Sample], elapsed: float) -> str:
    if not samples:
        return "no samples collected"
    average_latency = sum(item.latency_ms for item in samples) / len(samples)
    average_cpu = sum(item.cpu for item in samples) / len(samples)
    peak_queue = max(item.queue_depth for item in samples)
    return (
        f"dashboard summary: {len(samples)} samples over {elapsed:.2f}s, "
        f"avg latency={average_latency:.1f}ms, avg cpu={average_cpu:.1f}%, "
        f"peak queue={peak_queue}, errors={samples[-1].errors}"
    )


def run_dashboard(duration: float, fps: float, seed: int, *, alt_screen: bool) -> int:
    if duration <= 0:
        raise ValueError("duration must be positive")
    if fps <= 0 or fps > 60:
        raise ValueError("fps must be between 0 and 60")
    simulator = Simulator(seed)
    history: deque[float] = deque(maxlen=120)
    samples: list[Sample] = []
    started = time.monotonic()
    deadline = started + duration
    output = sys.stdout
    interactive = output.isatty()
    color = interactive and "NO_COLOR" not in os.environ
    columns = shutil.get_terminal_size((92, 24)).columns
    interval = 1.0 / fps
    entered_alt = False
    try:
        if interactive and alt_screen:
            output.write(ALT_SCREEN + HIDE_CURSOR + CLEAR)
            output.flush()
            entered_alt = True
        while True:
            now = time.monotonic()
            if now >= deadline:
                break
            sample = simulator.next_sample(now - started)
            samples.append(sample)
            history.append(sample.throughput)
            remaining = max(0.0, deadline - now)
            if interactive:
                frame_text = render_dashboard(
                    sample, history, now - started, remaining, columns, color=color
                )
                output.write(HOME + frame_text + "\n")
                output.flush()
            sleep_for = min(interval, max(0.0, deadline - time.monotonic()))
            if sleep_for:
                time.sleep(sleep_for)
        if not interactive:
            print(_summary(samples, time.monotonic() - started))
        elif samples:
            print(
                f"\n{RESET}{_summary(samples, time.monotonic() - started)}"
            )
    finally:
        if entered_alt:
            output.write(RESET + SHOW_CURSOR + NORMAL_SCREEN)
        elif interactive:
            output.write(RESET + SHOW_CURSOR)
        output.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ANSI live terminal dashboard demo.")
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-alt-screen", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_dashboard(
            args.duration, args.fps, args.seed, alt_screen=not args.no_alt_screen
        )
    except (ValueError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            print("\ninterrupted; terminal restored")
            return 130
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
