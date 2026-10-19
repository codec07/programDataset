"""Rock, Paper, Scissors (terminal).

Rules
-----
Choose rock, paper or scissors. Rock beats scissors, scissors beats paper,
and paper beats rock. Play a best-of-N match against the computer; ties are
replayed and do not count as a round. The first side to win the majority of
rounds takes the match.

Controls
--------
Type ``rock``, ``paper`` or ``scissors`` (or ``r``, ``p``, ``s``).
Type ``q`` to quit. Ctrl+C / Ctrl+D exit cleanly.

Run
---
    python rock_paper_scissors.py
"""

from __future__ import annotations

import random

CHOICES = ("rock", "paper", "scissors")
SHORT = {"r": "rock", "p": "paper", "s": "scissors"}
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
ART = {
    "rock": """
    _______
---'   ____)
      (_____)
      (_____)
      (____)
---.__(___)
""",
    "paper": """
     _______
---'    ____)
       ______)
      _______)
     _______)
---.__________)
""",
    "scissors": """
    _______
---'   ____)____
          ______)
       __________)
      (____)
---.__(___)
""",
}


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def parse_choice(raw: str) -> str | None:
    text = raw.strip().lower()
    if text in SHORT:
        return SHORT[text]
    if text in CHOICES:
        return text
    return None


def judge(player: str, computer: str) -> int:
    """Return 1 for a player win, -1 for a loss and 0 for a tie."""
    if player == computer:
        return 0
    return 1 if BEATS[player] == computer else -1


def choose_rounds() -> int:
    while True:
        raw = read_line("Best of how many rounds? [3/5/7]: ").strip()
        if raw in {"3", "5", "7"}:
            return int(raw)
        print("Choose 3, 5 or 7.")


def play_match(rng: random.Random, best_of: int) -> tuple[int, int]:
    needed = best_of // 2 + 1
    wins = losses = 0
    round_no = 0
    while wins < needed and losses < needed:
        round_no += 1
        print(f"\n--- Round {round_no} (first to {needed}) --- score {wins}-{losses}")
        while True:
            raw = read_line("Your move [rock/paper/scissors] (q to quit): ")
            if raw.strip().lower() in {"q", "quit", "exit"}:
                raise SystemExit("Thanks for playing!")
            player = parse_choice(raw)
            if player:
                break
            print("Invalid choice. Enter rock, paper, scissors, r, p or s.")

        computer = rng.choice(CHOICES)
        print(f"\nYou chose {player}:{ART[player]}")
        print(f"Computer chose {computer}:{ART[computer]}")
        result = judge(player, computer)
        if result > 0:
            wins += 1
            print("You win this round!")
        elif result < 0:
            losses += 1
            print("Computer wins this round.")
        else:
            print("It's a tie - replay the round.")

    print(f"\nFinal score: you {wins}, computer {losses}")
    if wins > losses:
        print("*** You win the match! ***")
    else:
        print("*** The computer wins the match. ***")
    return wins, losses


def main() -> None:
    print("=" * 42)
    print("        ROCK, PAPER, SCISSORS")
    print("=" * 42)
    rng = random.Random()
    matches = wins = losses = 0
    while True:
        best_of = choose_rounds()
        w, l = play_match(rng, best_of)
        matches += 1
        wins += w
        losses += l
        print(f"Match record: {wins} round wins, {losses} round losses in {matches} match(es)")
        again = read_line("Play another match? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
