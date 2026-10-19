#!/usr/bin/env python3
"""Generate or refresh a Markdown table of contents from headings.

ATX headings (#, ##, ...) are detected while fenced code blocks are
ignored. Slugs follow the usual GitHub rules and duplicate headings get
numeric suffixes. For in-place updates the document must contain a marker
block:

    <!-- toc -->
    <!-- /toc -->

Everything between the markers is replaced. `--check` exits with status 1
when the table is missing or out of date, which is handy in CI.

Usage:
    python markdown_toc.py README.md
    python markdown_toc.py README.md --max-level 3
    python markdown_toc.py README.md --in-place --dry-run
    python markdown_toc.py docs/*.md --check
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TOC_START = "<!-- toc -->"
TOC_END = "<!-- /toc -->"
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


@dataclass(frozen=True)
class Heading:
    """A single Markdown heading and its generated anchor."""

    level: int
    text: str
    slug: str


def read_text(path: Path) -> str:
    """Read a UTF-8 Markdown file with friendly errors."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings."""
    try:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        raise SystemExit(f"error: cannot write {path}: {exc}")


def plain_heading(text: str) -> str:
    """Turn inline Markdown into the plain label shown in the TOC."""
    text = LINK_RE.sub(r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"[*_~]{1,3}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    """Create a GitHub-style anchor from heading text."""
    slug = plain_heading(text).lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "section"


def extract_headings(lines: Sequence[str]) -> list[Heading]:
    """Collect headings outside fenced code blocks, de-duplicating slugs."""
    headings: list[Heading] = []
    seen: dict[str, int] = {}
    fence: str | None = None

    for line in lines:
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue

        match = HEADING_RE.match(line)
        if not match:
            continue
        display = plain_heading(match.group(2))
        if not display:
            continue
        base = slugify(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        slug = base if count == 0 else f"{base}-{count}"
        headings.append(Heading(len(match.group(1)), display, slug))
    return headings


def build_toc(headings: Sequence[Heading], min_level: int, max_level: int) -> list[str]:
    """Return TOC bullet lines for headings within the requested levels."""
    selected = [h for h in headings if min_level <= h.level <= max_level]
    if not selected:
        return []
    base_level = min(h.level for h in selected)
    return [
        f"{'  ' * (h.level - base_level)}- [{h.text}](#{h.slug})"
        for h in selected
    ]


def find_markers(lines: Sequence[str]) -> tuple[int, int] | None:
    """Return (start, end) marker indexes, or None when markers are absent."""
    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if start is None and stripped == TOC_START:
            start = index
        elif start is not None and stripped == TOC_END:
            return start, index
    return None


def render_document(lines: Sequence[str], toc_lines: Sequence[str]) -> str:
    """Insert or replace the TOC block and return the new document text."""
    markers = find_markers(lines)
    if markers is None:
        raise ValueError(
            f"missing TOC markers ({TOC_START} and {TOC_END})"
        )
    start, end = markers
    block = [TOC_START, *toc_lines, TOC_END]
    updated = list(lines[:start]) + block + list(lines[end + 1 :])
    return "\n".join(updated).rstrip("\n") + "\n"


def show_diff(path: Path, before: Sequence[str], after: Sequence[str]) -> None:
    """Print a unified diff between the old and new document."""
    diff = difflib.unified_diff(
        before,
        after,
        fromfile=f"{path} (current)",
        tofile=f"{path} (updated)",
        lineterm="",
        n=2,
    )
    for line in diff:
        print(line)


def process_file(
    path: Path,
    *,
    min_level: int,
    max_level: int,
    in_place: bool,
    dry_run: bool,
    check: bool,
) -> bool:
    """Handle one file. Return True when the file is up to date."""
    original = read_text(path)
    lines = original.splitlines()
    headings = extract_headings(lines)
    toc_lines = build_toc(headings, min_level, max_level)

    if not headings:
        print(f"{path}: no headings found", file=sys.stderr)
        return False
    if not toc_lines:
        print(
            f"{path}: no headings between levels {min_level} and {max_level}",
            file=sys.stderr,
        )
        return False

    markers = find_markers(lines)
    if markers is None:
        if in_place or check:
            raise SystemExit(
                f"error: {path} has no marker block; add '{TOC_START}' and "
                f"'{TOC_END}' where the table of contents belongs"
            )
        print("\n".join(toc_lines))
        return True

    try:
        updated = render_document(lines, toc_lines)
    except ValueError as exc:
        raise SystemExit(f"error: {path}: {exc}")

    if updated == original:
        if not check:
            print(f"{path}: table of contents is up to date", file=sys.stderr)
        return True

    if check:
        print(f"{path}: table of contents is out of date", file=sys.stderr)
        return False

    if in_place and not dry_run:
        write_text(path, updated)
        print(f"{path}: table of contents updated", file=sys.stderr)
        return True

    if dry_run:
        show_diff(path, original.splitlines(), updated.splitlines())
    else:
        print("\n".join(toc_lines))
    return False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown table of contents from heading levels.",
    )
    parser.add_argument("files", nargs="+", help="Markdown files to process")
    parser.add_argument("--min-level", type=int, default=1, metavar="N",
                        help="lowest heading level to include (default: 1)")
    parser.add_argument("--max-level", type=int, default=6, metavar="N",
                        help="highest heading level to include (default: 6)")
    parser.add_argument("--in-place", action="store_true",
                        help="rewrite the file between the TOC markers")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --in-place, show the diff without writing")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any TOC is missing or out of date")
    args = parser.parse_args(argv)

    if not 1 <= args.min_level <= args.max_level <= 6:
        parser.error("require 1 <= --min-level <= --max-level <= 6")
    if args.dry_run and not args.in_place:
        parser.error("--dry-run only makes sense together with --in-place")
    if args.check and args.in_place:
        parser.error("--check and --in-place are mutually exclusive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    all_current = True
    for name in args.files:
        current = process_file(
            Path(name),
            min_level=args.min_level,
            max_level=args.max_level,
            in_place=args.in_place,
            dry_run=args.dry_run,
            check=args.check,
        )
        all_current = all_current and current
    if args.check and not all_current:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
