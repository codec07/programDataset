"""Connect Four (terminal).

Rules
-----
Players take turns dropping a token into one of seven columns. Tokens fall to
the lowest free slot. The first player to line up four tokens horizontally,
vertically or diagonally wins. If the board fills with no line of four, the
game is a draw.

You are X and move first. The computer plays O and will take an immediate win,
block your winning move, and otherwise use a positional heuristic.

Controls
--------
Enter a column number from 1 to 7 and press Enter. ``q`` quits.
Ctrl+C / Ctrl+D exit cleanly.

Run
---
    python connect_four.py
"""

from __future__ import annotations

import os
import random
import sys

ROWS, COLS = 6, 7
HUMAN, COMPUTER = "X", "O"
SYMBOLS = {"X": "X", "O": "O", " ": "."}
RESET = "\033[0m"
COLORS = {"X": "\033[91m", "O": "\033[93m", " ": ""}


def enable_ansi() -> bool:
    """Best-effort ANSI support; return True when colours are safe to use."""
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # enables virtual terminal processing on Windows 10+
    return True


class Board:
    def __init__(self, rows: int = ROWS, cols: int = COLS) -> None:
        self.rows, self.cols = rows, cols
        self.grid: list[list[str]] = [[" "] * cols for _ in range(rows)]
        self.last_move: tuple[int, int] | None = None

    def copy(self) -> "Board":
        board = Board(self.rows, self.cols)
        board.grid = [row[:] for row in self.grid]
        board.last_move = self.last_move
        return board

    def legal_moves(self) -> list[int]:
        return [c for c in range(self.cols) if self.grid[0][c] == " "]

    def drop(self, col: int, mark: str) -> int | None:
        """Drop a token; return the landing row or None if the column is full."""
        if col < 0 or col >= self.cols:
            return None
        for row in range(self.rows - 1, -1, -1):
            if self.grid[row][col] == " ":
                self.grid[row][col] = mark
                self.last_move = (row, col)
                return row
        return None

    def full(self) -> bool:
        return all(self.grid[0][c] != " " for c in range(self.cols))

    def winner(self) -> str | None:
        directions = ((0, 1), (1, 0), (1, 1), (1, -1))
        for row in range(self.rows):
            for col in range(self.cols):
                mark = self.grid[row][col]
                if mark == " ":
                    continue
                for dr, dc in directions:
                    end_r = row + 3 * dr
                    end_c = col + 3 * dc
                    if not (0 <= end_r < self.rows and 0 <= end_c < self.cols):
                        continue
                    if all(self.grid[row + i * dr][col + i * dc] == mark
                           for i in range(1, 4)):
                        return mark
        return None

    def winning_columns(self, mark: str) -> list[int]:
        result = []
        for col in self.legal_moves():
            test = self.copy()
            test.drop(col, mark)
            if test.winner() == mark:
                result.append(col)
        return result

    def render(self, colors: bool = False) -> str:
        lines = [" " + "   ".join(str(c + 1) for c in range(self.cols)),
                 " " + "---".join("-" for _ in range(self.cols))]
        for row in range(self.rows):
            cells = []
            for col in range(self.cols):
                mark = self.grid[row][col]
                symbol = SYMBOLS[mark]
                if colors:
                    cells.append(f"{COLORS[mark]}{symbol}{RESET}")
                else:
                    cells.append(symbol)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("+" + "---+" * self.cols)
        return "\n".join(lines)


def evaluate(board: Board, ai: str, human: str) -> int:
    """Heuristic score from the AI's point of view."""
    score = 0
    center = board.cols // 2
    for row in range(board.rows):
        if board.grid[row][center] == ai:
            score += 3
        elif board.grid[row][center] == human:
            score -= 3

    windows: list[list[str]] = []
    for row in range(board.rows):
        for col in range(board.cols):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                end_r, end_c = row + 3 * dr, col + 3 * dc
                if 0 <= end_r < board.rows and 0 <= end_c < board.cols:
                    windows.append([board.grid[row + i * dr][col + i * dc]
                                    for i in range(4)])

    for window in windows:
        ai_count = window.count(ai)
        human_count = window.count(human)
        if ai_count and human_count:
            continue
        if ai_count == 3:
            score += 50
        elif ai_count == 2:
            score += 8
        if human_count == 3:
            score -= 60
        elif human_count == 2:
            score -= 10
    return score


def choose_move(board: Board, rng: random.Random) -> int:
    """Pick a computer column: win, block, then play the best heuristic move."""
    legal = board.legal_moves()
    wins = board.winning_columns(COMPUTER)
    if wins:
        return rng.choice(wins)
    blocks = board.winning_columns(HUMAN)
    if blocks:
        return rng.choice(blocks)

    best_score = -10_000
    best_cols: list[int] = []
    for col in legal:
        test = board.copy()
        test.drop(col, COMPUTER)
        score = evaluate(test, COMPUTER, HUMAN)
        if score > best_score:
            best_score = score
            best_cols = [col]
        elif score == best_score:
            best_cols.append(col)
    return rng.choice(best_cols)


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def play_game(rng: random.Random) -> str:
    """Play one game. Return 'X', 'O' or 'draw'."""
    board = Board()
    colors = enable_ansi()
    turn = HUMAN
    while True:
        print()
        print(board.render(colors))
        winner = board.winner()
        if winner:
            print(f"\n*** {'You win!' if winner == HUMAN else 'Computer wins!'} ***")
            return winner
        if board.full():
            print("\n*** It's a draw. ***")
            return "draw"

        if turn == HUMAN:
            raw = read_line(f"Your turn (X), column 1-{COLS} (q to quit): ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                raise SystemExit("Thanks for playing!")
            if not raw.isdigit() or not 1 <= int(raw) <= COLS:
                print("Enter a column number between 1 and 7.")
                continue
            col = int(raw) - 1
            if col not in board.legal_moves():
                print("That column is full. Pick another.")
                continue
            board.drop(col, HUMAN)
            turn = COMPUTER
        else:
            col = choose_move(board, rng)
            board.drop(col, COMPUTER)
            print(f"Computer drops in column {col + 1}.")
            turn = HUMAN


def main() -> None:
    print("=" * 44)
    print("            CONNECT FOUR")
    print("=" * 44)
    print("You are X. Line up four tokens to win.")
    rng = random.Random()
    score = {"X": 0, "O": 0, "draw": 0}
    while True:
        result = play_game(rng)
        score[result] += 1
        print(f"Score -> You {score['X']}  Computer {score['O']}  Draws {score['draw']}")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
