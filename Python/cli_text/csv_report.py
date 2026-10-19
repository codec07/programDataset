#!/usr/bin/env python3
"""Profile a CSV file and optionally aggregate numeric columns by group.

The default report describes every column: inferred type, missing and
unique counts, numeric summary (min/max/mean/median) and the most common
values. With --group-by, rows are grouped and the columns named in --agg
are aggregated with sum, mean, min, max or count.

Usage:
    python csv_report.py sales.csv
    python csv_report.py sales.csv --top 5
    python csv_report.py sales.csv --group-by region --agg amount:sum
    python csv_report.py sales.csv --group-by region --agg amount:mean --agg units:sum
    python csv_report.py sales.csv --json
    python csv_report.py export.tsv --delimiter "\\t"
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Sequence

INT_RE = re.compile(r"^[+-]?\d+$")
AGGREGATES = ("sum", "mean", "min", "max", "count")


def read_text(path: str, encoding: str) -> str:
    """Read the CSV source, supporting stdin."""
    if path == "-":
        return sys.stdin.read().lstrip("\ufeff")
    try:
        with open(path, "r", encoding=encoding, newline="") as handle:
            return handle.read().lstrip("\ufeff")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: cannot decode {path} as {encoding} ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def detect_delimiter(text: str) -> str:
    """Sniff a delimiter, falling back to a comma."""
    try:
        return csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def unique_headers(raw: Sequence[str], width: int) -> list[str]:
    """Return non-empty, unique header names."""
    headers: list[str] = []
    used: set[str] = set()
    for index in range(width):
        name = raw[index].strip() if index < len(raw) else ""
        name = name or f"column_{index + 1}"
        candidate = name
        suffix = 2
        while candidate in used:
            candidate = f"{name}_{suffix}"
            suffix += 1
        used.add(candidate)
        headers.append(candidate)
    return headers


def load_table(text: str, delimiter: str, has_header: bool
               ) -> tuple[list[str], list[list[str]], int]:
    """Parse CSV text into headers and rectangular rows."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as exc:
        raise SystemExit(f"error: malformed CSV at line {reader.line_num}: {exc}")
    if not raw_rows:
        raise SystemExit("error: input contains no data")

    if has_header:
        headers = unique_headers(raw_rows[0], len(raw_rows[0]))
        data = raw_rows[1:]
    else:
        headers = [f"column_{i + 1}" for i in range(len(raw_rows[0]))]
        data = raw_rows
    if not data:
        raise SystemExit("error: input has no data rows")

    ragged = 0
    rows: list[list[str]] = []
    for row in data:
        if len(row) != len(headers):
            ragged += 1
            row = (row + [""] * len(headers))[: len(headers)]
        rows.append(row)
    return headers, rows, ragged


def parse_number(value: str) -> int | float | None:
    """Parse a numeric cell, returning None when it is not a number."""
    stripped = value.strip()
    if not stripped:
        return None
    if INT_RE.match(stripped):
        try:
            return int(stripped)
        except ValueError:
            return None
    try:
        number = float(stripped)
    except ValueError:
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def profile_column(name: str, values: Sequence[str], top: int) -> dict[str, Any]:
    """Build a profile dictionary for one column."""
    non_empty = [value.strip() for value in values if value.strip()]
    numbers = [parse_number(value) for value in non_empty]
    numeric = bool(non_empty) and all(number is not None for number in numbers)

    profile: dict[str, Any] = {
        "name": name,
        "type": "number" if numeric else "text",
        "missing": len(values) - len(non_empty),
        "unique": len(set(non_empty)),
        "top": [],
    }

    if numeric:
        numeric_values = [float(number) for number in numbers if number is not None]
        profile.update({
            "min": min(numeric_values),
            "max": max(numeric_values),
            "mean": statistics.fmean(numeric_values),
            "median": statistics.median(numeric_values),
            "count": len(numeric_values),
        })
    else:
        counts = Counter(non_empty).most_common(top)
        profile["top"] = [{"value": value, "count": count} for value, count in counts]
    return profile


def print_profile(profile: dict[str, Any]) -> None:
    """Print one column profile block."""
    print(f"  {profile['name']} ({profile['type']})")
    print(f"    missing {profile['missing']}, unique {profile['unique']}")
    if profile["type"] == "number":
        print(
            f"    count {profile['count']}, min {profile['min']:.4g}, "
            f"max {profile['max']:.4g}, mean {profile['mean']:.4g}, "
            f"median {profile['median']:.4g}"
        )
    elif profile["top"]:
        rendered = ", ".join(
            f"{item['value']} ({item['count']})" for item in profile["top"]
        )
        print(f"    top: {rendered}")
    else:
        print("    (no non-empty values)")


