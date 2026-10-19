"""Battleship (terminal).

Rules
-----
You and the computer each hide a fleet of five ships on a 10x10 grid:

    Carrier (5), Battleship (4), Cruiser (3), Submarine (3), Destroyer (2)

Ships may touch but never overlap. On your turn call a shot such as ``B7``.
The reply is a miss, a hit, or a sunk ship. The computer fires back with a
hunt-and-target strategy. Sink the whole enemy fleet before yours is sunk.

Controls
--------
* Place ships with ``A1 H`` or ``A1 V`` (row letter, column, orientation),
  or type ``r`` to place the current ship randomly.
* Fire with a coordinate like ``C4``. Type ``q`` to quit.
* Ctrl+C / Ctrl+D exit cleanly.

Run
---
    python battleship.py
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

SIZE = 10
SHIPS: tuple[tuple[str, int], ...] = (
    ("Carrier", 5), ("Battleship", 4), ("Cruiser", 3),
    ("Submarine", 3), ("Destroyer", 2),
)
ROW_LABELS = "ABCDEFGHIJ"
SHOT_RE = re.compile(r"^([A-Ja-j])(10|[1-9])$")
PLACE_RE = re.compile(r"^([A-Ja-j])(10|[1-9])\s*([HhVv])$")


@dataclass
class Ship:
    name: str
    size: int
    cells: set[tuple[int, int]] = field(default_factory=set)
    hits: set[tuple[int, int]] = field(default_factory=set)

    @property
    def sunk(self) -> bool:
        return self.size > 0 and len(self.hits) >= self.size


class Fleet:
    """One player's ships and the shots received."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.ships: list[Ship] = [Ship(name, size) for name, size in SHIPS]
        self.misses: set[tuple[int, int]] = set()

    @property
    def occupied(self) -> set[tuple[int, int]]:
        return {cell for ship in self.ships for cell in ship.cells}

    def place_random(self) -> None:
        for ship in self.ships:
            for _ in range(500):
                horizontal = self.rng.random() < 0.5
                row = self.rng.randrange(SIZE)
                col = self.rng.randrange(SIZE)
                cells = self._span(row, col, ship.size, horizontal)
                if cells and self._fits(cells):
                    ship.cells = set(cells)
                    break
            else:
                raise RuntimeError("could not place fleet")

    @staticmethod
    def _span(row: int, col: int, size: int, horizontal: bool) -> list[tuple[int, int]]:
        if horizontal:
            if col + size > SIZE:
                return []
            return [(row, col + i) for i in range(size)]
        if row + size > SIZE:
            return []
        return [(row + i, col) for i in range(size)]

    def _fits(self, cells: list[tuple[int, int]]) -> bool:
        taken = self.occupied
        return all(0 <= r < SIZE and 0 <= c < SIZE and (r, c) not in taken
                   for r, c in cells)

    def place(self, ship: Ship, row: int, col: int, horizontal: bool) -> bool:
        cells = self._span(row, col, ship.size, horizontal)
        if not cells or not self._fits(cells):
            return False
        ship.cells = set(cells)
        return True

    def receive_shot(self, row: int, col: int) -> str:
        cell = (row, col)
        if any(cell in ship.hits for ship in self.ships) or cell in self.misses:
            return "repeat"
        for ship in self.ships:
            if cell in ship.cells:
                ship.hits.add(cell)
                return "sunk" if ship.sunk else "hit"
        self.misses.add(cell)
        return "miss"

    def all_sunk(self) -> bool:
        return all(ship.sunk for ship in self.ships)

    def render(self, reveal_ships: bool, title: str) -> str:
        lines = [f"  {title}", "   " + " ".join(str(c + 1).rjust(2) for c in range(SIZE))]
        for row in range(SIZE):
            parts = []
            for col in range(SIZE):
                cell = (row, col)
                if any(cell in ship.hits for ship in self.ships):
                    parts.append(" X")
                elif cell in self.misses:
                    parts.append(" o")
                elif reveal_ships and cell in self.occupied:
                    parts.append(" S")
                else:
                    parts.append(" ~")
            lines.append(f"{ROW_LABELS[row]}  " + " ".join(parts))
        return "\n".join(lines)


