#!/usr/bin/env python3
"""Shift SRT subtitle timestamps forwards or backwards by a fixed offset.

Every cue is validated before anything is written. A shift that would
produce a negative timestamp aborts the whole operation unless --clamp is
given. By default the shifted subtitles go to stdout; use --in-place or
--output to save them. With --in-place, --dry-run previews the result and
--backup keeps the original as a .bak file.

Usage:
    python srt_shift.py movie.srt --seconds 2.5
    python srt_shift.py movie.srt --seconds -1.2 -o fixed.srt
    python srt_shift.py movie.srt --seconds 3 --in-place --backup
    python srt_shift.py movie.srt --seconds 3 --in-place --dry-run
    python srt_shift.py movie.srt --seconds 12.3 --renumber
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

TIME_RE = re.compile(
    r"^(?P<h>\d{1,3}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})"
    r"\s*-->\s*"
    r"(?P<h2>\d{1,3}):(?P<m2>\d{2}):(?P<s2>\d{2})[,.](?P<ms2>\d{3})"
    r"(?P<settings>.*)$"
)


@dataclass
class Cue:
    """One subtitle cue."""

    index: int
    start_ms: int
    end_ms: int
    settings: str
    text: list[str]


def read_text(path: Path) -> str:
    """Read an SRT file as UTF-8 (BOM tolerated)."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def timestamp_to_ms(hours: str, minutes: str, seconds: str, millis: str) -> int:
    """Convert timestamp parts to milliseconds."""
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1000
        + int(millis)
    )


def ms_to_timestamp(value: int) -> str:
    """Format milliseconds as HH:MM:SS,mmm."""
    if value < 0:
        raise ValueError("negative timestamp")
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_srt(text: str) -> list[Cue]:
    """Parse SRT text, raising ValueError with a line number on bad input."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues: list[Cue] = []
    position = 0

    while position < len(lines):
        while position < len(lines) and not lines[position].strip():
            position += 1
        if position >= len(lines):
            break

        index_line = lines[position].strip()
        if not index_line.isdigit():
            raise ValueError(f"line {position + 1}: expected a numeric cue index")
        index = int(index_line)
        position += 1
        if position >= len(lines):
            raise ValueError(f"line {position + 1}: missing timestamp line")

        match = TIME_RE.match(lines[position].strip())
        if not match:
            raise ValueError(f"line {position + 1}: invalid timestamp line")
        start = timestamp_to_ms(
            match["h"], match["m"], match["s"], match["ms"]
        )
        end = timestamp_to_ms(
            match["h2"], match["m2"], match["s2"], match["ms2"]
        )
        if end < start:
            raise ValueError(f"line {position + 1}: cue ends before it starts")
        settings = match["settings"].strip()
        position += 1

        body: list[str] = []
        while position < len(lines) and lines[position].strip():
            body.append(lines[position].rstrip())
            position += 1
        if not body:
            raise ValueError(f"cue {index}: no subtitle text")

        cues.append(Cue(index, start, end, settings, body))

    if not cues:
        raise ValueError("no subtitle cues found")
    return cues


def shift_cues(cues: Sequence[Cue], offset_ms: int, clamp: bool) -> list[Cue]:
    """Return cues shifted by *offset_ms*, rejecting negative timestamps."""
    shifted: list[Cue] = []
    for cue in cues:
        start = cue.start_ms + offset_ms
        end = cue.end_ms + offset_ms
        if clamp:
            start = max(0, start)
            end = max(0, end)
        if start < 0 or end < 0:
            raise ValueError(
                f"cue {cue.index} would start before zero; use --clamp to allow it"
            )
        shifted.append(Cue(cue.index, start, end, cue.settings, cue.text))
    return shifted


def render_srt(cues: Sequence[Cue], renumber: bool) -> str:
    """Serialise cues back to SRT text."""
    blocks: list[str] = []
    for position, cue in enumerate(cues, start=1):
        index = position if renumber else cue.index
        timing = f"{ms_to_timestamp(cue.start_ms)} --> {ms_to_timestamp(cue.end_ms)}"
        if cue.settings:
            timing += f" {cue.settings}"
        blocks.append("\n".join([str(index), timing, *cue.text]))
    return "\n\n".join(blocks) + "\n"


def atomic_write(path: Path, text: str) -> None:
    """Write text atomically, keeping the original if anything fails."""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(text)
            temp_name = handle.name
        os.replace(temp_name, path)
    except OSError as exc:
        raise SystemExit(f"error: cannot write {path}: {exc}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shift SRT subtitle timestamps by a fixed offset.",
        epilog="Negative shifts are allowed; use --clamp to stop at 00:00:00,000.",
    )
    parser.add_argument("file", help="input .srt file")
    parser.add_argument("--seconds", type=float, required=True, metavar="N",
                        help="offset in seconds (negative moves subtitles earlier)")
    parser.add_argument("-o", "--output", help="write to this file instead of stdout")
    parser.add_argument("--in-place", action="store_true",
                        help="rewrite the input file")
    parser.add_argument("--backup", action="store_true",
                        help="with --in-place, save a .bak copy first")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --in-place, print the result without writing")
    parser.add_argument("--clamp", action="store_true",
                        help="clamp timestamps at zero instead of failing")
    parser.add_argument("--renumber", action="store_true",
                        help="renumber cues sequentially from 1")
    args = parser.parse_args(argv)

    if args.in_place and args.output:
        parser.error("--in-place and --output are mutually exclusive")
    if args.dry_run and not args.in_place:
        parser.error("--dry-run only makes sense together with --in-place")
    if args.backup and not args.in_place:
        parser.error("--backup only makes sense together with --in-place")
    if not -86400 <= args.seconds <= 86400:
        parser.error("--seconds must be between -86400 and 86400")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.file)
    text = read_text(source)

    try:
        cues = parse_srt(text)
        offset_ms = round(args.seconds * 1000)
        shifted = shift_cues(cues, offset_ms, args.clamp)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = render_srt(shifted, args.renumber)
    print(f"shifted {len(cues)} cue(s) by {offset_ms} ms", file=sys.stderr)

    if args.dry_run:
        sys.stdout.write(output)
        print("[dry-run] input file not modified", file=sys.stderr)
        return 0

    if args.in_place:
        if args.backup:
            backup = source.with_name(f"{source.name}.bak")
            try:
                shutil.copy2(source, backup)
            except OSError as exc:
                print(f"error: cannot create backup {backup}: {exc}", file=sys.stderr)
                return 1
            print(f"backup: {backup}", file=sys.stderr)
        atomic_write(source, output)
        print(f"updated: {source}", file=sys.stderr)
        return 0

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(output)
        except OSError as exc:
            print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
            return 1
        print(f"wrote: {args.output}", file=sys.stderr)
        return 0

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
