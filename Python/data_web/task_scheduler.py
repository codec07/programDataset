"""A small JSON-configured job scheduler with dry-run and one-shot modes.

Config format (jobs.json):
    {
      "jobs": [
        {"name": "tick", "command": ["python", "job.py", "--fast"],
         "interval": 5, "timeout": 30},
        {"name": "quote", "command": "python -c \\"print('hi')\\"",
         "interval": 60, "timeout": 30}
      ]
    }

Commands may be a list (recommended: no shell parsing, Windows-safe) or a
string split with shlex.  Jobs run without a shell.  Each run appends a line
to the log file.  ``--once`` executes every job a single time and exits,
which makes the tool easy to test; ``--duration`` bounds the loop.

Usage:
    python task_scheduler.py --config jobs.json --once
    python task_scheduler.py --config jobs.json --duration 60
    python task_scheduler.py --config jobs.json --list
    python task_scheduler.py --config jobs.json --once --dry-run
    python task_scheduler.py --demo
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Job:
    name: str
    command: str
    interval: float
    timeout: float
    argv: list[str]
    last_run: float = 0.0

    @property
    def due(self) -> bool:
        return time.monotonic() - self.last_run >= self.interval


def load_jobs(path: Path) -> list[Job]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read config {path}: {exc}") from exc
    raw_jobs = data.get("jobs") if isinstance(data, dict) else data
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("config must contain a non-empty 'jobs' list")

    jobs: list[Job] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_jobs):
        if not isinstance(item, dict):
            raise ValueError(f"job #{index} must be an object")
        name = str(item.get("name") or f"job{index}")
        raw_command = item.get("command")
        if isinstance(raw_command, list) and raw_command and all(
                isinstance(part, str) for part in raw_command):
            argv = list(raw_command)
            command = " ".join(argv)
        elif isinstance(raw_command, str) and raw_command.strip():
            command = raw_command
            try:
                argv = shlex.split(command)
            except ValueError as exc:
                raise ValueError(f"job {name!r}: cannot parse command: {exc}") from exc
        else:
            raise ValueError(f"job {name!r}: command must be a string or list")
        if not argv:
            raise ValueError(f"job {name!r}: empty command")
        if name in seen:
            raise ValueError(f"duplicate job name: {name}")
        seen.add(name)
        try:
            interval = float(item.get("interval", 60))
            timeout = float(item.get("timeout", 300))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"job {name!r}: interval/timeout must be numbers") from exc
        if interval <= 0 or timeout <= 0:
            raise ValueError(f"job {name!r}: interval and timeout must be positive")
        jobs.append(Job(name, command, interval, timeout, argv))
    return jobs


def log_line(log_path: Path | None, text: str) -> None:
    print(text)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")


def run_job(job: Job, log_path: Path | None, dry_run: bool) -> bool:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if dry_run:
        log_line(log_path, f"{stamp} [dry-run] {job.name}: {job.command}")
        return True
    started = time.monotonic()
    try:
        result = subprocess.run(
            job.argv, capture_output=True, text=True, timeout=job.timeout,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        log_line(log_path, f"{stamp} [error] {job.name}: command not found: {job.argv[0]}")
        return False
    except subprocess.TimeoutExpired:
        log_line(log_path, f"{stamp} [timeout] {job.name} after {job.timeout:g}s")
        return False
    except OSError as exc:
        log_line(log_path, f"{stamp} [error] {job.name}: {exc}")
        return False

    elapsed = time.monotonic() - started
    status = "ok" if result.returncode == 0 else f"exit {result.returncode}"
    log_line(log_path, f"{stamp} [{status}] {job.name} ({elapsed:.2f}s)")
    for stream, label in ((result.stdout, "out"), (result.stderr, "err")):
        for line in (stream or "").rstrip().splitlines()[:5]:
            log_line(log_path, f"    {label}: {line}")
    return result.returncode == 0


def run_schedule(jobs: list[Job], log_path: Path | None, once: bool,
                 duration: float, dry_run: bool, poll: float = 0.5) -> int:
    failures = 0
    if once:
        for job in jobs:
            failures += 0 if run_job(job, log_path, dry_run) else 1
        return failures

    deadline = time.monotonic() + duration
    log_line(log_path, f"scheduler started: {len(jobs)} job(s), "
                        f"duration {duration:g}s")
    while time.monotonic() < deadline:
        for job in jobs:
            if job.due:
                failures += 0 if run_job(job, log_path, dry_run) else 1
                job.last_run = time.monotonic()
        time.sleep(min(poll, max(0.0, deadline - time.monotonic())))
    log_line(log_path, f"scheduler finished: {failures} failure(s)")
    return failures


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config = root / "jobs.json"
        script = root / "work.py"
        script.write_text(
            "import sys\n"
            "print('processed', sys.argv[1] if len(sys.argv) > 1 else 'nothing')\n",
            encoding="utf-8",
        )
        config.write_text(json.dumps({"jobs": [
            {"name": "alpha", "command": [sys.executable, str(script), "alpha"],
             "interval": 5, "timeout": 20},
            {"name": "beta", "command": [sys.executable, str(script), "beta"],
             "interval": 5, "timeout": 20},
        ]}, indent=2), encoding="utf-8")
        jobs = load_jobs(config)
        print("loaded:", ", ".join(j.name for j in jobs))
        print()
        failures = run_schedule(jobs, root / "scheduler.log", once=True,
                                duration=0, dry_run=False)
        print()
        print("log file head:")
        print("\n".join((root / "scheduler.log").read_text(encoding="utf-8")
                        .splitlines()[:4]))
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run interval jobs from a JSON config.")
    p.add_argument("--config", type=Path, default=Path("jobs.json"))
    p.add_argument("--log", type=Path, help="append output to this file")
    p.add_argument("--once", action="store_true", help="run every job once and exit")
    p.add_argument("--duration", type=float, default=0.0,
                   help="seconds to keep scheduling (not used with --once)")
    p.add_argument("--dry-run", action="store_true", help="print commands only")
    p.add_argument("--list", action="store_true", help="list configured jobs")
    p.add_argument("--demo", action="store_true", help="offline demonstration")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    try:
        jobs = load_jobs(args.config)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list:
        for job in jobs:
            print(f"{job.name:<20} every {job.interval:>6g}s  timeout {job.timeout:>6g}s"
                  f"  {job.command}")
        return 0
    if not args.once and args.duration <= 0:
        print("error: use --once or a positive --duration", file=sys.stderr)
        return 2

    try:
        failures = run_schedule(jobs, args.log, args.once, args.duration,
                                args.dry_run)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
