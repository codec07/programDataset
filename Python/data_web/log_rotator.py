"""Rotate log files by size, gzip the archives and prune old copies.

Commands:
    rotate   move an oversized log to ``.1`` (shifting ``.1`` -> ``.2`` ...)
    list     show rotated archives in a directory
    prune    delete archives beyond a keep count or older than N days

Mutating commands support ``--dry-run``; ``--force`` allows rotating files
that are smaller than the threshold.

Usage:
    python log_rotator.py rotate logs/app.log --max-bytes 1MB --keep 5 --gzip
    python log_rotator.py rotate --dir logs --pattern "*.log" --dry-run
    python log_rotator.py list logs
    python log_rotator.py prune logs --keep 3 --max-age 30 --dry-run
    python log_rotator.py --demo
"""

from __future__ import annotations

import argparse
import gzip
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SIZE_UNITS = {"b": 1, "k": 1024, "kb": 1024, "m": 1024 ** 2, "mb": 1024 ** 2,
              "g": 1024 ** 3, "gb": 1024 ** 3}
ARCHIVE_RE = re.compile(r"^(?P<base>.+)\.(?P<index>\d+)(?P<gz>\.gz)?$")


def parse_size(text: str) -> int:
    cleaned = text.strip().lower().rstrip("b")
    for suffix, factor in sorted(SIZE_UNITS.items(), key=lambda kv: -len(kv[0])):
        if suffix in ("b",) or not cleaned.endswith(suffix):
            continue
        head = cleaned[: -len(suffix)]
        if head.replace(".", "", 1).isdigit():
            return int(float(head) * factor)
    try:
        return int(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid size: {text!r}") from exc


def human_bytes(value: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(value) < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB"


def archive_name(path: Path, index: int) -> Path:
    return path.with_name(f"{path.name}.{index}")


def find_archives(path: Path) -> list[tuple[int, Path]]:
    """Return (index, path) pairs for every archive of a log file."""
    found: list[tuple[int, Path]] = []
    for candidate in path.parent.glob(f"{path.name}.*"):
        match = ARCHIVE_RE.match(candidate.name)
        if match and match.group("base") == path.name:
            found.append((int(match.group("index")), candidate))
    return sorted(found, reverse=True)


def compress(path: Path) -> Path:
    target = path.with_name(path.name + ".gz")
    with path.open("rb") as src, gzip.open(target, "wb") as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()
    return target


def rotate_file(path: Path, max_bytes: int, keep: int, use_gzip: bool,
                dry_run: bool, force: bool) -> tuple[bool, str]:
    exists = path.exists()
    size = path.stat().st_size if exists and path.is_file() else 0
    if not exists:
        return False, f"skip (missing): {path}"
    if not path.is_file():
        return False, f"skip (not a file): {path}"
    if size < max_bytes and not force:
        return False, f"skip ({human_bytes(size)} < threshold): {path}"

    archives = find_archives(path)
    if dry_run:
        moves = [f"{old.name} -> {archive_name(path, idx + 1).name}"
                 for idx, old in archives if idx < keep]
        return True, (f"would rotate {path.name} ({human_bytes(size)}) "
                      f"moves=[{', '.join(moves) or 'none'}]")

    for index, archive in archives:
        if index >= keep:
            archive.unlink()
            continue
        suffix = ".gz" if archive.name.endswith(".gz") else ""
        archive.replace(path.with_name(f"{path.name}.{index + 1}{suffix}"))

    first = archive_name(path, 1)
    path.replace(first)
    if use_gzip:
        first = compress(first)
    return True, f"rotated {path.name} ({human_bytes(size)}) -> {first.name}"


def rotate(args: argparse.Namespace) -> int:
    targets: list[Path] = []
    if args.path:
        targets = [args.path]
    elif args.dir:
        if not args.dir.is_dir():
            print(f"error: not a directory: {args.dir}", file=sys.stderr)
            return 2
        targets = sorted(p for p in args.dir.glob(args.pattern) if p.is_file())
        if not targets:
            print(f"no files matching {args.pattern} in {args.dir}")
            return 0
    else:
        print("error: provide a log path or --dir", file=sys.stderr)
        return 2

    changed = 0
    for target in targets:
        try:
            rotated, message = rotate_file(target, args.max_bytes, max(1, args.keep),
                                           args.gzip, args.dry_run, args.force)
        except OSError as exc:
            print(f"error: {target}: {exc}", file=sys.stderr)
            return 1
        print(message)
        changed += 1 if rotated else 0
    print(f"{changed} of {len(targets)} file(s) "
          f"{'would be rotated' if args.dry_run else 'rotated'}")
    return 0


def list_archives(directory: Path) -> int:
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 2
    rows = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or not ARCHIVE_RE.match(path.name):
            continue
        stat = path.stat()
        rows.append((path.name, stat.st_size, stat.st_mtime))
    if not rows:
        print("no rotated archives found")
        return 0
    print(f"{'archive':<40} {'size':>10}  {'modified':<19}")
    for name, size, mtime in rows:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        print(f"{name:<40} {human_bytes(size):>10}  {stamp:<19}")
    return 0


def prune(directory: Path, keep: int, max_age_days: float, dry_run: bool) -> int:
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 2
    groups: dict[str, list[tuple[int, Path]]] = {}
    for path in sorted(directory.iterdir()):
        match = ARCHIVE_RE.match(path.name)
        if match and path.is_file():
            groups.setdefault(match.group("base"), []).append(
                (int(match.group("index")), path))

    cutoff = time.time() - max_age_days * 86400 if max_age_days > 0 else None
    removed = 0
    for base, entries in groups.items():
        for index, path in sorted(entries, reverse=True):
            too_old = cutoff is not None and path.stat().st_mtime < cutoff
            beyond_keep = keep > 0 and index > keep
            if not (too_old or beyond_keep):
                continue
            reason = "age" if too_old else f"index>{keep}"
            if dry_run:
                print(f"would delete {path.name} ({reason})")
            else:
                path.unlink()
                print(f"deleted {path.name} ({reason})")
            removed += 1
    print(f"{removed} archive(s) {'would be removed' if dry_run else 'removed'}")
    return 0


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        logs = root / "logs"
        logs.mkdir()
        log = logs / "app.log"
        for round_no in range(4):
            log.write_text(f"round {round_no}\n" * 400, encoding="utf-8")
            rotate_file(log, max_bytes=1024, keep=3, use_gzip=False,
                        dry_run=False, force=True)
            time.sleep(0.01)
        print()
        list_archives(logs)
        print()
        log.write_text("fresh\n" * 50, encoding="utf-8")
        rotate_file(log, max_bytes=64, keep=2, use_gzip=True, dry_run=False,
                    force=False)
        print()
        list_archives(logs)
        print()
        prune(logs, keep=2, max_age_days=0, dry_run=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS,
                        help="show what would change")

    p = argparse.ArgumentParser(description="Size-based log rotator.", parents=[common])
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("rotate", help="rotate one file or a directory glob",
                       parents=[common])
    r.add_argument("path", nargs="?", type=Path)
    r.add_argument("--dir", type=Path)
    r.add_argument("--pattern", default="*.log")
    r.add_argument("--max-bytes", type=parse_size, default=1024 * 1024)
    r.add_argument("--keep", type=int, default=5)
    r.add_argument("--gzip", action="store_true", help="compress the newest archive")
    r.add_argument("--force", action="store_true", help="rotate below the threshold")

    ls = sub.add_parser("list", help="list archives", parents=[common])
    ls.add_argument("directory", type=Path)

    pr = sub.add_parser("prune", help="delete old archives", parents=[common])
    pr.add_argument("directory", type=Path)
    pr.add_argument("--keep", type=int, default=5)
    pr.add_argument("--max-age", type=float, default=0.0, help="days")

    args = p.parse_args(argv, argparse.Namespace(dry_run=False))
    try:
        if args.command == "rotate":
            return rotate(args)
        if args.command == "list":
            return list_archives(args.directory)
        if args.command == "prune":
            return prune(args.directory, max(0, args.keep), args.max_age, args.dry_run)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        raise SystemExit(demo())
    raise SystemExit(main())
