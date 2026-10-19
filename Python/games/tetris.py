"""Tetris (tkinter).

Rules
-----
Seven tetromino shapes fall onto a 10x20 board. Move and rotate them to fill
complete horizontal lines; completed lines disappear and score points. The
game ends when a new piece cannot enter the board. Speed increases every ten
lines cleared.

Scoring
-------
1 line = 100, 2 = 300, 3 = 500, 4 = 800, multiplied by the current level.
Soft drop earns 1 point per row, hard drop earns 2 per row.

Controls
--------
* Left / Right  - move
* Down          - soft drop
* Up or X       - rotate clockwise
* Z             - rotate counter-clockwise
* Space         - hard drop
* P             - pause / resume
* R             - restart
* Esc           - quit

Run
---
    python tetris.py
"""

from __future__ import annotations

import random
import tkinter as tk

COLS, ROWS = 10, 20
CELL = 30
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
PANEL_W = 190
WIDTH, HEIGHT = BOARD_W + PANEL_W, BOARD_H
FRAME_MS = 16
PIECES = ("I", "O", "T", "S", "Z", "J", "L")
COLORS = {
    "I": "#00bcd4", "O": "#fdd835", "T": "#ab47bc", "S": "#66bb6a",
    "Z": "#ef5350", "J": "#42a5f5", "L": "#ffa726",
}
BASE_SHAPES = {
    "I": [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    "S": [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    "Z": [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
    "J": [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
    "L": [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
}


def rotate(matrix: list[list[int]]) -> list[list[int]]:
    """Rotate a square matrix 90 degrees clockwise."""
    return [list(row) for row in zip(*matrix[::-1])]


def build_rotations() -> dict[str, list[list[list[int]]]]:
    result: dict[str, list[list[list[int]]]] = {}
    for name, base in BASE_SHAPES.items():
        states: list[list[list[int]]] = []
        current = base
        for _ in range(4):
            states.append(current)
            current = rotate(current)
        result[name] = states
    return result


ROTATIONS = build_rotations()


class TetrisGame:
    """Board and piece logic with no tkinter dependency."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.board: list[list[str | None]] = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.paused = False
        self.game_over = False
        self.bag: list[str] = []
        self.next_name = self._draw_from_bag()
        self.name = ""
        self.rotation = 0
        self.x = 0
        self.y = 0
        self.spawn()

    def _draw_from_bag(self) -> str:
        if not self.bag:
            self.bag = list(PIECES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self) -> None:
        self.name = self.next_name
        self.next_name = self._draw_from_bag()
        self.rotation = 0
        shape = ROTATIONS[self.name][0]
        self.x = (COLS - len(shape[0])) // 2
        self.y = 0
        if not self.can_place(self.x, self.y, self.rotation):
            self.game_over = True

    def cells(self, x: int | None = None, y: int | None = None,
              rotation: int | None = None) -> list[tuple[int, int]]:
        shape = ROTATIONS[self.name][self.rotation if rotation is None else rotation % 4]
        px = self.x if x is None else x
        py = self.y if y is None else y
        return [(px + col, py + row)
                for row, line in enumerate(shape)
                for col, value in enumerate(line) if value]

    def can_place(self, x: int, y: int, rotation: int,
                  name: str | None = None) -> bool:
        name = name or self.name
        shape = ROTATIONS[name][rotation % 4]
        for row, line in enumerate(shape):
            for col, value in enumerate(line):
                if not value:
                    continue
                bx, by = x + col, y + row
                if bx < 0 or bx >= COLS or by >= ROWS:
                    return False
                if by >= 0 and self.board[by][bx] is not None:
                    return False
        return True

    def move(self, dx: int) -> bool:
        if self.game_over or self.paused:
            return False
        if self.can_place(self.x + dx, self.y, self.rotation):
            self.x += dx
            return True
        return False

    def rotate_piece(self, clockwise: bool = True) -> bool:
        if self.game_over or self.paused:
            return False
        new_rotation = (self.rotation + (1 if clockwise else -1)) % 4
        for kick in (0, -1, 1, -2, 2):
            if self.can_place(self.x + kick, self.y, new_rotation):
                self.x += kick
                self.rotation = new_rotation
                return True
        return False

    def soft_drop(self, award: bool = True) -> bool:
        """Move down one row. Return False if the piece locked."""
        if self.game_over or self.paused:
            return False
        if self.can_place(self.x, self.y + 1, self.rotation):
            self.y += 1
            if award:
                self.score += 1
            return True
        self.lock()
        return False

    def hard_drop(self) -> None:
        if self.game_over or self.paused:
            return
        distance = 0
        while self.can_place(self.x, self.y + 1, self.rotation):
            self.y += 1
            distance += 1
        self.score += distance * 2
        self.lock()

    def lock(self) -> None:
        for bx, by in self.cells():
            if by < 0:
                self.game_over = True
                return
            self.board[by][bx] = self.name
        cleared = self.clear_lines()
        if cleared:
            self.score += (0, 100, 300, 500, 800)[cleared] * self.level
            self.lines += cleared
            self.level = 1 + self.lines // 10
        if not self.game_over:
            self.spawn()

    def clear_lines(self) -> int:
        remaining = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(remaining)
        if cleared:
            self.board = [[None] * COLS for _ in range(cleared)] + remaining
        return cleared


class TetrisApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tetris")
        self.root.resizable(False, False)
        self.game = TetrisGame(rng=random.Random())
        self.drop_accumulator = 0.0
        self.job: str | None = None

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="#0d1117", highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.schedule()
        self.draw()

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.root.destroy()

    def schedule(self) -> None:
        self.job = self.root.after(FRAME_MS, self.tick)

    def gravity_interval(self) -> int:
        return max(90, 620 - (self.game.level - 1) * 55)

    def tick(self) -> None:
        self.job = None
        if not self.game.paused and not self.game.game_over:
            self.drop_accumulator += FRAME_MS
            interval = self.gravity_interval()
            while self.drop_accumulator >= interval:
                self.drop_accumulator -= interval
                self.game.soft_drop(award=False)
                if self.game.game_over:
                    break
        self.draw()
        self.schedule()

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        game = self.game
        if key == "left":
            game.move(-1)
        elif key == "right":
            game.move(1)
        elif key == "down":
            game.soft_drop()
        elif key in {"up", "x"}:
            game.rotate_piece(True)
        elif key == "z":
            game.rotate_piece(False)
        elif key == "space":
            game.hard_drop()
        elif key == "p" and not game.game_over:
            game.paused = not game.paused
        elif key == "r":
            self.game = TetrisGame(rng=random.Random())
            self.drop_accumulator = 0.0
        elif key == "escape":
            self.close()
        self.draw()

    def draw_block(self, x: int, y: int, color: str, size: int = CELL) -> None:
        left, top = x * size, y * size
        self.canvas.create_rectangle(left, top, left + size, top + size,
                                     fill=color, outline="#0d1117", width=1)
        self.canvas.create_rectangle(left + 3, top + 3, left + size - 3, top + 6,
                                     fill="#ffffff", outline="", stipple="gray50")

    def draw(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, BOARD_W, BOARD_H,
                                     fill="#161b22", outline="#30363d")
        for x in range(COLS + 1):
            self.canvas.create_line(x * CELL, 0, x * CELL, BOARD_H,
                                    fill="#21262d")
        for y in range(ROWS + 1):
            self.canvas.create_line(0, y * CELL, BOARD_W, y * CELL,
                                    fill="#21262d")

        for row in range(ROWS):
            for col in range(COLS):
                name = self.game.board[row][col]
                if name:
                    self.draw_block(col, row, COLORS[name])

        if not self.game.game_over:
            for bx, by in self.game.cells():
                if by >= 0:
                    self.draw_block(bx, by, COLORS[self.game.name])

        panel_x = BOARD_W + 22
        self.canvas.create_text(panel_x, 24, anchor="nw", text="SCORE",
                                fill="#8b949e", font=("Consolas", 12))
        self.canvas.create_text(panel_x, 42, anchor="nw", text=str(self.game.score),
                                fill="#e6edf3", font=("Consolas", 22, "bold"))
        self.canvas.create_text(panel_x, 104, anchor="nw",
                                text=f"LEVEL {self.game.level}   LINES {self.game.lines}",
                                fill="#e6edf3", font=("Consolas", 11))
        self.canvas.create_text(panel_x, 150, anchor="nw", text="NEXT",
                                fill="#8b949e", font=("Consolas", 12))

        shape = ROTATIONS[self.game.next_name][0]
        mini = 22
        blocks = [(c, r) for r, line in enumerate(shape)
                  for c, v in enumerate(line) if v]
        if blocks:
            min_c = min(c for c, _ in blocks)
            min_r = min(r for _, r in blocks)
            for c, r in blocks:
                left = panel_x + (c - min_c) * mini
                top = 176 + (r - min_r) * mini
                self.canvas.create_rectangle(left, top, left + mini, top + mini,
                                             fill=COLORS[self.game.next_name],
                                             outline="#0d1117")

        self.canvas.create_text(panel_x, 300, anchor="nw",
                                text="← →  move\n↓    soft drop\n↑/X  rotate\nZ    rotate ccw\n"
                                     "SPACE hard drop\nP    pause\nR    restart",
                                fill="#8b949e", font=("Consolas", 11))
        if self.game.paused:
            self.canvas.create_text(BOARD_W / 2, BOARD_H / 2, text="PAUSED",
                                    fill="#ffeb3b", font=("Segoe UI", 28, "bold"))
        if self.game.game_over:
            self.canvas.create_rectangle(0, BOARD_H / 2 - 70, BOARD_W,
                                         BOARD_H / 2 + 70, fill="#000000",
                                         outline="#ffeb3b", width=2)
            self.canvas.create_text(BOARD_W / 2, BOARD_H / 2 - 30, text="GAME OVER",
                                    fill="#ffeb3b", font=("Segoe UI", 26, "bold"))
            self.canvas.create_text(BOARD_W / 2, BOARD_H / 2 + 10,
                                    text=f"Score {self.game.score}",
                                    fill="#e6edf3", font=("Consolas", 15))
            self.canvas.create_text(BOARD_W / 2, BOARD_H / 2 + 40,
                                    text="Press R", fill="#8b949e",
                                    font=("Segoe UI", 13))


def main() -> None:
    root = tk.Tk()
    TetrisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
