#!/usr/bin/env python3
"""Generate strong random passwords or diceware-style passphrases.

Randomness comes from the `secrets` module. Passwords guarantee at least
one character from every enabled class (when the length allows it), and
ambiguous characters such as 0/O and 1/l can be removed. The estimated
entropy is printed to stderr so stdout stays pipe-friendly.

Usage:
    python password_generator.py
    python password_generator.py --length 24 --count 5
    python password_generator.py --length 20 --exclude-ambiguous
    python password_generator.py --passphrase --words 5 --separator "-"
    python password_generator.py --length 32 --json
"""

from __future__ import annotations

import argparse
import json
import math
import secrets
import string
import sys
from typing import Sequence

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
AMBIGUOUS = "Il1O0o|`'\""

WORDS = """
    amber anchor apple arrow autumn badge bamboo basket beacon breezy bridge
    bright bronze bubble cable cactus camera candle canyon carbon castle
    cedar cherry circle citrus clover cobalt comet copper coral cosmic cotton
    crimson crystal daisy dawn delta desert diamond dolphin dragon drift
    eagle earth ember emerald falcon feather fern field flame flint forest
    fossil frost galaxy garden glacier globe golden granite grape harbor
    hazel heron honey horizon island ivory jade jasmine jungle juniper kettle
    lagoon lantern lava lemon lilac linen lunar maple marble meadow meteor
    mint mirror monsoon moss mountain nectar nickel noble north oak ocean
    olive onyx opal orange orbit orchid otter pearl pebble pepper pine planet
    plum polar pond prairie prism quartz quiet rabbit radar raven reef river
    robin rocket ruby saffron sage salmon sand sapphire sea shadow silver
    sky solar spark spruce star stone storm summit sunset swift temple thunder
    tiger timber topaz trail tulip tundra turquoise valley velvet violet
    walnut willow window winter wolf yellow zenith zephyr
""".split()


def build_pools(
    *,
    use_lower: bool,
    use_upper: bool,
    use_digits: bool,
    use_symbols: bool,
    exclude_chars: str,
) -> list[str]:
    """Return one character set per enabled class, with exclusions applied."""
    pools: list[str] = []
    for enabled, characters in (
        (use_lower, LOWER),
        (use_upper, UPPER),
        (use_digits, DIGITS),
        (use_symbols, SYMBOLS),
    ):
        if not enabled:
            continue
        cleaned = "".join(ch for ch in characters if ch not in exclude_chars)
        if not cleaned:
            raise ValueError("exclusions removed every character from a class")
        pools.append(cleaned)
    if not pools:
        raise ValueError("at least one character class must be enabled")
    return pools


def generate_password(length: int, pools: Sequence[str]) -> str:
    """Generate a password containing at least one character per pool."""
    required = [secrets.choice(pool) for pool in pools]
    combined = "".join(pools)
    remaining = [secrets.choice(combined) for _ in range(length - len(required))]
    characters = required + remaining
    # Fisher-Yates shuffle with cryptographic randomness.
    for index in range(len(characters) - 1, 0, -1):
        swap = secrets.randbelow(index + 1)
        characters[index], characters[swap] = characters[swap], characters[index]
    return "".join(characters)


def generate_passphrase(words: int, separator: str, capitalize: bool) -> str:
    """Pick *words* random words from the built-in word list."""
    chosen = [secrets.choice(WORDS) for _ in range(words)]
    if capitalize:
        chosen = [word.capitalize() for word in chosen]
    return separator.join(chosen)


def password_entropy(length: int, pools: Sequence[str]) -> float:
    """Approximate entropy in bits for a uniformly generated password."""
    return length * math.log2(sum(len(pool) for pool in pools))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate random passwords or word-based passphrases.",
    )
    parser.add_argument("--length", type=int, default=16, metavar="N",
                        help="password length (default: 16)")
    parser.add_argument("--count", type=int, default=1, metavar="N",
                        help="number of secrets to generate (default: 1)")
    parser.add_argument("--no-lower", action="store_true", help="exclude a-z")
    parser.add_argument("--no-upper", action="store_true", help="exclude A-Z")
    parser.add_argument("--no-digits", action="store_true", help="exclude 0-9")
    parser.add_argument("--no-symbols", action="store_true", help="exclude punctuation")
    parser.add_argument("--exclude-ambiguous", action="store_true",
                        help="remove look-alike characters such as O/0 and l/1")
    parser.add_argument("--exclude", default="", metavar="CHARS",
                        help="extra characters to remove")
    parser.add_argument("--passphrase", action="store_true",
                        help="generate word-based passphrases instead")
    parser.add_argument("--words", type=int, default=5, metavar="N",
                        help="words per passphrase (default: 5)")
    parser.add_argument("--separator", default="-",
                        help="passphrase separator (default: -)")
    parser.add_argument("--capitalize", action="store_true",
                        help="capitalise each passphrase word")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="print results as JSON")
    args = parser.parse_args(argv)

    if not 4 <= args.length <= 256:
        parser.error("--length must be between 4 and 256")
    if not 1 <= args.count <= 100:
        parser.error("--count must be between 1 and 100")
    if not 2 <= args.words <= 12:
        parser.error("--words must be between 2 and 12")
    if not 0 <= len(args.separator) <= 3:
        parser.error("--separator must be at most 3 characters")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.passphrase:
        phrases = [
            generate_passphrase(args.words, args.separator, args.capitalize)
            for _ in range(args.count)
        ]
        bits = args.words * math.log2(len(WORDS))
        if args.as_json:
            print(json.dumps(
                {"passphrases": phrases, "entropy_bits": round(bits, 1),
                 "word_count": len(WORDS)},
                ensure_ascii=False, indent=2,
            ))
        else:
            for phrase in phrases:
                print(phrase)
            print(
                f"entropy: ~{bits:.1f} bits ({len(WORDS)}-word list, "
                f"{args.words} words)",
                file=sys.stderr,
            )
        return 0

    exclusions = args.exclude
    if args.exclude_ambiguous:
        exclusions += AMBIGUOUS
    try:
        pools = build_pools(
            use_lower=not args.no_lower,
            use_upper=not args.no_upper,
            use_digits=not args.no_digits,
            use_symbols=not args.no_symbols,
            exclude_chars=exclusions,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.length < len(pools):
        print(
            f"error: length {args.length} is too short for {len(pools)} enabled "
            "character classes",
            file=sys.stderr,
        )
        return 1

    passwords = [generate_password(args.length, pools) for _ in range(args.count)]
    bits = password_entropy(args.length, pools)
    pool_size = sum(len(pool) for pool in pools)

    if args.as_json:
        print(json.dumps(
            {"passwords": passwords, "entropy_bits": round(bits, 1),
             "pool_size": pool_size},
            ensure_ascii=False, indent=2,
        ))
    else:
        for password in passwords:
            print(password)
        print(
            f"entropy: ~{bits:.1f} bits (length {args.length}, pool {pool_size})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
