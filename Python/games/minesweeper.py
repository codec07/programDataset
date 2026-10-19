"""Minesweeper (tkinter).

Rules
-----
A 10x10 field hides 12 mines. Click a cell to uncover it. The first click is
always safe: mines are placed only after you click. Numbers count the mines
in the eight neighbouring cells. Uncover every safe cell to win. Opening a
mine loses the game.

Controls
--------
* Left click  - reveal a cell (flood-fills when the count is zero)
* Right click - place or remove a flag
* R           - restart with a fresh field
* Esc         - quit
The timer starts on your first reveal.

Run
---
    python minesweeper.py
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass

ROWS, COLS = 10, 10
MINES = 12
CELL = 40
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL

NUMBER_COLORS = {
    1: "#1976d2", 2: "#388e3c", 3: "#d32f2f", 4: "#7b1fa2",
    5: "#ff8f00", 6: "#00838f", 7: "#212121", 8: "#616161",
}


@dataclass
class Cell:
    mine: bool = False
    revealed: bool = False
    flagged: bool = False
    adjacent: int = 0


class Minesweeper:
    """Pure game logic, independent of tkinter."""

    def __init__(self, rows: int = ROWS, cols: int = COLS, mines: int = MINES,
                 rng: random.Random | None = None) -> None:
        if not 0 <= mines < rows * cols:
            raise ValueError("mines must fit on the board")
        self.rows, self.cols, self.mines = rows, cols, mines
        self.rng = rng or random.Random()
        self.grid: list[list[Cell]] = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.placed = False
        self.state = "ready"  # ready | playing | won | lost
        self.revealed_safe = 0

    def neighbours(self, r: int, c: int) -> list[tuple[int, int]]:
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    result.append((nr, nc))
        return result

    def place_mines(self, safe_r: int, safe_c: int) -> None:
        """Place mines, excluding the first clicked cell and its neighbours."""
        forbidden = {(safe_r, safe_c), *self.neighbours(safe_r, safe_c)}
        candidates = [(r, c) for r in range(self.rows) for c in range(self.cols)
                      if (r, c) not in forbidden]
        if self.mines > len(candidates):
            candidates = [(r, c) for r in range(self.rows) for c in range(self.cols)
                          if (r, c) != (safe_r, safe_c)]
        for r, c in self.rng.sample(candidates, self.mines):
            self.grid[r][c].mine = True
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c].adjacent = sum(
                    self.grid[nr][nc].mine for nr, nc in self.neighbours(r, c)
                )
        self.placed = True
        self.state = "playing"

    @property
    def flags(self) -> int:
        return sum(cell.flagged for row in self.grid for cell in row)

    @property
    def mines_left(self) -> int:
        return self.mines - self.flags

    def toggle_flag(self, r: int, c: int) -> None:
        if self.state not in {"ready", "playing"}:
            return
        cell = self.grid[r][c]
        if cell.revealed:
            return
        cell.flagged = not cell.flagged

    def reveal(self, r: int, c: int) -> str:
        """Reveal a cell. Return 'mine', 'ok', or 'ignored'."""
        if self.state not in {"ready", "playing"}:
            return "ignored"
        cell = self.grid[r][c]
        if cell.flagged or cell.revealed:
            return "ignored"
        if not self.placed:
            self.place_mines(r, c)

        if cell.mine:
            cell.revealed = True
            self.state = "lost"
            self._reveal_all_mines()
            return "mine"

        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            current = self.grid[cr][cc]
            if current.revealed or current.flagged:
                continue
            current.revealed = True
            self.revealed_safe += 1
            if current.adjacent == 0:
                stack.extend(self.neighbours(cr, cc))

        if self.revealed_safe == self.rows * self.cols - self.mines:
            self.state = "won"
            for row in self.grid:
                for item in row:
                    if item.mine and not item.flagged:
                        item.flagged = True
        return "ok"

    def _reveal_all_mines(self) -> None:
        for row in self.grid:
            for cell in row:
                if cell.mine:
                    cell.revealed = True

    def cell_at_pixel(self, x: int, y: int) -> tuple[int, int] | None:
        if not (0 <= x < BOARD_W and 0 <= y < BOARD_H):
            return None
        return y // CELL, x // CELL


class MinesweeperApp:
    """tkinter presentation layer."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Minesweeper")
        self.root.resizable(False, False)
        self.rng = random.Random()
        self.game = Minesweeper(rng=self.rng)
        self.seconds = 0
        self.timer_job: str | None = None

        top = tk.Frame(root, padx=8, pady=6)
        top.pack(fill="x")
        self.mine_label = tk.Label(top, text=f"Mines: {MINES}", font=("Segoe UI", 11))
        self.mine_label.pack(side="left")
        self.status_label = tk.Label(top, text="Click to start", font=("Segoe UI", 11, "bold"))
        self.status_label.pack(side="left", expand=True)
        self.time_label = tk.Label(top, text="Time: 0", font=("Segoe UI", 11))
        self.time_label.pack(side="right")

        self.canvas = tk.Canvas(root, width=BOARD_W, height=BOARD_H,
                                bg="#9e9e9e", highlightthickness=0)
        self.canvas.pack(padx=8, pady=(0, 8))
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        bottom = tk.Frame(root)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(bottom, text="New game (R)", command=self.restart).pack(side="left")
        tk.Label(bottom, text="Left: reveal   Right: flag", fg="#555").pack(side="right")

        root.bind("<r>", lambda _event: self.restart())
        root.bind("<R>", lambda _event: self.restart())
        root.bind("<Escape>", lambda _event: root.destroy())
        root.focus_force()
        self.draw()

    def restart(self) -> None:
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.game = Minesweeper(rng=self.rng)
        self.seconds = 0
        self.time_label.config(text="Time: 0")
        self.status_label.config(text="Click to start", fg="black")
        self.mine_label.config(text=f"Mines: {MINES}")
        self.draw()

    def start_timer(self) -> None:
        if self.timer_job is None:
            self.timer_job = self.root.after(1000, self.tick)

    def tick(self) -> None:
        self.timer_job = None
        if self.game.state == "playing":
            self.seconds += 1
            self.time_label.config(text=f"Time: {self.seconds}")
            self.timer_job = self.root.after(1000, self.tick)

    def on_left_click(self, event: tk.Event) -> None:
        pos = self.game.cell_at_pixel(event.x, event.y)
        if pos is None:
            return
        result = self.game.reveal(*pos)
        if result == "ignored":
            return
        if self.game.state == "playing":
            self.start_timer()
        self.draw()
        if self.game.state == "lost":
            self.status_label.config(text="BOOM! You lost.", fg="#c62828")
            self.stop_timer()
        elif self.game.state == "won":
            self.status_label.config(text=f"You win in {self.seconds}s!", fg="#2e7d32")
            self.stop_timer()

    def on_right_click(self, event: tk.Event) -> None:
        pos = self.game.cell_at_pixel(event.x, event.y)
        if pos is None:
            return
        self.game.toggle_flag(*pos)
        self.mine_label.config(text=f"Mines: {max(0, self.game.mines_left)}")
        self.draw()

    def stop_timer(self) -> None:
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def draw(self) -> None:
        self.canvas.delete("all")
        for r in range(self.game.rows):
            for c in range(self.game.cols):
                cell = self.game.grid[r][c]
                x0, y0 = c * CELL, r * CELL
                x1, y1 = x0 + CELL, y0 + CELL
                if cell.revealed:
                    fill = "#d32f2f" if cell.mine else "#eceff1"
                else:
                    fill = "#b0bec5"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill,
                                             outline="#78909c", width=1)

                cx, cy = x0 + CELL // 2, y0 + CELL // 2
                if cell.revealed and cell.mine:
                    self.canvas.create_oval(x0 + 9, y0 + 9, x1 - 9, y1 - 9,
                                            fill="#212121", outline="")
                elif cell.revealed and cell.adjacent:
                    self.canvas.create_text(
                        cx, cy, text=str(cell.adjacent), font=("Segoe UI", 15, "bold"),
                        fill=NUMBER_COLORS[cell.adjacent],
                    )
                elif cell.flagged:
                    self.canvas.create_polygon(cx, y0 + 9, cx, y0 + 22,
                                               x1 - 11, y0 + 15, fill="#e53935",
                                               outline="#8e0000")
                    self.canvas.create_line(cx, y0 + 9, cx, y1 - 8, fill="#37474f", width=2)
                    self.canvas.create_line(x0 + 12, y1 - 8, x1 - 12, y1 - 8,
                                            fill="#37474f", width=2)


def main() -> None:
    root = tk.Tk()
    MinesweeperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
