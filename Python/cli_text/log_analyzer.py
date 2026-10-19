#!/usr/bin/env python3
"""Summarise web-server or application logs without external tools.

Recognised line shapes:
  * Nginx/Apache access logs (combined or common) - client IP, request,
    status code, response size, timestamp.
  * Timestamped application logs containing DEBUG/INFO/WARNING/ERROR/
    CRITICAL/FATAL and an ISO-like timestamp.

The report includes level and status-code breakdowns, top client IPs,
top request paths, transfer volume, the observed time range and a few
sample error lines. Unrecognised lines are counted but not guessed at.

Usage:
    python log_analyzer.py access.log
    python log_analyzer.py app.log --top 15
    python log_analyzer.py access.log app.log --json
    type access.log | python log_analyzer.py -
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

ACCESS_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<request>[^"]*)" (?P<status>\d{3}) (?P<size>\S+)'
)
LEVEL_RE = re.compile(r"\b(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b")
ISO_TIME_RE = re.compile(
    r"(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
)
APACHE_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


@dataclass
class LogStats:
    """Aggregated counters for one log source."""

    source: str
    total_lines: int = 0
    recognised: int = 0
    unrecognised: int = 0
    levels: Counter[str] = field(default_factory=Counter)
    statuses: Counter[str] = field(default_factory=Counter)
    clients: Counter[str] = field(default_factory=Counter)
    paths: Counter[str] = field(default_factory=Counter)
    methods: Counter[str] = field(default_factory=Counter)
    bytes_sent: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    error_samples: list[str] = field(default_factory=list)
    unparsed_times: int = 0


def read_source(path: str) -> list[str]:
    """Read a log file (or stdin) as UTF-8, replacing bad byte sequences."""
    if path == "-":
        return sys.stdin.read().splitlines()
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def parse_timestamp(raw: str) -> datetime | None:
    """Parse an access-log or ISO-like timestamp, returning None on failure."""
    cleaned = raw.replace(",", ".").replace("T", " ")
    candidates = (
        (raw, APACHE_TIME_FORMAT),
        (cleaned, "%Y-%m-%d %H:%M:%S.%f"),
        (cleaned, "%Y-%m-%d %H:%M:%S"),
    )
    for value, fmt in candidates:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def note_time(stats: LogStats, raw_time: str) -> None:
    """Track the earliest and latest parsed timestamp."""
    moment = parse_timestamp(raw_time)
    if moment is None:
        stats.unparsed_times += 1
        return
    if stats.first_seen is None:
        stats.first_seen = moment
        stats.last_seen = moment
        return
    try:
        if moment < stats.first_seen:
            stats.first_seen = moment
        if moment > stats.last_seen:
            stats.last_seen = moment
    except TypeError:
        # Mixed naive and timezone-aware formats cannot be ordered reliably.
        stats.unparsed_times += 1


def analyse(lines: Sequence[str], source: str) -> LogStats:
    """Classify and aggregate *lines*."""
    stats = LogStats(source=source)
    for raw_line in lines:
        if not raw_line.strip():
            continue
        stats.total_lines += 1
        recognised = False

        access = ACCESS_RE.match(raw_line)
        if access:
            recognised = True
            stats.clients[access.group("ip")] += 1
            stats.statuses[access.group("status")] += 1
            request_parts = access.group("request").split()
            if request_parts:
                stats.methods[request_parts[0]] += 1
            if len(request_parts) >= 2:
                stats.paths[request_parts[1].split("?")[0]] += 1
            size = access.group("size")
            if size.isdigit():
                stats.bytes_sent += int(size)
            note_time(stats, access.group("time"))
            if access.group("status").startswith(("4", "5")) and len(stats.error_samples) < 5:
                stats.error_samples.append(raw_line.strip()[:160])

        level_match = LEVEL_RE.search(raw_line)
        if level_match:
            recognised = True
            level = level_match.group("level").upper()
            if level.startswith("WARN"):
                level = "WARNING"
            stats.levels[level] += 1
            time_match = ISO_TIME_RE.search(raw_line)
            if time_match:
                note_time(stats, time_match.group("time"))
            if level in {"ERROR", "CRITICAL", "FATAL"} and len(stats.error_samples) < 5:
                stats.error_samples.append(raw_line.strip()[:160])

        if recognised:
            stats.recognised += 1
        else:
            stats.unrecognised += 1
    return stats


def human_bytes(value: int) -> str:
    """Format a byte count using binary units."""
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def section(title: str) -> None:
    print()
    print(title)


def print_counter(counter: Counter[str], top: int, total: int, label: str) -> None:
    """Print a counter as aligned rows."""
    if not counter:
        print(f"  (no {label} data)")
        return
    shown = counter.most_common(top)
    width = max(len(key) for key, _ in shown)
    for key, count in shown:
        share = count / total * 100 if total else 0
        print(f"  {key:<{width}}  {count:>8}  {share:>6.1f}%")


def print_stats(stats: LogStats, top: int) -> None:
    """Print a human-readable report."""
    print(f"Log summary: {stats.source}")
    print(f"  Lines          {stats.total_lines}")
    print(f"  Recognised     {stats.recognised}")
    print(f"  Unrecognised   {stats.unrecognised}")
    if stats.total_lines == 0:
        print("  (file is empty)")
        return

    if stats.first_seen and stats.last_seen:
        print(f"  Time range     {stats.first_seen.isoformat()} .. {stats.last_seen.isoformat()}")
    elif stats.unparsed_times:
        print(f"  Time range     unavailable ({stats.unparsed_times} timestamp(s) unparsed)")

    if stats.levels:
        section("Levels")
        print_counter(stats.levels, top, sum(stats.levels.values()), "level")

    if stats.statuses:
        section("HTTP status codes")
        print_counter(stats.statuses, top, sum(stats.statuses.values()), "status")

    if stats.methods:
        section("HTTP methods")
        print_counter(stats.methods, top, sum(stats.methods.values()), "method")

    if stats.clients:
        section(f"Top {top} client IPs")
        print_counter(stats.clients, top, sum(stats.clients.values()), "client")

    if stats.paths:
        section(f"Top {top} request paths")
        print_counter(stats.paths, top, sum(stats.paths.values()), "path")

    if stats.bytes_sent:
        section("Transfer")
        print(f"  Response bytes {stats.bytes_sent} ({human_bytes(stats.bytes_sent)})")

    if stats.error_samples:
        section("Sample errors")
        for line in stats.error_samples:
            print(f"  {line}")


def to_dict(stats: LogStats, top: int) -> dict:
    """Convert the report to JSON-serialisable data."""
    return {
        "source": stats.source,
        "total_lines": stats.total_lines,
        "recognised": stats.recognised,
        "unrecognised": stats.unrecognised,
        "levels": dict(stats.levels.most_common(top)),
        "status_codes": dict(stats.statuses.most_common(top)),
        "methods": dict(stats.methods.most_common(top)),
        "top_clients": dict(stats.clients.most_common(top)),
        "top_paths": dict(stats.paths.most_common(top)),
        "bytes_sent": stats.bytes_sent,
        "first_seen": stats.first_seen.isoformat() if stats.first_seen else None,
        "last_seen": stats.last_seen.isoformat() if stats.last_seen else None,
        "error_samples": stats.error_samples,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarise web access and application logs.",
        epilog="Unrecognised lines are counted but never interpreted.",
    )
    parser.add_argument("paths", nargs="+", help="log files, or '-' for stdin")
    parser.add_argument("--top", type=int, default=10, metavar="N",
                        help="rows to show per section (default: 10)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of a text report")
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.paths.count("-") > 1:
        parser.error("stdin ('-') may only be given once")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    reports = [analyse(read_source(path), path) for path in args.paths]

    if not any(report.recognised for report in reports):
        print("error: no recognised log lines found", file=sys.stderr)
        return 1

    if args.as_json:
        payload = [to_dict(report, args.top) for report in reports]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for index, report in enumerate(reports):
        if index:
            print()
        print_stats(report, args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
