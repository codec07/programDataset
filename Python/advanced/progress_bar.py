"""ANSI progress bars with rate, ETA, and clean Windows Terminal handling.

The bar redraws one line with carriage return plus ``ESC[2K`` (erase line).
When stdout is redirected it prints milestone summaries instead of escape
sequences, so logs and CI output stay readable. ``KeyboardInterrupt`` always
restores a newline.

Usage:
    python progress_bar.py
    python progress_bar.py --duration 1.5
    python progress_bar.py --duration 4 --width 50 --unicode
    python progress_bar.py --duration 1 --no-color

The demo runs two passes and exits by itself.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from typing import IO, Iterable, Iterator, Sequence, TypeVar

T = TypeVar("T")
CLEAR_LINE = "\x1b[2K"
GREEN = "\x1b[32m"
CYAN = "\x1b[36m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"
SPINNER = "|/-\\"


def _format_seconds(seconds: float) -> str:
    if seconds < 0 or seconds == float("inf"):
        return "--:--"
    total = int(round(seconds))
    minutes, remainder = divmod(total, 60)
    return f"{minutes:02d}:{remainder:02d}"


@dataclass(slots=True)
class ProgressBar:
    """A single-line progress renderer for known-length loops."""

    total: int
    prefix: str = "progress"
    width: int = 36
    stream: IO[str] = field(default_factory=lambda: sys.stdout)
    color: bool | None = None
    unicode: bool = False
    _count: int = field(default=0, init=False)
    _started: float = field(default_factory=time.monotonic, init=False)
    _last_render: float = field(default=0.0, init=False)
    _closed: bool = field(default=False, init=False)
    _next_milestone: int = field(default=25, init=False)

    def __post_init__(self) -> None:
        if self.total <= 0:
            raise ValueError("total must be positive")
        if self.width < 10:
            raise ValueError("bar width must be at least 10")
        if self.color is None:
            self.color = bool(getattr(self.stream, "isatty", lambda: False)())
        if self.unicode:
            encoding = getattr(self.stream, "encoding", None) or "ascii"
            try:
                "█░".encode(encoding)
            except (UnicodeEncodeError, LookupError):
                # Redirected streams on Windows often use cp1252.
                self.unicode = False

    @property
    def elapsed(self) -> float:
        return max(1e-9, time.monotonic() - self._started)

    @property
    def fraction(self) -> float:
        return min(1.0, self._count / self.total)

    def _line(self, note: str = "") -> str:
        fraction = self.fraction
        filled = int(fraction * self.width)
        left, right = ("█", "░") if self.unicode else ("=", ".")
        bar = left * filled + right * (self.width - filled)
        rate = self._count / self.elapsed
        remaining = max(0.0, (self.total - self._count) / rate) if rate else float("inf")
        spin = SPINNER[int(self.elapsed * 8) % len(SPINNER)]
        percent = fraction * 100
        text = (
            f"{self.prefix} [{bar}] {percent:6.2f}% "
            f"{self._count}/{self.total} {rate:6.1f}/s ETA {_format_seconds(remaining)} {spin}"
        )
        if note:
            text += f" {note[:24]}"
        if self.color:
            bar_start = text.index("[") + 1
            bar_end = text.index("]", bar_start)
            text = (
                text[:bar_start]
                + GREEN
                + text[bar_start:bar_end]
                + RESET
                + text[bar_end:]
            )
        return text

    def advance(self, amount: int = 1, note: str = "") -> None:
        """Advance the counter and repaint (at most ~30 times per second)."""
        if self._closed:
            raise RuntimeError("progress bar is closed")
        if amount < 0:
            raise ValueError("amount must be non-negative")
        self._count = min(self.total, self._count + amount)
        if getattr(self.stream, "isatty", lambda: False)():
            now = time.monotonic()
            # The final frame is painted by finish(), avoiding a duplicate line.
            if self._count < self.total and now - self._last_render >= 1 / 30:
                self.stream.write("\r" + CLEAR_LINE + self._line(note))
                self.stream.flush()
                self._last_render = now
        else:
            milestone = int(self.fraction * 100)
            if self._count < self.total and milestone >= self._next_milestone:
                while milestone >= self._next_milestone:
                    self._next_milestone += 25
                plain = self._line(note).replace(CLEAR_LINE, "")
                self.stream.write(plain + "\n")
                self.stream.flush()

    def set(self, count: int, note: str = "") -> None:
        if count < self._count:
            raise ValueError("progress cannot move backwards")
        self.advance(count - self._count, note)

    def finish(self, note: str = "done") -> None:
        """Paint the final frame and emit a newline exactly once."""
        if self._closed:
            return
        self._count = self.total
        if getattr(self.stream, "isatty", lambda: False)():
            self.stream.write("\r" + CLEAR_LINE + self._line(note) + "\n")
        else:
            self.stream.write(self._line(note).replace(CLEAR_LINE, "") + "\n")
        self.stream.flush()
        self._closed = True

    def __enter__(self) -> "ProgressBar":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if not self._closed:
            self.finish("finished")


def track(
    iterable: Iterable[T],
    *,
    total: int | None = None,
    prefix: str = "items",
    width: int = 36,
    unicode: bool = False,
) -> Iterator[T]:
    """Yield items while updating a progress bar."""
    items = list(iterable) if total is None else iterable
    count = len(items) if total is None else total
    with ProgressBar(max(1, count), prefix=prefix, width=width, unicode=unicode) as bar:
        for item in items:
            yield item
            bar.advance()


def _demo(duration: float, width: int, unicode: bool, color: bool) -> None:
    first = max(0.05, duration * 0.65)
    steps = 42
    with ProgressBar(steps, prefix="building", width=width, unicode=unicode, color=color) as bar:
        for index in range(steps):
            time.sleep(first / steps)
            bar.advance(1, note=f"chunk {index + 1:02d}")

    second = max(0.05, duration * 0.35)
    files = 14
    with ProgressBar(files, prefix="verifying", width=width, unicode=unicode, color=color) as bar:
        for index in range(files):
            time.sleep(second / files)
            bar.advance(note=f"file {index + 1:02d}")
    print(f"completed {steps + files} simulated units in {first + second:.2f}s")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ANSI progress bar demonstration.")
    parser.add_argument("--duration", type=float, default=2.5)
    parser.add_argument("--width", type=int, default=36)
    parser.add_argument("--unicode", action="store_true", help="use block characters")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("duration must be positive")
    try:
        _demo(args.duration, args.width, args.unicode, not args.no_color)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
