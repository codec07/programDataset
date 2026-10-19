#!/usr/bin/env python3
"""Display a directory tree with optional sizes, filters and depth limits.

The tree is read-only. Only the requested directory is scanned; symlinks
are shown but never followed, and unreadable directories are reported
instead of aborting the whole walk. File sizes are displayed with --sizes
and the footer totals only what was actually visited.

Usage:
    python directory_tree.py
    python directory_tree.py src --depth 2
    python directory_tree.py . --dirs-only
    python directory_tree.py project --sizes --exclude "__pycache__"
    python directory_tree.py . --exclude "*.pyc" --exclude ".git" --exclude-hidden
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class TreeStats:
    """Counters collected while rendering the tree."""

    directories: int = 0
    files: int = 0
    symlinks: int = 0
    unreadable: int = 0
    total_bytes: int = 0


def human_size(value: int) -> str:
    """Format bytes using binary units."""
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def is_excluded(name: str, patterns: Sequence[str], hidden: bool) -> bool:
    """Return True when a name should be skipped."""
    if hidden and name.startswith("."):
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def list_entries(path: Path, args: argparse.Namespace) -> list[Path] | None:
    """List a directory, returning None when it cannot be read."""
    try:
        entries = [
            entry for entry in path.iterdir()
            if not is_excluded(entry.name, args.exclude, args.exclude_hidden)
        ]
    except (PermissionError, OSError):
        return None
    return sorted(
        entries,
        key=lambda entry: (entry.is_symlink() or not entry.is_dir(), entry.name.casefold()),
    )


def render_directory(
    directory: Path,
    prefix: str,
    depth: int,
    args: argparse.Namespace,
    stats: TreeStats,
    lines: list[str],
) -> None:
    """Append the children of *directory* to *lines* recursively."""
    entries = list_entries(directory, args)
    if entries is None:
        lines.append(f"{prefix}`-- [unreadable]")
        stats.unreadable += 1
        return

    for position, entry in enumerate(entries):
        last = position == len(entries) - 1
        connector = "`-- " if last else "|-- "
        child_prefix = prefix + ("    " if last else "|   ")

        if entry.is_symlink():
            stats.symlinks += 1
            try:
                target = entry.resolve()
                lines.append(f"{prefix}{connector}{entry.name} -> {target} (symlink)")
            except OSError:
                lines.append(f"{prefix}{connector}{entry.name} (symlink)")
            continue

        if entry.is_dir():
            stats.directories += 1
            lines.append(f"{prefix}{connector}{entry.name}/")
            if depth < args.depth:
                render_directory(entry, child_prefix, depth + 1, args, stats, lines)
            continue

        if args.dirs_only:
            continue
        stats.files += 1
        suffix = ""
        if args.sizes:
            try:
                size = entry.stat().st_size
                stats.total_bytes += size
                suffix = f"  [{human_size(size)}]"
            except OSError:
                suffix = "  [?]"
                stats.unreadable += 1
        lines.append(f"{prefix}{connector}{entry.name}{suffix}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a directory tree.",
        epilog="Symlinks are displayed but never followed.",
    )
    parser.add_argument("root", nargs="?", default=".", help="directory to display (default: .)")
    parser.add_argument("--depth", type=int, default=3, metavar="N",
                        help="maximum recursion depth (default: 3, 0 = root only)")
    parser.add_argument("--dirs-only", action="store_true", help="hide files")
    parser.add_argument("--sizes", action="store_true", help="show file sizes")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip names matching this glob (repeatable)")
    parser.add_argument("--exclude-hidden", action="store_true",
                        help="skip dot files and dot directories")
    args = parser.parse_args(argv)
    if args.depth < 0:
        parser.error("--depth cannot be negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    stats = TreeStats()
    lines = [f"{root.resolve()}/"]
    render_directory(root, "", 0, args, stats, lines)
    print("\n".join(lines))

    summary = f"{stats.directories} director{'y' if stats.directories == 1 else 'ies'}, "
    summary += f"{stats.files} file(s)"
    if args.sizes:
        summary += f", {human_size(stats.total_bytes)} visited"
    if stats.symlinks:
        summary += f", {stats.symlinks} symlink(s)"
    if stats.unreadable:
        summary += f", {stats.unreadable} unreadable"
    print(f"\n{summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
