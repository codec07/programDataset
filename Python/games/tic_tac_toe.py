"""Tic-Tac-Toe (terminal).

Rules
-----
Players alternate placing their mark (X or O) in an empty cell of a 3x3
board. The first player to fill a row, column or diagonal with their own
mark wins. If all nine cells are filled with no winner, the game is a draw.

Modes
-----
1. Two humans on the same keyboard.
2. Human (X) versus an unbeatable computer (O) using minimax.

Controls
--------
Enter a number from 1 to 9 to place your mark (the keypad layout is shown).
Enter ``q`` to quit. Ctrl+C / Ctrl+D also exit cleanly.

Run
---
    python tic_tac_toe.py
"""

from __future__ import annotations

WIN_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # columns
    (0, 4, 8), (2, 4, 6),              # diagonals
)


class Board:
    """Mutable 3x3 tic-tac-toe board stored as a flat list of nine cells."""

    def __init__(self) -> None:
        self.cells: list[str] = [" "] * 9

    def clone(self) -> "Board":
        copy = Board()
        copy.cells = self.cells.copy()
        return copy

    def available(self) -> list[int]:
        """Return the indices of all empty cells."""
        return [i for i, cell in enumerate(self.cells) if cell == " "]

    def play(self, index: int, mark: str) -> bool:
        """Place ``mark`` at ``index``. Return False if the move is illegal."""
        if index < 0 or index > 8 or self.cells[index] != " ":
            return False
        self.cells[index] = mark
        return True

    def winner(self) -> str | None:
        """Return 'X', 'O', or None if nobody has three in a row yet."""
        for a, b, c in WIN_LINES:
            if self.cells[a] != " " and self.cells[a] == self.cells[b] == self.cells[c]:
                return self.cells[a]
        return None

    def full(self) -> bool:
        return " " not in self.cells

    def game_over(self) -> bool:
        return self.winner() is not None or self.full()

    def render(self) -> str:
        """Return a printable board; empty cells show their keypad number."""
        labels = [cell if cell != " " else str(i + 1) for i, cell in enumerate(self.cells)]
        rows = []
        for row in range(3):
            start = row * 3
            rows.append(f" {labels[start]} | {labels[start + 1]} | {labels[start + 2]} ")
            if row < 2:
                rows.append("---+---+---")
        return "\n".join(rows)


def minimax(board: Board, ai_mark: str, human_mark: str, depth: int = 0,
            alpha: int = -100, beta: int = 100) -> int:
    """Score a position for ``ai_mark``; higher is better for the computer."""
    win = board.winner()
    if win == ai_mark:
        return 10 - depth          # prefer the fastest possible win
    if win == human_mark:
        return depth - 10          # prefer the slowest possible loss
    if board.full():
        return 0

    if depth % 2 == 0:             # AI to move
        best = -100
        for move in board.available():
            board.cells[move] = ai_mark
            score = minimax(board, ai_mark, human_mark, depth + 1, alpha, beta)
            board.cells[move] = " "
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best

    best = 100
    for move in board.available():
        board.cells[move] = human_mark
        score = minimax(board, ai_mark, human_mark, depth + 1, alpha, beta)
        board.cells[move] = " "
        best = min(best, score)
        beta = min(beta, best)
        if beta <= alpha:
            break
    return best


def computer_move(board: Board, ai_mark: str, human_mark: str) -> int:
    """Return the index of the computer's best move."""
    best_score = -100
    best_move = board.available()[0]
    for move in board.available():
        board.cells[move] = ai_mark
        score = minimax(board, ai_mark, human_mark, depth=1)
        board.cells[move] = " "
        if score > best_score:
            best_score = score
            best_move = move
    return best_move


def parse_move(text: str, board: Board) -> int | None:
    """Convert user input to a zero-based cell index, or None if invalid."""
    text = text.strip()
    if not text.isdigit():
        return None
    index = int(text) - 1
    if index not in board.available():
        return None
    return index


def ask_move(board: Board, mark: str) -> int:
    while True:
        try:
            raw = input(f"Player {mark}, choose a cell (1-9, q to quit): ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            raise SystemExit(0)
        if raw.strip().lower() in {"q", "quit", "exit"}:
            print("Goodbye!")
            raise SystemExit(0)
        move = parse_move(raw, board)
        if move is not None:
            return move
        print("Invalid move. Pick an empty cell numbered 1-9.")


def play_round(two_players: bool) -> str:
    """Play one game and return the result: 'X', 'O' or 'draw'."""
    board = Board()
    mark = "X"
    while not board.game_over():
        print("\n" + board.render() + "\n")
        if not two_players and mark == "O":
            move = computer_move(board, "O", "X")
            print(f"Computer plays cell {move + 1}.")
        else:
            move = ask_move(board, mark)
        board.play(move, mark)
        mark = "O" if mark == "X" else "X"

    print("\n" + board.render() + "\n")
    winner = board.winner()
    if winner:
        print(f"*** Player {winner} wins! ***")
        return winner
    print("*** It's a draw. ***")
    return "draw"


def main() -> None:
    print("=" * 40)
    print("        TIC-TAC-TOE")
    print("=" * 40)
    print("Enter 1-9 using the numeric keypad layout:")
    print(" 1 | 2 | 3\n---+---+---\n 4 | 5 | 6\n---+---+---\n 7 | 8 | 9")
    while True:
        try:
            mode = input("\nChoose mode: [1] two players  [2] vs computer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return
        if mode in {"1", "2"}:
            break
        print("Please enter 1 or 2.")

    two_players = mode == "1"
    score = {"X": 0, "O": 0, "draw": 0}
    while True:
        result = play_round(two_players)
        score[result] += 1
        print(f"Score -> X: {score['X']}  O: {score['O']}  Draws: {score['draw']}")
        try:
            again = input("Play again? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nThanks for playing!")
            return
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
