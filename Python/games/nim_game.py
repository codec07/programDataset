"""Nim (terminal).

Rules
-----
Three piles start with 3, 4 and 5 stones. On your turn remove any positive
number of stones from exactly one pile. The player who takes the last stone
wins (normal play). You move first against a computer that plays perfectly.

Winning strategy (spoiler): leave the opponent a position where the bitwise
XOR of the pile sizes is zero.

Controls
--------
Enter two numbers, the pile and how many stones to remove, e.g. ``2 3``
(remove 3 stones from pile 2). ``q`` quits. Ctrl+C / Ctrl+D exit.

Run
---
    python nim_game.py
"""

from __future__ import annotations


def xor_value(piles: list[int]) -> int:
    result = 0
    for pile in piles:
        result ^= pile
    return result


def best_move(piles: list[int]) -> tuple[int, int]:
    """Return (pile index, stones) for the optimal computer move."""
    target = xor_value(piles)
    if target:
        for index, pile in enumerate(piles):
            wanted = pile ^ target
            if 0 <= wanted < pile:
                return index, pile - wanted
    # Already losing: take one stone from the largest pile and hope.
    index = max(range(len(piles)), key=lambda i: piles[i])
    return index, 1


def render(piles: list[int]) -> str:
    lines = []
    for number, count in enumerate(piles, start=1):
        stones = " ".join("O" for _ in range(count)) if count else "(empty)"
        lines.append(f"Pile {number}: {stones}  [{count}]")
    return "\n".join(lines)


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def parse_move(text: str, piles: list[int]) -> tuple[int, int] | None:
    parts = text.replace(",", " ").split()
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    pile, stones = int(parts[0]), int(parts[1])
    if not 1 <= pile <= len(piles):
        return None
    index = pile - 1
    if not 1 <= stones <= piles[index]:
        return None
    return index, stones


def play_round() -> bool:
    """Play one game. Return True when the human wins."""
    piles = [3, 4, 5]
    print("\nNew game. Piles: 3, 4, 5.")
    print("Remove any number of stones from one pile. Take the last stone to win.")

    human_turn = True
    while any(piles):
        print()
        print(render(piles))
        if human_turn:
            while True:
                raw = read_line("Your move (pile count, q to quit): ").strip()
                if raw.lower() in {"q", "quit", "exit"}:
                    raise SystemExit("Thanks for playing!")
                move = parse_move(raw, piles)
                if move is not None:
                    break
                print("Enter two numbers, e.g. '2 3'. The pile must be 1-3 "
                      "and the count must not exceed that pile.")
            index, stones = move
            print(f"You take {stones} from pile {index + 1}.")
        else:
            index, stones = best_move(piles)
            print(f"Computer takes {stones} from pile {index + 1}.")

        piles[index] -= stones
        if not any(piles):
            if human_turn:
                print("\n*** You took the last stone. You win! ***")
                return True
            print("\n*** The computer took the last stone. You lose. ***")
            return False
        human_turn = not human_turn

    return False


def main() -> None:
    print("=" * 44)
    print("                 NIM")
    print("=" * 44)
    print("Normal play: whoever takes the last stone wins.")
    wins = losses = 0
    while True:
        if play_round():
            wins += 1
        else:
            losses += 1
        print(f"\nRecord: {wins} wins, {losses} losses")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
