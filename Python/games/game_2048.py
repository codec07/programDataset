"""2048 (tkinter).

Rules
-----
Slide all tiles on a 4x4 grid with the arrow keys. Tiles with the same number
merge into their sum when they collide; each move adds a new 2 or 4 tile.
Reach the 2048 tile to win, but you may keep playing for a higher score.
The game ends when the board is full and no merges remain.

Controls
--------
* Arrow keys or W A S D - slide tiles
* Enter                 - continue after reaching 2048
* R                     - restart
* Esc                   - quit

Run
---
    python game_2048.py
"""

from __future__ import annotations

import random
import tkinter as tk

SIZE = 4
CELL = 100
GAP = 12
HEADER = 86
BOARD_PX = SIZE * CELL + (SIZE + 1) * GAP
WIDTH, HEIGHT = BOARD_PX, BOARD_PX + HEADER

BACKGROUND = "#faf8ef"
BOARD_BG = "#bbada0"
EMPTY = "#cdc1b4"
TEXT_DARK = "#776e65"
TEXT_LIGHT = "#f9f6f2"
TILE_COLORS = {
    2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563",
    32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72", 256: "#edcc61",
    512: "#edc850", 1024: "#edc53f", 2048: "#edc22e",
}


class Game2048:
    """Grid, merging and scoring. No tkinter dependency."""

    def __init__(self, size: int = SIZE, rng: random.Random | None = None) -> None:
        self.size = size
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.grid: list[list[int]] = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.continue_after_win = False
        self.game_over = False
        self.spawn_tile()
        self.spawn_tile()

    def empty_cells(self) -> list[tuple[int, int]]:
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if self.grid[r][c] == 0]

    def spawn_tile(self) -> tuple[int, int] | None:
        empty = self.empty_cells()
        if not empty:
            return None
        r, c = self.rng.choice(empty)
        self.grid[r][c] = 4 if self.rng.random() < 0.1 else 2
        return r, c

    def _slide(self, values: list[int]) -> tuple[list[int], int]:
        tiles = [value for value in values if value]
        merged: list[int] = []
        score = 0
        i = 0
        while i < len(tiles):
            if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
                value = tiles[i] * 2
                merged.append(value)
                score += value
                i += 2
            else:
                merged.append(tiles[i])
                i += 1
        merged.extend([0] * (len(values) - len(merged)))
        return merged, score

    def move(self, direction: str) -> bool:
        """Slide in 'left', 'right', 'up' or 'down'. Return True if changed."""
        if self.game_over:
            return False
        before = [row[:] for row in self.grid]
        gained = 0
        n = self.size

        if direction in {"left", "right"}:
            for r in range(n):
                values = self.grid[r][:]
                if direction == "right":
                    values.reverse()
                line, score = self._slide(values)
                if direction == "right":
                    line.reverse()
                self.grid[r] = line
                gained += score
        elif direction in {"up", "down"}:
            for c in range(n):
                values = [self.grid[r][c] for r in range(n)]
                if direction == "down":
                    values.reverse()
                line, score = self._slide(values)
                if direction == "down":
                    line.reverse()
                for r in range(n):
                    self.grid[r][c] = line[r]
                gained += score
        else:
            raise ValueError(f"unknown direction: {direction!r}")

        if self.grid == before:
            return False

        self.score += gained
        if any(value >= 2048 for row in self.grid for value in row):
            self.won = True
        self.spawn_tile()
        self.game_over = not self.empty_cells() and not self._merges_available()
        return True

    def _merges_available(self) -> bool:
        for r in range(self.size):
            for c in range(self.size):
                value = self.grid[r][c]
                if c + 1 < self.size and value == self.grid[r][c + 1]:
                    return True
                if r + 1 < self.size and value == self.grid[r + 1][c]:
                    return True
        return False

    def max_tile(self) -> int:
        return max(max(row) for row in self.grid)


class Game2048App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("2048")
        self.root.resizable(False, False)
        self.game = Game2048(rng=random.Random())
        self.best = 0

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg=BACKGROUND, highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<Key>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()

    def close(self) -> None:
        self.root.destroy()

    def restart(self) -> None:
        self.game = Game2048(rng=random.Random())
        self.draw()

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        directions = {
            "left": "left", "a": "left",
            "right": "right", "d": "right",
            "up": "up", "w": "up",
            "down": "down", "s": "down",
        }
        if key in directions:
            self.game.move(directions[key])
        elif key == "return" and self.game.won:
            self.game.continue_after_win = True
        elif key == "r":
            self.restart()
        elif key == "escape":
            self.close()
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        self.best = max(self.best, self.game.score)
        self.canvas.create_text(20, 22, anchor="nw", text="2048",
                                fill=TEXT_DARK, font=("Segoe UI", 30, "bold"))
        self.canvas.create_text(20, 62, anchor="nw",
                                text="Join the tiles, reach 2048!",
                                fill=TEXT_DARK, font=("Segoe UI", 10))
        self.canvas.create_text(WIDTH - 20, 22, anchor="ne",
                                text=f"SCORE\n{self.game.score}",
                                fill=TEXT_DARK, font=("Consolas", 14, "bold"),
                                justify="right")
        self.canvas.create_text(WIDTH - 130, 22, anchor="ne",
                                text=f"BEST\n{self.best}",
                                fill=TEXT_DARK, font=("Consolas", 14, "bold"),
                                justify="right")

        top = HEADER
        self.canvas.create_rectangle(GAP, top, WIDTH - GAP, top + BOARD_PX,
                                     fill=BOARD_BG, outline="")
        for r in range(SIZE):
            for c in range(SIZE):
                value = self.game.grid[r][c]
                x = GAP + c * (CELL + GAP)
                y = top + GAP + r * (CELL + GAP)
                fill = TILE_COLORS.get(value, "#3c3a32") if value else EMPTY
                self.canvas.create_rectangle(x, y, x + CELL, y + CELL,
                                             fill=fill, outline="")
                if value:
                    color = TEXT_DARK if value <= 4 else TEXT_LIGHT
                    size = 34 if value < 100 else 28 if value < 1000 else 23
                    self.canvas.create_text(x + CELL / 2, y + CELL / 2,
                                            text=str(value), fill=color,
                                            font=("Segoe UI", size, "bold"))

        if self.game.won and not self.game.continue_after_win:
            self.overlay("YOU WIN!", "Press Enter to keep playing, R to restart")
        elif self.game.game_over:
            self.overlay("GAME OVER", "Press R to restart")

    def overlay(self, title: str, subtitle: str) -> None:
        top = HEADER
        self.canvas.create_rectangle(GAP, top, WIDTH - GAP, top + BOARD_PX,
                                     fill="#faf8ef", stipple="gray50", outline="")
        self.canvas.create_text(WIDTH / 2, top + BOARD_PX / 2 - 20, text=title,
                                fill=TEXT_DARK, font=("Segoe UI", 32, "bold"))
        self.canvas.create_text(WIDTH / 2, top + BOARD_PX / 2 + 26, text=subtitle,
                                fill=TEXT_DARK, font=("Segoe UI", 11))


def main() -> None:
    root = tk.Tk()
    Game2048App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
