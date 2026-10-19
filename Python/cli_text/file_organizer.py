#!/usr/bin/env python3
"""Sort files in a directory into category folders by extension.

By default the tool only previews the moves. Pass --apply to perform them.
Name collisions are resolved with a numeric suffix, so no existing file is
ever overwritten. Hidden and already-categorised files stay untouched
because only files directly inside the target directory are considered.

Usage:
    python file_organizer.py Downloads
    python file_organizer.py Downloads --apply
    python file_organizer.py . --apply --unknown-folder Misc
    python file_organizer.py . --exclude "*.tmp" --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence

CATEGORIES: dict[str, set[str]] = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
        ".tif", ".tiff", ".ico", ".heic", ".avif",
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md",
        ".tex", ".epub", ".pages",
    },
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
    "Presentations": {".ppt", ".pptx", ".odp", ".key"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Code": {
        ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml",
        ".yaml", ".sh", ".bat", ".ps1", ".c", ".cpp", ".h", ".java",
        ".rs", ".go", ".rb", ".php", ".sql", ".ini", ".toml", ".ipynb",
    },
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
}

EXTENSION_MAP: dict[str, str] = {
    extension: category
    for category, extensions in CATEGORIES.items()
    for extension in extensions
}


def category_for(path: Path, unknown_folder: str) -> str:
    """Return the destination folder name for one file."""
    return EXTENSION_MAP.get(path.suffix.lower(), unknown_folder)


def unique_destination(target: Path) -> Path:
    """Return *target* or a numbered variant that does not exist yet."""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for number in range(1, 1000):
        candidate = target.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"could not find a free name for {target}")


def collect_files(directory: Path, exclude: Sequence[str]) -> list[Path]:
    """Return top-level regular files that are not hidden or excluded."""
    files: list[Path] = []
    for entry in sorted(directory.iterdir(), key=lambda p: p.name.casefold()):
        if not entry.is_file() or entry.is_symlink():
            continue
        if entry.name.startswith("."):
            continue
        if any(entry.match(pattern) for pattern in exclude):
            print(f"  skipped (excluded): {entry.name}")
            continue
        files.append(entry)
    return files


def organize(
    directory: Path,
    files: Sequence[Path],
    *,
    dry_run: bool,
    unknown_folder: str,
) -> int:
    """Move files into category folders. Return the number of failures."""
    counts: Counter[str] = Counter()
    failures = 0

    for source in files:
        category = category_for(source, unknown_folder)
        destination_dir = directory / category
        try:
            destination = unique_destination(destination_dir / source.name)
        except FileExistsError as exc:
            print(f"error: {exc}", file=sys.stderr)
            failures += 1
            continue

        action = "would move" if dry_run else "moving"
        print(f"  {action}: {source.name} -> {category}/{destination.name}")
        counts[category] += 1

        if dry_run:
            continue
        try:
            destination_dir.mkdir(exist_ok=True)
            shutil.move(str(source), str(destination))
        except OSError as exc:
            print(f"error: cannot move {source.name}: {exc}", file=sys.stderr)
            failures += 1
            counts[category] -= 1

    print()
    if not counts:
        print("Nothing to organize.")
        return failures
    for category, count in sorted(counts.items()):
        print(f"  {category:<15} {count} file(s)")
    total = sum(counts.values())
    prefix = "Would move" if dry_run else "Moved"
    print(f"{prefix} {total} file(s).")
    if dry_run and total:
        print("Preview only - re-run with --apply to perform the moves.")
    return failures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sort files into category folders by extension.",
        epilog="Without --apply this is a read-only preview.",
    )
    parser.add_argument("directory", nargs="?", default=".",
                        help="directory to organize (default: current directory)")
    parser.add_argument("--apply", action="store_true",
                        help="actually move files (default is a dry run)")
    parser.add_argument("--dry-run", action="store_true",
                        help="explicitly request the default preview mode")
    parser.add_argument("--unknown-folder", default="Other", metavar="NAME",
                        help="folder for unrecognised extensions (default: Other)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="skip file names matching this glob (repeatable)")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    if not args.unknown_folder.strip() or any(ch in args.unknown_folder for ch in "/\\"):
        parser.error("--unknown-folder must be a simple folder name")
    if args.unknown_folder.strip() in {".", ".."}:
        parser.error("--unknown-folder cannot be '.' or '..'")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    directory = Path(args.directory)
    if not directory.exists():
        print(f"error: directory not found: {directory}", file=sys.stderr)
        return 1
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 1

    dry_run = not args.apply
    print(f"Organizing: {directory.resolve()}")
    print(f"Mode: {'dry run (no changes)' if dry_run else 'apply'}")
    print()

    try:
        files = collect_files(directory, args.exclude)
    except OSError as exc:
        print(f"error: cannot list {directory}: {exc}", file=sys.stderr)
        return 1

    failures = organize(
        directory,
        files,
        dry_run=dry_run,
        unknown_folder=args.unknown_folder.strip(),
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