def parse_aggregates(specs: Sequence[str], headers: Sequence[str]) -> list[tuple[int, str, str]]:
    """Parse COL:FUNC specs into (index, func, label) triples."""
    lookup = {name: index for index, name in enumerate(headers)}
    parsed: list[tuple[int, str, str]] = []
    for spec in specs:
        if ":" not in spec:
            raise SystemExit(f"error: --agg must look like COLUMN:FUNC, got {spec!r}")
        column, function = (part.strip() for part in spec.rsplit(":", 1))
        if column not in lookup:
            raise SystemExit(
                f"error: unknown column {column!r} in --agg "
                f"(available: {', '.join(headers)})"
            )
        if function not in AGGREGATES:
            raise SystemExit(
                f"error: unknown aggregate {function!r} "
                f"(choose from {', '.join(AGGREGATES)})"
            )
        parsed.append((lookup[column], function, f"{column}:{function}"))
    return parsed


def aggregate(values: Sequence[str], function: str) -> int | float | None:
    """Apply one aggregate to a column's values."""
    if function == "count":
        return sum(1 for value in values if value.strip())
    numbers = [parse_number(value) for value in values]
    numeric = [float(number) for number in numbers if number is not None]
    if not numeric:
        return None
    if function == "sum":
        return sum(numeric)
    if function == "mean":
        return statistics.fmean(numeric)
    if function == "min":
        return min(numeric)
    return max(numeric)


def group_report(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    group_column: str,
    aggregates: Sequence[tuple[int, str, str]],
) -> list[dict[str, Any]]:
    """Aggregate rows by a column and return ordered group dictionaries."""
    try:
        group_index = list(headers).index(group_column)
    except ValueError:
        raise SystemExit(
            f"error: unknown group column {group_column!r} "
            f"(available: {', '.join(headers)})"
        )

    groups: "OrderedDict[str, list[Sequence[str]]]" = OrderedDict()
    for row in rows:
        key = row[group_index].strip() or "(blank)"
        groups.setdefault(key, []).append(row)

    results: list[dict[str, Any]] = []
    for key in sorted(groups):
        members = groups[key]
        entry: dict[str, Any] = {"group": key, "rows": len(members)}
        for index, function, label in aggregates:
            entry[label] = aggregate([row[index] for row in members], function)
        results.append(entry)
    return results


def format_value(value: int | float | None) -> str:
    """Format an aggregate for the text table."""
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}".rstrip("0").rstrip(".")


def print_groups(column: str, aggregates: Sequence[tuple[int, str, str]],
                 results: Sequence[dict[str, Any]]) -> None:
    """Print the grouped aggregation table."""
    print(f"\nGrouped by {column}: {len(results)} group(s)")
    labels = [label for _, _, label in aggregates]
    headers = ["GROUP", "ROWS", *labels]
    rows = []
    for entry in results:
        rows.append([
            entry["group"], str(entry["rows"]),
            *(format_value(entry[label]) for label in labels),
        ])
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile CSV columns and aggregate numeric values by group.",
    )
    parser.add_argument("csvfile", help="CSV/TSV file, or '-' for stdin")
    parser.add_argument("--delimiter", help="field delimiter (default: auto-detect)")
    parser.add_argument("--encoding", default="utf-8", help="input encoding (default: utf-8)")
    parser.add_argument("--no-header", action="store_true",
                        help="name columns column_1..N instead of using row 1")
    parser.add_argument("--top", type=int, default=3, metavar="N",
                        help="common values shown per text column (default: 3)")
    parser.add_argument("--group-by", metavar="COLUMN",
                        help="group rows by this column before aggregating")
    parser.add_argument("--agg", action="append", default=[], metavar="COL:FUNC",
                        help="aggregate COLUMN with sum/mean/min/max/count (repeatable)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON")
    args = parser.parse_args(argv)

    if args.delimiter is not None and len(args.delimiter) != 1:
        parser.error("--delimiter must be exactly one character")
    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.agg and not args.group_by:
        parser.error("--agg requires --group-by")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    text = read_text(args.csvfile, args.encoding)
    if not text.strip():
        raise SystemExit("error: input is empty")
    delimiter = args.delimiter or detect_delimiter(text)
    headers, rows, ragged = load_table(text, delimiter, not args.no_header)

    profiles = [
        profile_column(headers[index], [row[index] for row in rows], args.top)
        for index in range(len(headers))
    ]
    groups = None
    aggregates: list[tuple[int, str, str]] = []
    if args.group_by:
        aggregates = parse_aggregates(args.agg, headers)
        groups = group_report(headers, rows, args.group_by, aggregates)

    if ragged:
        print(
            f"warning: {ragged} ragged row(s) were padded or truncated",
            file=sys.stderr,
        )

    if args.as_json:
        payload = {
            "file": args.csvfile,
            "rows": len(rows),
            "columns": profiles,
            "groups": groups,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"CSV report: {args.csvfile}")
    print(f"  {len(rows)} row(s), {len(headers)} column(s), delimiter {delimiter!r}\n")
    for profile in profiles:
        print_profile(profile)

    if groups is not None and args.group_by:
        print_groups(args.group_by, aggregates, groups)
    return 0


if __name__ == "__main__":
    sys.exit(main())
