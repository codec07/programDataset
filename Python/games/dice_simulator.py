"""Dice Simulator (simulation).

Rolls a configurable set of dice many times and reports the distribution of
totals. The expected mean of ``n`` dice with ``s`` sides is ``n * (s + 1) / 2``.
Use ``--seed`` for a reproducible run and ``--csv`` to export the results.

Options
-------
    python dice_simulator.py
    python dice_simulator.py --dice 3 --sides 8 --rolls 50000 --seed 42
    python dice_simulator.py --dice 2 --rolls 100000 --csv dice.csv

Output
------
Console statistics plus an ASCII histogram, and an optional CSV with columns
``sum,count,percent``.

Run
---
    python dice_simulator.py --seed 1
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter


def roll_dice(rng: random.Random, dice: int, sides: int) -> int:
    return sum(rng.randint(1, sides) for _ in range(dice))


def simulate(rolls: int, dice: int, sides: int, rng: random.Random) -> Counter[int]:
    """Return a mapping of total -> frequency."""
    counts: Counter[int] = Counter()
    for _ in range(rolls):
        counts[roll_dice(rng, dice, sides)] += 1
    return counts


def histogram(count: int, maximum: int, width: int = 40) -> str:
    if maximum <= 0:
        return ""
    filled = round(width * count / maximum)
    return "#" * filled


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate rolling dice.")
    parser.add_argument("--dice", type=positive_int, default=2,
                        help="number of dice (default 2)")
    parser.add_argument("--sides", type=positive_int, default=6,
                        help="sides per die (default 6)")
    parser.add_argument("--rolls", type=positive_int, default=10_000,
                        help="number of rolls (default 10000)")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--csv", metavar="PATH", help="write results to CSV")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    if args.rolls > 5_000_000:
        print("Please choose --rolls <= 5,000,000.")
        return 2

    rng = random.Random(args.seed)
    counts = simulate(args.rolls, args.dice, args.sides, rng)
    totals = sorted(counts)
    total_rolls = sum(counts.values())
    mean = sum(value * count for value, count in counts.items()) / total_rolls
    expected = args.dice * (args.sides + 1) / 2

    # Population standard deviation of the observed totals.
    variance = sum(count * (value - mean) ** 2 for value, count in counts.items()) / total_rolls
    std_dev = variance ** 0.5
    most_common, most_count = counts.most_common(1)[0]

    print("=" * 62)
    print(f"DICE SIMULATOR: {args.dice}d{args.sides}, {total_rolls:,} rolls, seed={args.seed}")
    print("=" * 62)
    print(f"Observed mean      : {mean:.4f}   (expected {expected:.4f})")
    print(f"Observed std. dev. : {std_dev:.4f}")
    print(f"Minimum / maximum  : {min(totals)} / {max(totals)}")
    print(f"Most common total  : {most_common} ({most_count:,} times, "
          f"{100 * most_count / total_rolls:.2f}%)")
    print(f"Distinct totals    : {len(totals)} "
          f"(expected {args.dice * (args.sides - 1) + 1})")
    print()
    print(f"{'Sum':>4}  {'Count':>8}  {'Percent':>8}  Histogram")
    print("-" * 62)
    for value in totals:
        count = counts[value]
        percent = 100 * count / total_rolls
        bar = histogram(count, most_count)
        print(f"{value:>4}  {count:>8,}  {percent:>7.2f}%  {bar}")

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["sum", "count", "percent"])
                for value in totals:
                    count = counts[value]
                    writer.writerow([value, count, f"{100 * count / total_rolls:.4f}"])
        except OSError as error:
            print(f"\nCould not write CSV: {error}")
            return 1
        print(f"\nResults written to {args.csv}")
    return 0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        raise SystemExit(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