class BattleshipAI:
    """Random hunting with adjacent targeting after a hit."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.tried: set[tuple[int, int]] = set()
        self.targets: list[tuple[int, int]] = []

    def choose(self) -> tuple[int, int]:
        while self.targets:
            cell = self.targets.pop()
            if cell not in self.tried:
                self.tried.add(cell)
                return cell
        candidates = [(r, c) for r in range(SIZE) for c in range(SIZE)
                      if (r, c) not in self.tried]
        cell = self.rng.choice(candidates)
        self.tried.add(cell)
        return cell

    def report(self, cell: tuple[int, int], result: str) -> None:
        if result not in {"hit", "sunk"}:
            return
        row, col = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = row + dr, col + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE and (nr, nc) not in self.tried:
                self.targets.append((nr, nc))


def parse_shot(text: str) -> tuple[int, int] | None:
    match = SHOT_RE.match(text.strip())
    if not match:
        return None
    return ROW_LABELS.index(match.group(1).upper()), int(match.group(2)) - 1


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def setup_player_fleet(rng: random.Random) -> Fleet:
    fleet = Fleet(rng)
    print("\nPlace your ships. Example: B2 H (B2 is the left end of a"
          " horizontal ship).")
    for ship in fleet.ships:
        while True:
            print()
            print(fleet.render(reveal_ships=True, title=f"Your fleet - place {ship.name} ({ship.size})"))
            raw = read_line(f"Place {ship.name} (length {ship.size}) or 'r' for random: ").strip()
            if raw.lower() in {"q", "quit"}:
                raise SystemExit("Thanks for playing!")
            if raw.lower() == "r":
                while True:
                    horizontal = rng.random() < 0.5
                    row, col = rng.randrange(SIZE), rng.randrange(SIZE)
                    if fleet.place(ship, row, col, horizontal):
                        break
                break
            match = PLACE_RE.match(raw)
            if not match:
                print("Use a coordinate and H/V, for example C4 H.")
                continue
            row = ROW_LABELS.index(match.group(1).upper())
            col = int(match.group(2)) - 1
            horizontal = match.group(3).upper() == "H"
            if not fleet.place(ship, row, col, horizontal):
                print("That does not fit there (out of bounds or overlapping).")
                continue
            break
    print()
    print(fleet.render(reveal_ships=True, title="Your fleet is ready"))
    return fleet


def describe(result: str, ship_name: str = "") -> str:
    return {
        "miss": "Miss!",
        "hit": "Hit!",
        "sunk": f"Hit! You sank the {ship_name}!",
        "repeat": "You already fired there. Try again.",
    }[result]


def play_game(rng: random.Random) -> bool:
    """Return True if the human wins."""
    player = setup_player_fleet(rng)
    enemy = Fleet(rng)
    enemy.place_random()
    ai = BattleshipAI(rng)

    # Track which ship was sunk so the player gets a useful message.
    enemy_ship_by_cell = {cell: ship.name for ship in enemy.ships for cell in ship.cells}
    player_ship_by_cell = {cell: ship.name for ship in player.ships for cell in ship.cells}

    print("\nThe enemy fleet is hidden. Call shots like B7.")
    while True:
        print()
        print(enemy.render(reveal_ships=False, title="Enemy waters"))
        print()
        print(player.render(reveal_ships=True, title="Your fleet"))

        # Player's shot
        while True:
            raw = read_line("\nYour shot (e.g. B7, q to quit): ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                raise SystemExit("Thanks for playing!")
            shot = parse_shot(raw)
            if shot is None:
                print("Invalid coordinate. Use A-J plus 1-10, such as B7.")
                continue
            result = enemy.receive_shot(*shot)
            if result == "repeat":
                print("You already fired at that cell.")
                continue
            print(describe(result, enemy_ship_by_cell.get(shot, "")))
            break

        if enemy.all_sunk():
            print("\n" + enemy.render(reveal_ships=True, title="Enemy fleet destroyed"))
            print("*** You win! The enemy fleet is sunk. ***")
            return True

        # Computer's shot
        cell = ai.choose()
        result = player.receive_shot(*cell)
        ai.report(cell, result)
        label = f"{ROW_LABELS[cell[0]]}{cell[1] + 1}"
        if result == "repeat":
            continue
        if result == "miss":
            print(f"Computer fires at {label}: miss.")
        elif result == "hit":
            print(f"Computer fires at {label}: HIT!")
        else:
            print(f"Computer fires at {label}: your {player_ship_by_cell.get(cell, 'ship')} was sunk!")

        if player.all_sunk():
            print("\n" + player.render(reveal_ships=True, title="Your fleet"))
            print("*** Your fleet is sunk. Computer wins. ***")
            return False


def main() -> None:
    print("=" * 46)
    print("               BATTLESHIP")
    print("=" * 46)
    rng = random.Random()
    wins = losses = 0
    while True:
        if play_game(rng):
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
