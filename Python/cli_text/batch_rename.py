#!/usr/bin/env python3
"""Batch-rename files with regex, prefix/suffix and numbering rules.

The default is a dry run: the planned renames are printed but no file is
touched. Pass --apply to execute the plan. A rename plan is rejected as a
whole when two files would receive the same name or when a target already
exists, so existing data is never overwritten.

Rename order: regex substitution on the stem, then prefix/suffix, then an
optional sequential number.

Usage:
    python batch_rename.py . --pattern "IMG_(\\d+)" --replace "photo_\\1"
    python batch_rename.py photos --prefix "2026-" --apply
    python batch_rename.py . --filter "*.txt" --suffix "_backup" --apply
    python batch_rename.py . --pattern "\\s+" --replace "_" --number --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Rename:
    """One planned rename operation."""

    source: Path
    target: Path


def compile_pattern(pattern: str | None) -> re.Pattern[str] | None:
    """Compile the optional regex, reporting a friendly error."""
    if pattern is None:
        return None
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise SystemExit(f"error: invalid regular expression: {exc}")


def build_target_name(
    path: Path,
    *,
    pattern: re.Pattern[str] | None,
    replacement: str,
    prefix: str,
    suffix: str,
    number: int | None,
    number_width: int,
    number_sep: str,
    include_extension: bool,
) -> str:
    """Compute the new file name (without a directory)."""
    if include_extension:
        stem, extension = path.name, ""
    else:
        stem, extension = path.stem, path.suffix

    if pattern is not None:
        try:
            stem = pattern.sub(replacement, stem)
        except re.error as exc:
            raise SystemExit(f"error: replacement failed: {exc}")

    stem = f"{prefix}{stem}{suffix}"
    if number is not None:
        stem = f"{stem}{number_sep}{number:0{number_width}d}"
    target = f"{stem}{extension}"
    if not stem.strip():
        raise ValueError(f"rules produced an empty name for {path.name}")
    return target


def collect_files(directory: Path, glob: str, extensions: set[str]) -> list[Path]:
    """Return matching top-level regular files in sorted order."""
    if not directory.is_dir():
        raise SystemExit(f"error: not a directory: {directory}")
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name.casefold())
    except OSError as exc:
        raise SystemExit(f"error: cannot list {directory}: {exc}")
    files: list[Path] = []
    for entry in entries:
        if not entry.is_file() or entry.is_symlink():
            continue
        if not entry.match(glob):
            continue
        if extensions and entry.suffix.lower() not in extensions:
            continue
        files.append(entry)
    return files


def build_plan(files: Sequence[Path], args: argparse.Namespace,
               pattern: re.Pattern[str] | None) -> list[Rename]:
    """Create the rename plan without touching the filesystem."""
    plan: list[Rename] = []
    for index, source in enumerate(files):
        number = args.number_start + index * args.number_step if args.number else None
        try:
            name = build_target_name(
                source,
                pattern=pattern,
                replacement=args.replace,
                prefix=args.prefix,
                suffix=args.suffix,
                number=number,
                number_width=args.number_width,
                number_sep=args.number_sep,
                include_extension=args.include_extension,
            )
        except ValueError as exc:
            raise SystemExit(f"error: {exc}")
        plan.append(Rename(source, source.with_name(name)))
    return plan


def validate_plan(plan: Sequence[Rename]) -> list[str]:
    """Return a list of problems that make the plan unsafe."""
    problems: list[str] = []
    targets: dict[str, Rename] = {}

    for operation in plan:
        key = str(operation.target).casefold()
        if key in targets:
            problems.append(
                f"duplicate target: {operation.target.name} "
                f"(from {targets[key].source.name} and {operation.source.name})"
            )
        else:
            targets[key] = operation
        if operation.target.exists() and operation.source != operation.target:
            problems.append(f"target already exists: {operation.target.name}")
        if operation.source == operation.target:
            continue
        if not operation.target.parent.is_dir():
            problems.append(f"target directory missing: {operation.target.parent}")
    return problems


def execute(plan: Sequence[Rename], apply: bool) -> int:
    """Print the plan and optionally perform it."""
    changes = [operation for operation in plan if operation.source != operation.target]
    if not changes:
        print("Nothing to rename.")
        return 0

    width = max(len(operation.source.name) for operation in changes)
    for operation in changes:
        print(f"  {operation.source.name:<{width}}  ->  {operation.target.name}")
    print()
    if not apply:
        print(f"Dry run: {len(changes)} rename(s) planned. Re-run with --apply to execute.")
        return 0

    failures = 0
    for operation in changes:
        try:
            operation.source.rename(operation.target)
        except OSError as exc:
            print(f"error: cannot rename {operation.source.name}: {exc}", file=sys.stderr)
            failures += 1
    succeeded = len(changes) - failures
    print(f"Renamed {succeeded} file(s), {failures} failure(s).")
    return 1 if failures else 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename files in bulk using patterns, affixes and numbers.",
        epilog="Without --apply nothing is changed.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="directory to process (default: .)")
    parser.add_argument("--pattern", help="regular expression applied to the file stem")
    parser.add_argument("--replace", default="", help="replacement for --pattern (supports \\1 groups)")
    parser.add_argument("--prefix", default="", help="text added before the stem")
    parser.add_argument("--suffix", default="", help="text added after the stem, before the extension")
    parser.add_argument("--filter", default="*", metavar="GLOB",
                        help="only rename files matching this glob (default: *)")
    parser.add_argument("--extensions", default="", metavar="LIST",
                        help="comma-separated extensions to include, e.g. .txt,.md")
    parser.add_argument("--include-extension", action="store_true",
                        help="apply rules to the full file name")
    parser.add_argument("--number", action="store_true", help="append a sequential number")
    parser.add_argument("--number-start", type=int, default=1, metavar="N")
    parser.add_argument("--number-step", type=int, default=1, metavar="N")
    parser.add_argument("--number-width", type=int, default=3, metavar="N")
    parser.add_argument("--number-sep", default="_", metavar="TEXT")
    parser.add_argument("--apply", action="store_true", help="perform the renames")
    parser.add_argument("--dry-run", action="store_true", help="explicitly request the default preview")
    args = parser.parse_args(argv)

    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    if args.pattern is None and args.replace:
        parser.error("--replace requires --pattern")
    if not (args.prefix or args.suffix or args.pattern or args.number):
        parser.error("nothing to do: provide --pattern, --prefix, --suffix and/or --number")
    if not 1 <= args.number_width <= 10:
        parser.error("--number-width must be between 1 and 10")
    if args.number_step == 0:
        parser.error("--number-step cannot be zero")
    if not 1 <= len(args.number_sep) <= 5:
        parser.error("--number-sep must be between 1 and 5 characters")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pattern = compile_pattern(args.pattern)
    extensions = {
        item if item.startswith(".") else f".{item}"
        for item in (part.strip().lower() for part in args.extensions.split(","))
        if item
    }
    directory = Path(args.directory)
    files = collect_files(directory, args.filter, extensions)
    if not files:
        print("No matching files.")
        return 0

    plan = build_plan(files, args, pattern)
    problems = validate_plan(plan)
    if problems:
        print("error: the rename plan is unsafe and was not applied:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return execute(plan, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
