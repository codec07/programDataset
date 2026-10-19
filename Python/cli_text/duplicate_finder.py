#!/usr/bin/env python3
"""Find duplicate files using size grouping plus strong content hashes.

Files are first grouped by exact size, so only plausible candidates are
hashed. The default BLAKE2b digest makes accidental collisions negligible.
Reporting is read-only; deletion requires both --delete and --yes, and the
first path in each group (sorted alphabetically) is always kept.

Usage:
    python duplicate_finder.py .
    python duplicate_finder.py photos downloads --min-size 4096
    python duplicate_finder.py . --json
    python duplicate_finder.py . --delete --dry-run
    python duplicate_finder.py . --delete --yes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

CHUNK_SIZE = 1024 * 1024


def human_size(value: int) -> str:
    """Format bytes with binary units."""
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def collect_files(paths: Sequence[str], recursive: bool) -> list[Path]:
    """Expand paths into a sorted, de-duplicated list of regular files."""
    found: dict[Path, None] = {}
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            print(f"warning: skipping missing path: {path}", file=sys.stderr)
            continue
        if path.is_file():
            found[path.resolve()] = None
            continue
        if not path.is_dir():
            print(f"warning: skipping unsupported path: {path}", file=sys.stderr)
            continue
        pattern = "**/*" if recursive else "*"
        try:
            for candidate in path.glob(pattern):
                if candidate.is_file() and not candidate.is_symlink():
                    found[candidate.resolve()] = None
        except OSError as exc:
            print(f"warning: cannot scan {path}: {exc}", file=sys.stderr)
    return sorted(found, key=lambda item: str(item).casefold())


def hash_file(path: Path, algorithm: str) -> str | None:
    """Hash a file in chunks; return None when it cannot be read."""
    digest = hashlib.new(algorithm)
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_SIZE):
                digest.update(chunk)
    except OSError as exc:
        print(f"warning: cannot read {path}: {exc}", file=sys.stderr)
        return None
    return digest.hexdigest()


def find_duplicates(
    files: Sequence[Path], min_size: int, algorithm: str
) -> list[tuple[int, str, list[Path]]]:
    """Return (size, digest, paths) groups containing at least two files."""
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in files:
        try:
            size = path.stat().st_size
        except OSError as exc:
            print(f"warning: cannot stat {path}: {exc}", file=sys.stderr)
            continue
        if size >= min_size:
            by_size[size].append(path)

    by_digest: dict[tuple[int, str], list[Path]] = defaultdict(list)
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        for path in candidates:
            digest = hash_file(path, algorithm)
            if digest is not None:
                by_digest[(size, digest)].append(path)

    groups = [
        (size, digest, sorted(paths, key=lambda p: str(p).casefold()))
        for (size, digest), paths in by_digest.items()
        if len(paths) > 1
    ]
    groups.sort(key=lambda item: item[0] * (len(item[2]) - 1), reverse=True)
    return groups


def report_text(groups: Sequence[tuple[int, str, list[Path]]]) -> None:
    """Print a human-readable duplicate report."""
    if not groups:
        print("No duplicate files found.")
        return
    waste = sum(size * (len(paths) - 1) for size, _, paths in groups)
    print(f"Found {len(groups)} duplicate group(s).\n")
    for number, (size, digest, paths) in enumerate(groups, start=1):
        print(
            f"[{number}] {human_size(size)} each, {len(paths)} copies, "
            f"{human_size(size * (len(paths) - 1))} wasted"
        )
        print(f"    hash: {digest[:16]}...")
        for path in paths:
            print(f"    {path}")
        print()
    print(f"Total reclaimable space: {human_size(waste)}")


def delete_duplicates(
    groups: Sequence[tuple[int, str, list[Path]]], dry_run: bool
) -> tuple[int, int]:
    """Delete all but the first file in each group. Return (count, failures)."""
    deleted = 0
    failures = 0
    for _, _, paths in groups:
        keep, *extras = paths
        print(f"keeping: {keep}")
        for path in extras:
            if dry_run:
                print(f"  [dry-run] would delete: {path}")
                continue
            try:
                path.unlink()
                print(f"  deleted: {path}")
                deleted += 1
            except OSError as exc:
                print(f"  error: cannot delete {path}: {exc}", file=sys.stderr)
                failures += 1
    if dry_run:
        print("\nDry run only - nothing was deleted.")
    return deleted, failures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find duplicate files by size and content hash.",
        epilog="Deletion keeps the first path in each sorted group.",
    )
    parser.add_argument("paths", nargs="+", help="files or directories to scan")
    parser.add_argument("--min-size", type=int, default=0, metavar="BYTES",
                        help="ignore files smaller than this, e.g. 4096 (default: 0)")
    parser.add_argument("--algorithm", default="blake2b",
                        choices=sorted(hashlib.algorithms_guaranteed),
                        help="hash algorithm (default: blake2b)")
    parser.add_argument("--no-recursive", action="store_true",
                        help="scan only the top level of each directory")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of text")
    parser.add_argument("--delete", action="store_true",
                        help="delete duplicates, keeping one copy per group")
    parser.add_argument("--yes", action="store_true",
                        help="confirm deletion (required with --delete)")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --delete, show what would be removed")
    args = parser.parse_args(argv)

    if args.min_size < 0:
        parser.error("--min-size cannot be negative")
    if args.delete and not args.yes and not args.dry_run:
        parser.error("--delete requires --yes (or use --dry-run to preview)")
    if args.dry_run and not args.delete:
        parser.error("--dry-run only makes sense together with --delete")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    files = collect_files(args.paths, recursive=not args.no_recursive)
    if not files:
        print("error: no files to scan", file=sys.stderr)
        return 1

    groups = find_duplicates(files, args.min_size, args.algorithm)
    print(f"Scanned {len(files)} file(s).", file=sys.stderr)

    if args.as_json:
        payload = [
            {
                "size": size,
                "hash": digest,
                "paths": [str(path) for path in paths],
                "wasted_bytes": size * (len(paths) - 1),
            }
            for size, digest, paths in groups
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        report_text(groups)

    if args.delete and groups:
        print()
        deleted, failures = delete_duplicates(groups, args.dry_run)
        if not args.dry_run:
            print(f"Deleted {deleted} file(s), {failures} failure(s).")
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
