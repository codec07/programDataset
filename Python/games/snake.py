"""Snake (tkinter).

Rules
-----
Guide the snake around the grid and eat the red food. Each meal makes the
snake one segment longer and awards 10 points. Running into a wall or into
your own body ends the game. Try to fill the whole board!

Controls
--------
* Arrow keys or W A S D - change direction
* Space                 - pause / resume
* R                     - restart
* Esc                   - quit

Run
---
    python snake.py
"""

from __future__ import annotations

import random
import tkinter as tk

COLS, ROWS = 22, 22
CELL = 24
DELAY_MS = 110
START_LENGTH = 3


class SnakeGame:
    """Pure snake logic; no tkinter required."""

    def __init__(self, cols: int = COLS, rows: int = ROWS,
                 rng: random.Random | None = None) -> None:
        self.cols, self.rows = cols, rows
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        cx, cy = self.cols // 2, self.rows // 2
        self.snake: list[tuple[int, int]] = [(cx - i, cy) for i in range(START_LENGTH)]
        self.direction: tuple[int, int] = (1, 0)
        self.pending: list[tuple[int, int]] = []
        self.score = 0
        self.alive = True
        self.won = False
        self.food = self.spawn_food()

    def spawn_food(self) -> tuple[int, int]:
        occupied = set(self.snake)
        free = [(x, y) for y in range(self.rows) for x in range(self.cols)
                if (x, y) not in occupied]
        if not free:
            self.won = True
            self.alive = False
            return (-1, -1)
        return self.rng.choice(free)

    def set_direction(self, direction: tuple[int, int]) -> bool:
        """Queue a direction change; ignore reversals and duplicates."""
        base = self.pending[-1] if self.pending else self.direction
        if direction == base:
            return False
        if direction[0] == -base[0] and direction[1] == -base[1]:
            return False
        if len(self.pending) >= 2:
            return False
        self.pending.append(direction)
        return True

    def step(self) -> str:
        """Advance one tick. Return 'ok', 'ate', 'dead' or 'won'."""
        if not self.alive:
            return "dead"
        if self.pending:
            self.direction = self.pending.pop(0)

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if not (0 <= new_head[0] < self.cols and 0 <= new_head[1] < self.rows):
            self.alive = False
            return "dead"
        if new_head in self.snake[:-1]:
            self.alive = False
            return "dead"

        ate = new_head == self.food
        self.snake.insert(0, new_head)
        if ate:
            self.score += 10
            self.food = self.spawn_food()
            if self.won:
                return "won"
            return "ate"
        self.snake.pop()
        return "ok"


class SnakeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Snake")
        self.root.resizable(False, False)
        self.rng = random.Random()
        self.game = SnakeGame(rng=self.rng)
        self.paused = False
        self.started = False
        self.high_score = 0
        self.job: str | None = None

        width, height = COLS * CELL, ROWS * CELL
        self.canvas = tk.Canvas(root, width=width, height=height,
                                bg="#101820", highlightthickness=0)
        self.canvas.pack()
        self.info = tk.Label(root, text="", font=("Consolas", 12), bg="#101820",
                             fg="#e0e0e0", pady=4)
        self.info.pack(fill="x")

        root.bind("<Key>", self.on_key)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()
        self.schedule()

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.root.destroy()

    def restart(self) -> None:
        self.game = SnakeGame(rng=self.rng)
        self.paused = False
        self.started = False
        self.draw()

    def schedule(self) -> None:
        self.job = self.root.after(DELAY_MS, self.tick)

    def tick(self) -> None:
        self.job = None
        if self.started and not self.paused and self.game.alive:
            result = self.game.step()
            if self.game.score > self.high_score:
                self.high_score = self.game.score
            if result == "dead":
                self.started = False
            elif result == "won":
                self.started = False
                self.game.won = True
        self.draw()
        self.schedule()

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        directions = {
            "up": (0, -1), "w": (0, -1),
            "down": (0, 1), "s": (0, 1),
            "left": (-1, 0), "a": (-1, 0),
            "right": (1, 0), "d": (1, 0),
        }
        if key in directions:
            if not self.game.alive:
                return
            if not self.started:
                self.started = True
            self.game.set_direction(directions[key])
        elif key == "space":
            if self.game.alive and self.started:
                self.paused = not self.paused
        elif key == "r":
            self.restart()
        elif key == "escape":
            self.close()

    def draw(self) -> None:
        self.canvas.delete("all")
        for x in range(0, COLS * CELL, CELL):
            self.canvas.create_line(x, 0, x, ROWS * CELL, fill="#18242e")
        for y in range(0, ROWS * CELL, CELL):
            self.canvas.create_line(0, y, COLS * CELL, y, fill="#18242e")

        if self.game.food != (-1, -1):
            fx = self.game.food[0] * CELL + CELL // 2
            fy = self.game.food[1] * CELL + CELL // 2
            self.canvas.create_oval(fx - 8, fy - 8, fx + 8, fy + 8,
                                    fill="#e53935", outline="#ff8a80")

        for index, (x, y) in enumerate(self.game.snake):
            pad = 2
            color = "#66bb6a" if index else "#c8e6c9"
            self.canvas.create_rectangle(
                x * CELL + pad, y * CELL + pad,
                (x + 1) * CELL - pad, (y + 1) * CELL - pad,
                fill=color, outline="#1b5e20",
            )
        hx, hy = self.game.snake[0]
        if self.game.alive:
            for ox, oy in ((7, 7), (15, 7)):
                self.canvas.create_oval(hx * CELL + ox, hy * CELL + oy,
                                        hx * CELL + ox + 4, hy * CELL + oy + 4,
                                        fill="#1b5e20", outline="")

        status = f"Score {self.game.score}   Best {self.high_score}"
        if not self.started and self.game.alive:
            status += "   |  Press an arrow key to start"
        elif self.paused:
            status += "   |  PAUSED (space)"
        elif not self.game.alive:
            status = ("YOU WIN! " if self.game.won else "GAME OVER  ") + status
        self.info.config(text=status)

        if not self.game.alive:
            self.canvas.create_text(
                COLS * CELL // 2, ROWS * CELL // 2,
                text="YOU WIN!" if self.game.won else "GAME OVER",
                fill="#ffeb3b", font=("Segoe UI", 30, "bold"),
            )
            self.canvas.create_text(
                COLS * CELL // 2, ROWS * CELL // 2 + 38,
                text="Press R to restart", fill="#e0e0e0", font=("Segoe UI", 14),
            )
        elif self.paused:
            self.canvas.create_text(
                COLS * CELL // 2, ROWS * CELL // 2,
                text="PAUSED", fill="#ffeb3b", font=("Segoe UI", 30, "bold"),
            )


def main() -> None:
    root = tk.Tk()
    SnakeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
