#!/usr/bin/env python3
"""Reflow and justify plain text to a chosen line width.

Paragraphs are rejoined and wrapped, blank lines are preserved as single
separators, and bullet lists keep their markers with hanging indents.
`--no-reflow` wraps each existing line independently instead, which is
useful for code or poetry. Output goes to stdout unless -o is given.

Usage:
    python text_wrap_formatter.py notes.txt
    python text_wrap_formatter.py draft.txt --width 100 --justify
    python text_wrap_formatter.py README.md --width 72 -o wrapped.md
    type notes.txt | python text_wrap_formatter.py - --width 60
    python text_wrap_formatter.py poem.txt --no-reflow --width 40
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path
from typing import Sequence

BULLET_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>(?:[-*+]|\d+[.)])\s+)(?P<text>.*)$")


def read_source(path: str) -> str:
    """Read UTF-8 text from a file or stdin."""
    if path == "-":
        return sys.stdin.read()
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def split_blocks(text: str) -> list[list[str]]:
    """Split text into blank-line separated blocks of non-empty lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def justify_line(line: str, width: int) -> str:
    """Expand the spaces in *line* so it reaches *width* characters."""
    content = line.strip()
    words = content.split()
    if len(words) < 2:
        return line
    indent = line[: len(line) - len(line.lstrip())]
    available = width - len(indent) - sum(len(word) for word in words)
    if available < len(words) - 1:
        return line
    base, extra = divmod(available, len(words) - 1)
    pieces = [words[0]]
    for index, word in enumerate(words[1:]):
        spaces = base + (1 if index < extra else 0)
        pieces.append(" " * spaces + word)
    return indent + "".join(pieces)


def wrap_paragraph(
    text: str,
    width: int,
    *,
    initial_indent: str = "",
    subsequent_indent: str = "",
    justify: bool,
    break_long_words: bool,
) -> list[str]:
    """Wrap one paragraph and optionally justify all but its last line."""
    if len(initial_indent) >= width:
        lines = [initial_indent + text]
    else:
        lines = textwrap.wrap(
            text,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=break_long_words,
            break_on_hyphens=False,
        )
    if justify and len(lines) > 1:
        lines = [
            justify_line(line, width) if index < len(lines) - 1 else line
            for index, line in enumerate(lines)
        ]
    return lines or [initial_indent.rstrip()]


def format_list_block(
    lines: Sequence[str], width: int, justify: bool, break_long_words: bool
) -> list[str]:
    """Format a block whose lines are bullet items (with continuations)."""
    items: list[tuple[str, str]] = []
    current_marker: str | None = None
    current_text = ""

    for line in lines:
        match = BULLET_RE.match(line)
        if match:
            if current_marker is not None:
                items.append((current_marker, current_text.strip()))
            current_marker = match.group("indent") + match.group("marker")
            current_text = match.group("text")
        elif current_marker is not None:
            current_text += " " + line.strip()
        else:
            items.append(("", line.strip()))

    if current_marker is not None:
        items.append((current_marker, current_text.strip()))

    output: list[str] = []
    for marker, content in items:
        if not content:
            output.append(marker.rstrip())
            continue
        output.extend(wrap_paragraph(
            content, width,
            initial_indent=marker,
            subsequent_indent=" " * len(marker),
            justify=justify,
            break_long_words=break_long_words,
        ))
    return output


def format_block(
    lines: Sequence[str], width: int, justify: bool, break_long_words: bool
) -> list[str]:
    """Format one paragraph or list block."""
    has_bullet = any(BULLET_RE.match(line) for line in lines)
    if has_bullet:
        return format_list_block(lines, width, justify, break_long_words)

    text = " ".join(line.strip() for line in lines)
    return wrap_paragraph(
        text, width, justify=justify, break_long_words=break_long_words
    )


def format_text(
    text: str,
    width: int,
    *,
    reflow: bool,
    justify: bool,
    break_long_words: bool,
) -> str:
    """Format a whole document."""
    if not text.strip():
        return ""
    if not reflow:
        output: list[str] = []
        for line in text.splitlines():
            if not line.strip():
                output.append("")
                continue
            indent = line[: len(line) - len(line.lstrip())]
            output.extend(wrap_paragraph(
                line.strip(), width,
                initial_indent=indent,
                subsequent_indent=indent,
                justify=justify,
                break_long_words=break_long_words,
            ))
        return "\n".join(output).strip("\n") + "\n"

    blocks = split_blocks(text)
    formatted = [
        format_block(block, width, justify, break_long_words) for block in blocks
    ]
    return "\n\n".join("\n".join(block) for block in formatted).strip("\n") + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reflow and justify plain text.",
        epilog="Bullet markers are preserved with hanging indents.",
    )
    parser.add_argument("paths", nargs="*", default=["-"],
                        help="text files, or '-' for stdin (default: stdin)")
    parser.add_argument("--width", type=int, default=80, metavar="N",
                        help="target line width (default: 80)")
    parser.add_argument("--justify", action="store_true",
                        help="stretch lines to the full width")
    parser.add_argument("--no-reflow", action="store_true",
                        help="wrap each existing line independently")
    parser.add_argument("--no-break-long-words", action="store_true",
                        help="leave words longer than the width intact")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args(argv)

    if not 20 <= args.width <= 200:
        parser.error("--width must be between 20 and 200")
    if args.paths.count("-") > 1:
        parser.error("stdin ('-') may only be given once")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pieces: list[str] = []
    for path in args.paths:
        formatted = format_text(
            read_source(path),
            args.width,
            reflow=not args.no_reflow,
            justify=args.justify,
            break_long_words=not args.no_break_long_words,
        )
        if formatted:
            pieces.append(formatted.rstrip("\n"))

    result = "\n\n".join(pieces)
    if result:
        result += "\n"

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(result)
        except OSError as exc:
            raise SystemExit(f"error: cannot write {args.output}: {exc}")
        print(f"wrote {len(result)} characters to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
