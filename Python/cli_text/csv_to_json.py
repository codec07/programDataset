#!/usr/bin/env python3
"""Convert CSV files to JSON (array or newline-delimited JSON).

The delimiter is sniffed from the first chunk of the file unless one is
given explicitly. Header names are de-duplicated, ragged rows are padded
(or keep their surplus values in an "extra" list), and `--types` enables
conservative inference of integers, floats, booleans and nulls.

Usage:
    python csv_to_json.py people.csv
    python csv_to_json.py people.csv -o people.json --indent 4
    python csv_to_json.py export.tsv --delimiter "\\t" --ndjson
    python csv_to_json.py data.csv --no-header --types
    type data.csv | python csv_to_json.py - --types
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Sequence

INT_RE = re.compile(r"^[+-]?\d+$")


def read_text(path: str, encoding: str) -> str:
    """Read a CSV source as text, supporting '-' for stdin."""
    if path == "-":
        data = sys.stdin.read()
        return data.lstrip("\ufeff")
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


def detect_delimiter(sample: str, fallback: str = ",") -> str:
    """Sniff the CSV delimiter, falling back gracefully on tiny inputs."""
    if not sample.strip():
        return fallback
    try:
        dialect = csv.Sniffer().sniff(sample[:8192], delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return fallback


def infer_type(value: str) -> Any:
    """Conservatively convert a CSV string to a JSON scalar."""
    stripped = value.strip()
    if stripped == "":
        return ""
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered == "null":
        return None
    if INT_RE.match(stripped):
        try:
            return int(stripped)
        except ValueError:
            return value
    if any(ch in stripped for ch in ".eE") and re.match(r"^[+-]?[\d.eE+-]+$", stripped):
        try:
            number = float(stripped)
        except ValueError:
            return value
        if math.isfinite(number):
            return number
    return value


def unique_headers(raw: Sequence[str], width: int) -> list[str]:
    """Make header names non-empty and unique."""
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


def parse_rows(
    text: str,
    delimiter: str,
    has_header: bool,
    infer: bool,
) -> tuple[list[dict[str, Any]], int]:
    """Parse CSV text into records; return records and ragged-row count."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as exc:
        raise SystemExit(f"error: malformed CSV at line {reader.line_num}: {exc}")

    if not raw_rows:
        raise SystemExit("error: input contains no data rows")

    if has_header:
        headers = unique_headers(raw_rows[0], len(raw_rows[0]))
        data_rows = raw_rows[1:]
    else:
        headers = [f"column_{i + 1}" for i in range(len(raw_rows[0]))]
        data_rows = raw_rows

    if not data_rows:
        raise SystemExit("error: input has a header but no data rows")

    records: list[dict[str, Any]] = []
    ragged = 0
    for row in data_rows:
        if len(row) != len(headers):
            ragged += 1
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            value = row[index] if index < len(row) else ""
            record[header] = infer_type(value) if infer else value
        if len(row) > len(headers):
            record["extra"] = list(row[len(headers):])
        records.append(record)
    return records, ragged


def write_output(payload: str, output: str | None) -> None:
    """Write JSON to a file or stdout."""
    if output is None or output == "-":
        print(payload)
        return
    try:
        with open(output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload + "\n")
    except OSError as exc:
        raise SystemExit(f"error: cannot write {output}: {exc}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a CSV file to JSON.",
        epilog="The delimiter is auto-detected unless --delimiter is supplied.",
    )
    parser.add_argument("csvfile", help="CSV/TSV file, or '-' for stdin")
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    parser.add_argument("--delimiter", help="field delimiter (default: auto-detect)")
    parser.add_argument("--encoding", default="utf-8", help="input encoding (default: utf-8)")
    parser.add_argument("--no-header", action="store_true",
                        help="treat the first row as data and name columns column_1..N")
    parser.add_argument("--types", action="store_true",
                        help="infer integers, floats, booleans and nulls")
    parser.add_argument("--ndjson", action="store_true",
                        help="emit one JSON object per line instead of an array")
    parser.add_argument("--indent", type=int, default=2, metavar="N",
                        help="pretty-print indentation (default: 2, 0 = compact)")
    parser.add_argument("--strict", action="store_true",
                        help="fail when any row has the wrong number of fields")
    args = parser.parse_args(argv)

    if args.delimiter is not None and len(args.delimiter) != 1:
        parser.error("--delimiter must be exactly one character")
    if not 0 <= args.indent <= 8:
        parser.error("--indent must be between 0 and 8")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    text = read_text(args.csvfile, args.encoding)
    if not text.strip():
        raise SystemExit("error: input is empty")

    delimiter = args.delimiter or detect_delimiter(text)
    records, ragged = parse_rows(text, delimiter, not args.no_header, args.types)

    if ragged:
        print(
            f"warning: {ragged} row(s) had a different field count; "
            "short rows were padded and surplus values kept under 'extra'",
            file=sys.stderr,
        )
        if args.strict:
            raise SystemExit("error: ragged rows found in --strict mode")

    if args.ndjson:
        payload = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    elif args.indent > 0:
        payload = json.dumps(records, ensure_ascii=False, indent=args.indent)
    else:
        payload = json.dumps(records, ensure_ascii=False, separators=(",", ":"))

    write_output(payload, args.output)
    if args.output and args.output != "-":
        print(
            f"converted {len(records)} record(s) using delimiter {delimiter!r} -> {args.output}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
