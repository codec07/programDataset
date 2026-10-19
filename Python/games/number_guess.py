"""Number Guess (terminal).

Rules
-----
The computer chooses a secret whole number in a range. Guess it in as few
tries as possible. After each guess you are told whether the secret is
higher or lower, plus a "temperature" hint based on how close you are:
boiling (within 2%), hot (10%), warm (25%) or cold.

Difficulties
------------
1. Easy   - 1 to 50,   8 tries
2. Normal - 1 to 100,  7 tries
3. Hard   - 1 to 1000, 10 tries

Controls
--------
Type a whole number and press Enter. ``q`` quits. Ctrl+C / Ctrl+D exit.

Run
---
    python number_guess.py
"""

from __future__ import annotations

import random

DIFFICULTIES = {
    "1": ("Easy", 1, 50, 8),
    "2": ("Normal", 1, 100, 7),
    "3": ("Hard", 1, 1000, 10),
}


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def temperature(guess: int, secret: int, low: int, high: int) -> str:
    distance = abs(guess - secret)
    span = max(1, high - low)
    fraction = distance / span
    if distance == 0:
        return "correct"
    if fraction <= 0.02:
        return "BOILING"
    if fraction <= 0.10:
        return "hot"
    if fraction <= 0.25:
        return "warm"
    return "cold"


def choose_difficulty() -> tuple[str, int, int, int]:
    print("\nChoose a difficulty:")
    print("  1. Easy   - 1 to 50,   8 tries")
    print("  2. Normal - 1 to 100,  7 tries")
    print("  3. Hard   - 1 to 1000, 10 tries")
    while True:
        choice = read_line("Difficulty [1/2/3]: ").strip()
        if choice in DIFFICULTIES:
            return DIFFICULTIES[choice]
        print("Enter 1, 2 or 3.")


def play_round(rng: random.Random, name: str, low: int, high: int,
               max_tries: int) -> bool:
    secret = rng.randint(low, high)
    print(f"\n{name}: I picked a number between {low} and {high}.")
    print(f"You have {max_tries} guesses.")

    for attempt in range(1, max_tries + 1):
        while True:
            raw = read_line(f"Guess {attempt}/{max_tries} (q to quit): ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                print(f"The number was {secret}.")
                raise SystemExit("Thanks for playing!")
            if raw.lstrip("-").isdigit():
                guess = int(raw)
                if low <= guess <= high:
                    break
            print(f"Enter a whole number between {low} and {high}.")

        if guess == secret:
            print(f"Correct! You found {secret} in {attempt} guess"
                  f"{'es' if attempt != 1 else ''}.")
            return True

        hint = "higher" if secret > guess else "lower"
        temp = temperature(guess, secret, low, high)
        print(f"{guess} is too {hint} - you are {temp}.")

    print(f"Out of guesses. The number was {secret}.")
    return False


def main() -> None:
    print("=" * 42)
    print("            NUMBER GUESS")
    print("=" * 42)
    rng = random.Random()
    wins = losses = 0
    while True:
        name, low, high, tries = choose_difficulty()
        if play_round(rng, name, low, high, tries):
            wins += 1
        else:
            losses += 1
        print(f"Record: {wins} wins, {losses} losses")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
