#!/usr/bin/env python3
"""Report readability and size statistics for text files.

For every input file (or stdin) the tool prints line, word, character,
sentence and paragraph counts, estimated reading/speaking time, and the
Flesch reading-ease score with a rough US grade level. Multi-file totals
are printed when more than one source is analysed.

Usage:
    python text_stats.py article.txt
    python text_stats.py draft.md notes.txt
    type article.txt | python text_stats.py -
    python text_stats.py article.txt --json
    python text_stats.py article.txt --words-per-minute 180
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

WORD_RE = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*", re.UNICODE)
SENTENCE_RE = re.compile(r"[.!?]+(?:[\"'\u201d\u2019)]*)(?=\s|$)")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


@dataclass
class TextStats:
    """Statistics collected for a single text source."""

    source: str
    characters: int = 0
    characters_no_spaces: int = 0
    words: int = 0
    unique_words: int = 0
    sentences: int = 0
    paragraphs: int = 0
    lines: int = 0
    non_empty_lines: int = 0
    longest_line: int = 0
    syllables: int = 0
    reading_minutes: float = 0.0
    speaking_minutes: float = 0.0
    flesch_ease: float | None = None
    grade_level: str = "n/a"
    extra: dict = field(default_factory=dict)


def read_source(path: str) -> str:
    """Read *path* as UTF-8, using stdin for '-'."""
    if path == "-":
        try:
            return sys.stdin.read()
        except UnicodeDecodeError as exc:
            raise SystemExit(f"error: stdin is not valid UTF-8 ({exc.reason})")
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


def count_syllables(word: str) -> int:
    """Estimate the number of syllables in an English *word*.

    The heuristic counts vowel groups and subtracts a silent trailing 'e',
    which is accurate enough for the Flesch score at document level.
    """
    word = word.lower()
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def analyze_text(text: str, source: str, wpm: int = 200) -> TextStats:
    """Compute all statistics for *text*."""
    stats = TextStats(source=source)
    stats.characters = len(text)
    stats.characters_no_spaces = sum(1 for ch in text if not ch.isspace())
    stats.lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)

    lines = text.splitlines()
    stats.non_empty_lines = sum(1 for line in lines if line.strip())
    stats.longest_line = max((len(line) for line in lines), default=0)

    words = WORD_RE.findall(text)
    stats.words = len(words)
    stats.unique_words = len({w.casefold() for w in words})
    stats.sentences = len(SENTENCE_RE.findall(text))
    blocks = [block for block in PARAGRAPH_SPLIT_RE.split(text) if block.strip()]
    stats.paragraphs = len(blocks)
    stats.syllables = sum(count_syllables(w) for w in words)

    if stats.words:
        stats.reading_minutes = stats.words / wpm
        stats.speaking_minutes = stats.words / 130

    if stats.words and stats.sentences:
        score = (
            206.835
            - 1.015 * (stats.words / stats.sentences)
            - 84.6 * (stats.syllables / stats.words)
        )
        stats.flesch_ease = round(score, 1)
        stats.grade_level = grade_label(score)
    return stats


def grade_label(score: float) -> str:
    """Map a Flesch reading-ease score to a plain-English grade label."""
    if score >= 90:
        return "5th grade (very easy)"
    if score >= 80:
        return "6th grade (easy)"
    if score >= 70:
        return "7th grade (fairly easy)"
    if score >= 60:
        return "8th-9th grade (plain English)"
    if score >= 50:
        return "10th-12th grade (fairly hard)"
    if score >= 30:
        return "college (hard)"
    return "college graduate (very hard)"


def print_stats(stats: TextStats) -> None:
    """Print one readable statistics block."""
    print(f"Source: {stats.source}")
    rows = [
        ("Lines", f"{stats.lines} ({stats.non_empty_lines} non-empty)"),
        ("Words", f"{stats.words} ({stats.unique_words} unique)"),
        ("Characters", f"{stats.characters} ({stats.characters_no_spaces} without spaces)"),
        ("Sentences", str(stats.sentences)),
        ("Paragraphs", str(stats.paragraphs)),
        ("Longest line", f"{stats.longest_line} chars"),
        ("Reading time", f"{stats.reading_minutes:.1f} min at 200 wpm"),
        ("Speaking time", f"{stats.speaking_minutes:.1f} min at 130 wpm"),
    ]
    if stats.flesch_ease is not None:
        rows.append(("Flesch ease", f"{stats.flesch_ease:.1f} - {stats.grade_level}"))
    else:
        rows.append(("Flesch ease", "n/a (needs at least one sentence)"))
    width = max(len(label) for label, _ in rows)
    for label, value in rows:
        print(f"  {label + ':':<{width + 1}} {value}")
    print()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show word, character and readability statistics for text files.",
        epilog="Use '-' as a path to read from standard input.",
    )
    parser.add_argument("paths", nargs="+", help="UTF-8 text files, or '-' for stdin")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="print machine-readable JSON")
    parser.add_argument("--words-per-minute", type=int, default=200, metavar="N",
                        help="reading speed used for the time estimate (default: 200)")
    args = parser.parse_args(argv)
    if args.words_per_minute < 50 or args.words_per_minute > 2000:
        parser.error("--words-per-minute must be between 50 and 2000")
    if args.paths.count("-") > 1:
        parser.error("stdin ('-') may only be given once")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    all_stats = [
        analyze_text(read_source(path), path, args.words_per_minute)
        for path in args.paths
    ]

    if args.as_json:
        payload = {"files": [asdict(item) for item in all_stats]}
        if len(all_stats) > 1:
            payload["totals"] = {
                "characters": sum(s.characters for s in all_stats),
                "words": sum(s.words for s in all_stats),
                "lines": sum(s.lines for s in all_stats),
                "reading_minutes": round(sum(s.reading_minutes for s in all_stats), 1),
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for stats in all_stats:
        print_stats(stats)

    if len(all_stats) > 1:
        words = sum(s.words for s in all_stats)
        chars = sum(s.characters for s in all_stats)
        print(f"TOTAL: {words} words, {chars} characters across {len(all_stats)} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
