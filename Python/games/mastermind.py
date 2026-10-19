"""Mastermind (terminal).

Rules
-----
A secret code of four coloured pegs is hidden. You have ten guesses. Each
guess is scored with:

* ``B`` (black) - correct colour in the correct position
* ``W`` (white) - correct colour in the wrong position

Duplicate colours are allowed. For example, if the secret is ``RRGB`` and you
guess ``RGRB``, the score is 2B 2W. Use the scores to deduce the code.

Controls
--------
Enter four colour letters from ``R G B Y O P`` (red, green, blue, yellow,
orange, purple). ``q`` quits. Ctrl+C / Ctrl+D also exit.

Run
---
    python mastermind.py
"""

from __future__ import annotations

import random
from collections import Counter

COLORS = "RGBYOP"
COLOR_NAMES = {
    "R": "red", "G": "green", "B": "blue",
    "Y": "yellow", "O": "orange", "P": "purple",
}
CODE_LENGTH = 4
MAX_GUESSES = 10


def score_guess(secret: str, guess: str) -> tuple[int, int]:
    """Return (exact matches, colour-only matches)."""
    exact = sum(a == b for a, b in zip(secret, guess))
    secret_rest = Counter(a for a, b in zip(secret, guess) if a != b)
    guess_rest = Counter(b for a, b in zip(secret, guess) if a != b)
    partial = sum((secret_rest & guess_rest).values())
    return exact, partial


def format_feedback(exact: int, partial: int) -> str:
    if exact == 0 and partial == 0:
        return "no matches"
    parts = []
    if exact:
        parts.append(f"{exact}B")
    if partial:
        parts.append(f"{partial}W")
    return " ".join(parts)


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def validate_guess(text: str) -> str | None:
    text = text.strip().upper()
    if len(text) != CODE_LENGTH:
        return None
    if any(ch not in COLORS for ch in text):
        return None
    return text


def play_round(rng: random.Random) -> tuple[bool, str, int]:
    """Play one round. Return (won, secret, guesses_used)."""
    secret = "".join(rng.choice(COLORS) for _ in range(CODE_LENGTH))
    print(f"\nI have chosen a secret code of {CODE_LENGTH} pegs.")
    print("Colours: R=red  G=green  B=blue  Y=yellow  O=orange  P=purple")
    print("Feedback: B = right colour and place, W = right colour, wrong place")
    print("Example guess: RGBY")

    for attempt in range(1, MAX_GUESSES + 1):
        while True:
            raw = read_line(f"Guess {attempt}/{MAX_GUESSES} (q to quit): ")
            if raw.strip().lower() in {"q", "quit", "exit"}:
                print("The secret was", secret)
                raise SystemExit(0)
            guess = validate_guess(raw)
            if guess is not None:
                break
            print("Enter exactly four letters from R, G, B, Y, O, P.")

        exact, partial = score_guess(secret, guess)
        print(f"  {guess}  ->  {format_feedback(exact, partial)}")
        if exact == CODE_LENGTH:
            print(f"Solved in {attempt} guess{'es' if attempt != 1 else ''}!")
            return True, secret, attempt

    print(f"Out of guesses. The secret was {secret}.")
    return False, secret, MAX_GUESSES


def main() -> None:
    print("=" * 46)
    print("               MASTERMIND")
    print("=" * 46)
    rng = random.Random()
    wins = losses = 0
    while True:
        won, _, _ = play_round(rng)
        if won:
            wins += 1
        else:
            losses += 1
        print(f"Score: {wins} wins, {losses} losses")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
