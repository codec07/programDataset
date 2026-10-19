"""Clean and normalise CSV files with a streaming, constant-memory pipeline.

Reads a CSV, applies a configurable set of cleaning steps, and writes a new
CSV.  Rows are streamed one at a time so arbitrarily large files can be
processed without loading them into memory.

Usage:
    python csv_cleaner.py messy.csv -o clean.csv --trim --dedupe --drop-empty
    python csv_cleaner.py messy.csv -o clean.csv --fill-empty NA --dry-run
    python csv_cleaner.py messy.csv -o clean.csv --lower-cols email,name --force
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stream-clean a CSV file.")
    p.add_argument("source", type=Path, help="input CSV path")
    p.add_argument("-o", "--output", type=Path, required=True, help="output CSV path")
    p.add_argument("--trim", action="store_true", help="strip surrounding whitespace")
    p.add_argument("--drop-empty", action="store_true",
                   help="drop rows where every field is empty")
    p.add_argument("--fill-empty", metavar="VALUE", default=None,
                   help="replace empty fields with VALUE")
    p.add_argument("--dedupe", action="store_true", help="drop duplicate rows")
    p.add_argument("--lower-cols", nargs="*", default=[], metavar="COL",
                   help="lowercase values in the named columns")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would happen without writing")
    p.add_argument("--force", action="store_true", help="overwrite output if it exists")
    p.add_argument("--delimiter", default=",", help="input delimiter (default ',')")
    return p.parse_args(argv)


def clean_row(row: dict[str, str], *, trim: bool, fill: str | None,
              lower_cols: set[str]) -> dict[str, str]:
    """Normalise a single row; unknown extra columns are discarded."""
    out: dict[str, str] = {}
    for key, value in row.items():
        if key is None:          # ragged row: extra unnamed fields
            continue
        text = value if value is not None else ""
        if trim:
            text = text.strip()
        if fill is not None and text == "":
            text = fill
        if key.strip().lower() in lower_cols:
            text = text.lower()
        out[key.strip()] = text
    return out


def process(source: Path, output: Path, args: argparse.Namespace,
            lower_cols: set[str]) -> dict[str, int]:
    """Stream source -> output and return counters."""
    stats = {"in": 0, "out": 0, "empty": 0, "dupe": 0}
    seen: set[tuple[str, ...]] = set()

    with source.open("r", encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src, delimiter=args.delimiter)
        if not reader.fieldnames:
            raise ValueError(f"{source} has no header row")
        header = [h.strip() for h in reader.fieldnames]

        dst = None
        try:
            writer: csv.DictWriter | None = None
            if not args.dry_run:
                dst = output.open("w", encoding="utf-8", newline="")
                writer = csv.DictWriter(dst, fieldnames=header,
                                        extrasaction="ignore", lineterminator="\r\n")
                writer.writeheader()

            for row in reader:
                stats["in"] += 1
                cleaned = clean_row(row, trim=args.trim, fill=args.fill_empty,
                                    lower_cols=lower_cols)
                if args.drop_empty and not any(cleaned.values()):
                    stats["empty"] += 1
                    continue
                key = tuple(cleaned.get(col, "") for col in header)
                if args.dedupe:
                    if key in seen:
                        stats["dupe"] += 1
                        continue
                    seen.add(key)
                if writer is not None:
                    writer.writerow(cleaned)
                stats["out"] += 1
        finally:
            if dst is not None:
                dst.close()
    return stats


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.source.is_file():
        print(f"error: input not found: {args.source}", file=sys.stderr)
        return 2
    if args.output.resolve() == args.source.resolve():
        print("error: refusing to overwrite the input file", file=sys.stderr)
        return 2
    if args.output.exists() and not args.force and not args.dry_run:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    lower_cols = {c.strip().lower() for c in args.lower_cols}
    try:
        stats = process(args.source, args.output, args, lower_cols)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    verb = "would keep" if args.dry_run else "wrote"
    print(f"rows read:            {stats['in']}")
    print(f"empty rows dropped:   {stats['empty']}")
    print(f"duplicate rows dropped: {stats['dupe']}")
    print(f"{verb}: {stats['out']} rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
