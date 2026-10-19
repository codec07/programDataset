#!/usr/bin/env python3
"""Count word frequencies in UTF-8 text files or standard input.

The tool tokenises words, optionally drops very short tokens and common
English stop words, then prints a ranked frequency table. Aggregating
several files is supported, and JSON output makes the result easy to feed
into another program.

Usage:
    python word_frequency.py notes.txt
    python word_frequency.py chapter1.txt chapter2.txt --top 20
    python word_frequency.py notes.txt --min-length 3 --ignore-stopwords
    type notes.txt | python word_frequency.py - --case-sensitive
    python word_frequency.py notes.txt --json > counts.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

# A word is a run of letters/digits; internal apostrophes and hyphens are
# kept so "don't" and "state-of-the-art" stay together.
WORD_RE = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*", re.UNICODE)

STOP_WORDS = frozenset(
    """
    a about after again against all am an and any are as at be because been
    before being below between both but by can could did do does doing down
    during each few for from further had has have having he her here hers
    herself him himself his how i if in into is it its itself just me more
    most my myself no nor not now of off on once only or other our ours
    ourselves out over own same she should so some such than that the their
    theirs them themselves then there these they this those through to too
    under until up very was we were what when where which while who whom why
    will with would you your yours yourself yourselves
    """.split()
)


def read_source(path: str) -> str:
    """Return the text of *path*, or stdin when path is '-'."""
    if path == "-":
        try:
            return sys.stdin.read()
        except UnicodeDecodeError as exc:
            raise SystemExit(f"error: stdin is not valid UTF-8 ({exc.reason})")
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def iter_words(text: str, case_sensitive: bool = False) -> Iterable[str]:
    """Yield words from *text*, lower-casing them unless requested otherwise."""
    for match in WORD_RE.finditer(text):
        word = match.group(0)
        yield word if case_sensitive else word.casefold()


def count_words(
    texts: Sequence[str],
    *,
    case_sensitive: bool,
    min_length: int,
    ignore_stopwords: bool,
) -> tuple[Counter[str], int]:
    """Count words across *texts* and return the counter plus total tokens."""
    counter: Counter[str] = Counter()
    total = 0
    for text in texts:
        for word in iter_words(text, case_sensitive):
            total += 1
            if len(word) < min_length:
                continue
            if ignore_stopwords and word.casefold() in STOP_WORDS:
                continue
            counter[word] += 1
    return counter, total


def print_table(counter: Counter[str], top: int, total: int) -> None:
    """Print a fixed-width ranked table to stdout."""
    if not counter:
        return
    rows = counter.most_common(top)
    word_width = min(max(len(word) for word, _ in rows), 30)
    rank_width = len(str(len(rows)))
    kept = sum(counter.values())

    header = f"{'#':>{rank_width}}  {'WORD':<{word_width}}  {'COUNT':>7}  {'SHARE':>7}"
    print(header)
    print("-" * len(header))
    for rank, (word, count) in enumerate(rows, start=1):
        share = (count / kept * 100) if kept else 0.0
        shown = word if len(word) <= word_width else word[: word_width - 3] + "..."
        print(f"{rank:>{rank_width}}  {shown:<{word_width}}  {count:>7}  {share:>6.2f}%")
    print()
    print(f"Tokens read: {total}    Distinct words kept: {len(counter)}    Shown: {len(rows)}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count word frequencies in text files or stdin.",
        epilog="Use '-' as a path to read from standard input.",
    )
    parser.add_argument("paths", nargs="+", help="UTF-8 text files, or '-' for stdin")
    parser.add_argument("--top", type=int, default=25, metavar="N",
                        help="show only the N most common words (default: 25)")
    parser.add_argument("--min-length", type=int, default=1, metavar="N",
                        help="ignore words shorter than N characters (default: 1)")
    parser.add_argument("--case-sensitive", action="store_true",
                        help="treat 'Word' and 'word' as different words")
    parser.add_argument("--ignore-stopwords", action="store_true",
                        help="drop common English stop words")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.min_length < 1:
        parser.error("--min-length must be at least 1")
    if args.paths.count("-") > 1:
        parser.error("stdin ('-') may only be given once")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    texts = [read_source(path) for path in args.paths]
    counter, total = count_words(
        texts,
        case_sensitive=args.case_sensitive,
        min_length=args.min_length,
        ignore_stopwords=args.ignore_stopwords,
    )

    if not counter:
        print("error: no words matched the given filters", file=sys.stderr)
        return 1

    if args.as_json:
        payload = {
            "sources": args.paths,
            "tokens_read": total,
            "distinct_words": len(counter),
            "words": [{"word": w, "count": c} for w, c in counter.most_common(args.top)],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_table(counter, args.top, total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
