"""A streaming CSV pipeline: read -> transform -> aggregate -> write.

Every stage is a generator, so files larger than memory are fine; only the
aggregate state (one entry per group) is held.  Bad rows are counted and
skipped rather than aborting the run.

Usage:
    python data_pipeline.py --generate-sample 20000 --out sample.csv
    python data_pipeline.py --input sample.csv --group-by region \\
        --value amount --agg sum --out totals.csv
    python data_pipeline.py --input sample.csv --group-by region --value amount \\
        --agg mean --out mean.csv --dry-run
    python data_pipeline.py --demo
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

REGIONS = ("north", "south", "east", "west", "central")
PRODUCTS = ("widget", "gadget", "sprocket", "bolt", "nut")
AGGS = ("sum", "count", "mean", "min", "max")


def read_csv(path: Path) -> Iterator[dict[str, str]]:
    """Yield rows as dicts, streaming from disk."""
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no header row")
        header = [name.strip() for name in reader.fieldnames]
        for row in reader:
            yield {key.strip(): (value if value is not None else "") for key, value
                   in row.items() if key is not None and key.strip() in header}


def transform(rows: Iterable[dict[str, str]], value_col: str,
              key_col: str) -> Iterator[tuple[str, float]]:
    """Coerce the value column to float; skip rows that cannot be parsed."""
    for row in rows:
        key = (row.get(key_col) or "").strip()
        raw = (row.get(value_col) or "").strip().replace(",", "")
        if not key or not raw:
            continue
        try:
            yield key, float(raw)
        except ValueError:
            continue


class Aggregator:
    """Incremental aggregate holding one small record per group.

    Every mode is computed with running state (no per-group value lists), so
    memory depends only on the number of distinct groups.
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.count: dict[str, int] = defaultdict(int)
        self.total: dict[str, float] = defaultdict(float)
        self.extremes: dict[str, float] = {}
        self.rows_seen = 0

    def add(self, key: str, value: float) -> None:
        self.rows_seen += 1
        self.count[key] += 1
        self.total[key] += value
        if self.mode == "min":
            self.extremes[key] = min(self.extremes.get(key, value), value)
        elif self.mode == "max":
            self.extremes[key] = max(self.extremes.get(key, value), value)

    def result(self) -> list[tuple[str, float, int]]:
        out: list[tuple[str, float, int]] = []
        for key in sorted(self.count):
            n = self.count[key]
            if self.mode == "sum":
                value = self.total[key]
            elif self.mode == "count":
                value = float(n)
            elif self.mode == "mean":
                value = self.total[key] / n
            else:
                value = self.extremes[key]
            out.append((key, value, n))
        return out


def write_csv(path: Path, rows: Iterable[tuple[str, ...]],
              header: tuple[str, ...]) -> int:
    written = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\r\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
            written += 1
    return written


def generate_sample(path: Path, rows: int, seed: int = 7) -> int:
    rng = random.Random(seed)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["order_id", "region", "product", "amount"])
        for index in range(rows):
            if index % 500 == 0 and index:  # sprinkle in a dirty row
                writer.writerow([index, rng.choice(REGIONS), "freebie", ""])
                continue
            writer.writerow([index, rng.choice(REGIONS), rng.choice(PRODUCTS),
                             f"{rng.uniform(5, 500):.2f}"])
    return rows


def run_pipeline(source: Path, key_col: str, value_col: str, mode: str,
                 out: Path | None, dry_run: bool) -> int:
    class Counter:
        """Wrap any iterator and count the items that pass through it."""

        def __init__(self) -> None:
            self.total = 0

        def wrap(self, items: Iterable[Any]) -> Iterator[Any]:
            for item in items:
                self.total += 1
                yield item

    counter = Counter()
    aggregator = Aggregator(mode)
    for key, value in transform(counter.wrap(read_csv(source)), value_col, key_col):
        aggregator.add(key, value)

    results = aggregator.result()
    groups = len(results)
    print(f"input rows     : {counter.total:,}")
    print(f"usable rows    : {aggregator.rows_seen:,} "
          f"({counter.total - aggregator.rows_seen:,} skipped)")
    print(f"groups         : {groups:,}")
    print(f"aggregate      : {mode}({value_col}) by {key_col}")
    for key, value, n in results[:5]:
        print(f"  {key:<16} {value:>14,.2f}  (n={n})")
    if groups > 5:
        print(f"  ... {groups - 5} more")

    if dry_run:
        print("[dry-run] no output written")
        return 0
    if out is not None:
        written = write_csv(
            out,
            ((key, f"{value:.4f}", str(n)) for key, value, n in results),
            (f"{key_col}", f"{mode}_{value_col}", "rows"),
        )
        print(f"wrote {written} group(s) -> {out}")
    return 0


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sample = root / "sample.csv"
        generate_sample(sample, 5000)
        print(f"generated {sample.stat().st_size:,} bytes of sample data\n")
        for mode in ("sum", "mean", "count", "min", "max"):
            print(f"--- {mode} ---")
            run_pipeline(sample, "region", "amount", mode, root / f"{mode}.csv", False)
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Streaming CSV aggregation pipeline.")
    p.add_argument("--input", type=Path, help="input CSV")
    p.add_argument("--group-by", default="region", help="key column")
    p.add_argument("--value", default="amount", help="numeric column")
    p.add_argument("--agg", choices=AGGS, default="sum")
    p.add_argument("--out", type=Path, help="output CSV path")
    p.add_argument("--generate-sample", type=int, metavar="N",
                   help="write an N-row sample CSV to --out and exit")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)

    if args.demo:
        return demo()

    if args.generate_sample is not None:
        if not args.out:
            print("error: --generate-sample needs --out", file=sys.stderr)
            return 2
        if args.generate_sample <= 0:
            print("error: sample size must be positive", file=sys.stderr)
            return 2
        if args.out.exists() and not args.force:
            print(f"error: {args.out} exists (use --force)", file=sys.stderr)
            return 2
        rows = generate_sample(args.out, args.generate_sample, args.seed)
        print(f"wrote {rows:,} row(s) -> {args.out}")
        return 0

    if not args.input or not args.input.is_file():
        print("error: --input CSV not found", file=sys.stderr)
        return 2
    if args.out and args.out.exists() and not args.force and not args.dry_run:
        print(f"error: {args.out} exists (use --force)", file=sys.stderr)
        return 2
    try:
        return run_pipeline(args.input, args.group_by, args.value, args.agg,
                            args.out, args.dry_run)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
