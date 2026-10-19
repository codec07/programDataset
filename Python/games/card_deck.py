"""Card Deck and Poker Hand Simulator (simulation).

What it does
------------
Provides a sealed, shuffled 52-card deck and evaluates five-card poker hands.
Running the file deals many random hands and reports how often each category
appears, comparing the observed frequencies with the theoretical values.

The deck only exposes ``draw``/``deal``; its internal order is private, so
callers cannot peek at upcoming cards.

Options
-------
    python card_deck.py
    python card_deck.py --hands 50000 --seed 7
    python card_deck.py --hands 20000 --show 8 --csv poker.csv

CSV columns: ``category,count,percent,expected_percent``.

Run
---
    python card_deck.py --seed 1
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter
from dataclasses import dataclass

SUITS = ("S", "H", "D", "C")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANKS)}
CATEGORY_NAMES = (
    "High card", "One pair", "Two pair", "Three of a kind", "Straight",
    "Flush", "Full house", "Four of a kind", "Straight flush", "Royal flush",
)
EXPECTED_PERCENT = {
    "Royal flush": 0.000154, "Straight flush": 0.00139,
    "Four of a kind": 0.0240, "Full house": 0.1441,
    "Flush": 0.1965, "Straight": 0.3925,
    "Three of a kind": 2.1128, "Two pair": 4.7539,
    "One pair": 42.2569, "High card": 50.1177,
}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Deck:
    """A standard 52-card deck. Order is private; only draw/deal are exposed."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._cards: list[Card] = []
        self.shuffle()

    def shuffle(self) -> None:
        self._cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        if not self._cards:
            raise IndexError("cannot draw from an empty deck")
        return self._cards.pop()

    def deal(self, count: int) -> list[Card]:
        if count < 0 or count > len(self._cards):
            raise ValueError(f"cannot deal {count} cards; {len(self._cards)} remain")
        return [self.draw() for _ in range(count)]

    def __len__(self) -> int:
        return len(self._cards)


def evaluate_five(cards: list[Card]) -> str:
    """Return the poker category name for exactly five cards."""
    if len(cards) != 5:
        raise ValueError("exactly five cards are required")

    values = sorted((RANK_VALUE[card.rank] for card in cards), reverse=True)
    counts = Counter(values)
    groups = sorted(counts.values(), reverse=True)
    flush = len({card.suit for card in cards}) == 1

    unique = sorted(set(values), reverse=True)
    straight_high = 0
    if len(unique) == 5:
        if unique[0] - unique[-1] == 4:
            straight_high = unique[0]
        elif unique == [14, 5, 4, 3, 2]:  # ace-low wheel
            straight_high = 5

    if flush and straight_high:
        return "Royal flush" if straight_high == 14 else "Straight flush"
    if groups == [4, 1]:
        return "Four of a kind"
    if groups == [3, 2]:
        return "Full house"
    if flush:
        return "Flush"
    if straight_high:
        return "Straight"
    if groups == [3, 1, 1]:
        return "Three of a kind"
    if groups == [2, 2, 1]:
        return "Two pair"
    if groups == [2, 1, 1, 1]:
        return "One pair"
    return "High card"


def simulate(hands: int, rng: random.Random,
             sample_count: int = 5) -> tuple[Counter[str], list[list[Card]]]:
    """Deal ``hands`` independent five-card hands and count categories."""
    counts: Counter[str] = Counter()
    samples: list[list[Card]] = []
    for index in range(hands):
        deck = Deck(rng)
        hand = deck.deal(5)
        counts[evaluate_five(hand)] += 1
        if index < sample_count:
            samples.append(hand)
    return counts, samples


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deal poker hands and analyse them.")
    parser.add_argument("--hands", type=positive_int, default=20_000,
                        help="number of five-card hands to deal (default 20000)")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--show", type=positive_int, default=5,
                        help="number of sample hands to print (default 5)")
    parser.add_argument("--csv", metavar="PATH", help="write statistics to CSV")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.hands > 2_000_000:
        raise SystemExit("Please choose --hands <= 2,000,000.")

    rng = random.Random(args.seed)
    counts, samples = simulate(args.hands, rng, args.show)

    print("=" * 68)
    print(f"POKER HAND SIMULATOR: {args.hands:,} hands, seed={args.seed}")
    print("=" * 68)
    for hand in samples[:args.show]:
        print("  " + " ".join(str(card) for card in hand) +
              f"  ->  {evaluate_five(hand)}")
    print()
    print(f"{'Category':<16}{'Count':>9}{'Observed %':>12}{'Expected %':>12}")
    print("-" * 68)

    for category in reversed(CATEGORY_NAMES):
        count = counts.get(category, 0)
        observed = 100 * count / args.hands
        expected = EXPECTED_PERCENT[category]
        print(f"{category:<16}{count:>9,}{observed:>11.4f}%{expected:>11.4f}%")

    print("-" * 68)
    print(f"{'Total':<16}{sum(counts.values()):>9,}")

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["category", "count", "percent", "expected_percent"])
                for category in reversed(CATEGORY_NAMES):
                    count = counts.get(category, 0)
                    writer.writerow([category, count,
                                     f"{100 * count / args.hands:.6f}",
                                     EXPECTED_PERCENT[category]])
        except OSError as error:
            raise SystemExit(f"Could not write CSV: {error}")
        print(f"\nResults written to {args.csv}")


if __name__ == "__main__":
    main()
