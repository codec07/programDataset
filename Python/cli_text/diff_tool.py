#!/usr/bin/env python3
"""Compare files or directory trees and print unified diffs.

Two files are compared directly; two directories are compared recursively
by relative path, including files that exist on only one side. Binary
files are detected and reported without dumping bytes. Exit status
follows the classic diff convention: 0 = identical, 1 = differences,
2 = an error such as a missing path.

Usage:
    python diff_tool.py old.txt new.txt
    python diff_tool.py before/ after/ --stat
    python diff_tool.py a.py b.py --context 5
    python diff_tool.py a.txt b.txt --ignore-case --ignore-whitespace
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class FileResult:
    """Comparison outcome for one file pair."""

    relative: str
    added: int = 0
    removed: int = 0
    identical: bool = True
    note: str = ""


def read_bytes(path: Path) -> bytes:
    """Read a file, converting OS errors into a friendly exit."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def decode_text(data: bytes) -> str | None:
    """Decode bytes as UTF-8, returning None when they look binary."""
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def normalise(line: str, ignore_case: bool, ignore_whitespace: bool) -> str:
    """Normalise a line for comparison according to the flags."""
    if ignore_whitespace:
        line = WHITESPACE_RE.sub(" ", line).strip()
    if ignore_case:
        line = line.casefold()
    return line


def compare_text(
    left_text: str,
    right_text: str,
    left_label: str,
    right_label: str,
    *,
    context: int,
    ignore_case: bool,
    ignore_whitespace: bool,
) -> tuple[list[str], int, int]:
    """Return unified diff lines plus added and removed counts."""
    left = left_text.splitlines()
    right = right_text.splitlines()
    left_keys = [normalise(line, ignore_case, ignore_whitespace) for line in left]
    right_keys = [normalise(line, ignore_case, ignore_whitespace) for line in right]

    if left_keys == right_keys:
        return [], 0, 0

    diff = list(difflib.unified_diff(
        left_keys,
        right_keys,
        fromfile=left_label,
        tofile=right_label,
        lineterm="",
        n=context,
    ))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return diff, added, removed


def compare_file(
    left: Path,
    right: Path,
    label: str,
    args: argparse.Namespace,
) -> FileResult:
    """Compare two regular files."""
    result = FileResult(relative=label)
    left_data = read_bytes(left)
    right_data = read_bytes(right)
    if left_data == right_data:
        return result

    left_text = decode_text(left_data)
    right_text = decode_text(right_data)
    if left_text is None or right_text is None:
        result.identical = False
        result.note = "binary files differ"
        return result

    diff, added, removed = compare_text(
        left_text, right_text, str(left), str(right),
        context=args.context,
        ignore_case=args.ignore_case,
        ignore_whitespace=args.ignore_whitespace,
    )
    result.added = added
    result.removed = removed
    result.identical = not diff
    if diff:
        print("\n".join(diff))
        print()
    elif not args.quiet:
        print(f"{label}: no differences after normalisation")
    return result


def collect_tree(root: Path, excludes: Sequence[str]) -> dict[str, Path]:
    """Map relative POSIX paths to files under *root*."""
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*"), key=lambda p: str(p).casefold()):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(relative.match(pattern) for pattern in excludes):
            continue
        files[relative.as_posix()] = path
    return files


def compare_directories(left: Path, right: Path, args: argparse.Namespace) -> list[FileResult]:
    """Compare two directory trees by relative path."""
    left_files = collect_tree(left, args.exclude)
    right_files = collect_tree(right, args.exclude)
    results: list[FileResult] = []
    all_names = sorted(set(left_files) | set(right_files), key=str.casefold)

    for name in all_names:
        left_file = left_files.get(name)
        right_file = right_files.get(name)
        if left_file is None:
            print(f"Only in {right}: {name}")
            results.append(FileResult(name, added=1, identical=False, note="only right"))
        elif right_file is None:
            print(f"Only in {left}: {name}")
            results.append(FileResult(name, removed=1, identical=False, note="only left"))
        else:
            result = compare_file(left_file, right_file, name, args)
            results.append(result)
    return results


def print_stat(results: Sequence[FileResult]) -> None:
    """Print a per-file change summary."""
    changed = [item for item in results if not item.identical]
    print(f"\nSummary: {len(results)} file(s) compared, {len(changed)} changed.")
    for item in changed:
        detail = item.note or f"+{item.added} -{item.removed}"
        print(f"  {item.relative}: {detail}")
    print(f"  total lines: +{sum(i.added for i in results)} -{sum(i.removed for i in results)}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diff two files or directory trees.",
        epilog="Exit codes: 0 identical, 1 differences, 2 error.",
    )
    parser.add_argument("left", help="original file or directory")
    parser.add_argument("right", help="new file or directory")
    parser.add_argument("--context", type=int, default=3, metavar="N",
                        help="lines of context around changes (default: 3)")
    parser.add_argument("--ignore-case", action="store_true",
                        help="compare case-insensitively")
    parser.add_argument("--ignore-whitespace", action="store_true",
                        help="collapse whitespace before comparing")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip matching relative paths in directory mode")
    parser.add_argument("--stat", action="store_true",
                        help="print a change summary")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the note about equal normalised files")
    args = parser.parse_args(argv)
    if args.context < 0:
        parser.error("--context cannot be negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    left = Path(args.left)
    right = Path(args.right)

    for path in (left, right):
        if not path.exists():
            print(f"error: path not found: {path}", file=sys.stderr)
            return 2

    left_is_dir = left.is_dir()
    right_is_dir = right.is_dir()
    if left_is_dir != right_is_dir:
        print("error: cannot compare a file with a directory", file=sys.stderr)
        return 2

    if left_is_dir:
        results = compare_directories(left, right, args)
    else:
        results = [compare_file(left, right, left.name, args)]

    if args.stat:
        print_stat(results)

    identical = all(item.identical for item in results)
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
