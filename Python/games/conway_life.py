"""Conway's Game of Life (tkinter simulation + headless mode).

Rules
-----
Each cell is alive or dead. Every generation updates all cells at once using
these rules (B3/S23) on a wrapping, toroidal grid:

* A live cell with 2 or 3 live neighbours survives.
* A dead cell with exactly 3 live neighbours becomes alive.
* Every other cell dies or stays dead.

Controls (windowed mode)
------------------------
* Left click - toggle a cell (while paused is easiest)
* Space      - run / pause
* N          - advance one generation while paused
* R          - randomise the grid
* C          - clear the grid
* G          - place a glider near the centre
* Esc        - quit

Command line
------------
    python conway_life.py
    python conway_life.py --headless --steps 100 --seed 7 --csv life.csv
    python conway_life.py --width 60 --height 40 --density 0.3

Run
---
    python conway_life.py
"""

from __future__ import annotations

import argparse
import csv
import random
import tkinter as tk
from collections import Counter

DEFAULT_COLS, DEFAULT_ROWS = 80, 50
CELL = 12
TICK_MS = 90


class Life:
    """Game of Life on a finite toroidal grid."""

    def __init__(self, cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS,
                 rng: random.Random | None = None, density: float = 0.28) -> None:
        self.cols, self.rows = cols, rows
        self.rng = rng or random.Random()
        self.live: set[tuple[int, int]] = set()
        self.generation = 0
        self.randomize(density)

    def randomize(self, density: float = 0.28) -> None:
        self.live = {(r, c) for r in range(self.rows) for c in range(self.cols)
                     if self.rng.random() < density}
        self.generation = 0

    def clear(self) -> None:
        self.live.clear()
        self.generation = 0

    def toggle(self, row: int, col: int) -> None:
        cell = (row, col)
        if cell in self.live:
            self.live.remove(cell)
        else:
            self.live.add(cell)

    def add_glider(self, row: int | None = None, col: int | None = None) -> None:
        row = self.rows // 2 if row is None else row
        col = self.cols // 2 if col is None else col
        pattern = ((0, 1), (1, 2), (2, 0), (2, 1), (2, 2))
        for dr, dc in pattern:
            self.live.add(((row + dr) % self.rows, (col + dc) % self.cols))

    def step(self) -> int:
        """Advance one generation and return the new population."""
        counts: Counter[tuple[int, int]] = Counter()
        for row, col in self.live:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    counts[((row + dr) % self.rows, (col + dc) % self.cols)] += 1

        self.live = {cell for cell, count in counts.items()
                     if count == 3 or (count == 2 and cell in self.live)}
        self.generation += 1
        return len(self.live)

    def render(self) -> str:
        lines = []
        for row in range(self.rows):
            lines.append("".join("#" if (row, col) in self.live else "."
                                 for col in range(self.cols)))
        return "\n".join(lines)


class LifeApp:
    def __init__(self, root: tk.Tk, rng: random.Random, density: float,
                 cols: int = DEFAULT_COLS, rows: int = DEFAULT_ROWS) -> None:
        self.root = root
        self.root.title("Conway's Game of Life")
        self.root.resizable(False, False)
        self.life = Life(cols, rows, rng, density)
        self.density = density
        self.running = True
        self.job: str | None = None

        self.canvas = tk.Canvas(root, width=self.life.cols * CELL,
                                height=self.life.rows * CELL,
                                bg="#0d1117", highlightthickness=0)
        self.canvas.pack()
        self.info = tk.Label(root, text="", anchor="w", padx=8, pady=4,
                             bg="#161b22", fg="#c9d1d9",
                             font=("Consolas", 10))
        self.info.pack(fill="x")

        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<space>", lambda _event: self.toggle_running())
        self.root.bind("<n>", lambda _event: self.single_step())
        self.root.bind("<r>", lambda _event: self.randomize())
        self.root.bind("<c>", lambda _event: self.clear())
        self.root.bind("<g>", lambda _event: self.glider())
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.schedule()
        self.draw()

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.root.destroy()

    def schedule(self) -> None:
        self.job = self.root.after(TICK_MS, self.tick)

    def tick(self) -> None:
        self.job = None
        if self.running:
            self.life.step()
        self.draw()
        self.schedule()

    def toggle_running(self) -> None:
        self.running = not self.running
        self.draw()

    def single_step(self) -> None:
        if not self.running:
            self.life.step()
            self.draw()

    def randomize(self) -> None:
        self.life.randomize(self.density)
        self.draw()

    def clear(self) -> None:
        self.running = False
        self.life.clear()
        self.draw()

    def glider(self) -> None:
        self.running = False
        self.life.add_glider()
        self.draw()

    def on_click(self, event: tk.Event) -> None:
        col, row = event.x // CELL, event.y // CELL
        if 0 <= row < self.life.rows and 0 <= col < self.life.cols:
            self.life.toggle(row, col)
            self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        for row, col in self.life.live:
            x, y = col * CELL, row * CELL
            self.canvas.create_rectangle(x, y, x + CELL - 1, y + CELL - 1,
                                         fill="#4ade80", outline="")
        state = "RUNNING" if self.running else "PAUSED"
        self.info.config(text=f"{state}   generation {self.life.generation}   "
                              f"population {len(self.life.live)}   "
                              f"space=run/pause  n=step  r=random  c=clear  g=glider")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conway's Game of Life.")
    parser.add_argument("--headless", action="store_true",
                        help="run without a window and print statistics")
    parser.add_argument("--steps", type=int, default=100,
                        help="generations to simulate in headless mode (default 100)")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--width", type=int, default=DEFAULT_COLS,
                        help="number of columns (default 80)")
    parser.add_argument("--height", type=int, default=DEFAULT_ROWS,
                        help="number of rows (default 50)")
    parser.add_argument("--density", type=float, default=0.28,
                        help="initial live-cell probability, 0..1 (default 0.28)")
    parser.add_argument("--csv", metavar="PATH",
                        help="write generation,population statistics to CSV")
    args = parser.parse_args(argv)
    if args.width < 5 or args.height < 5:
        parser.error("width and height must be at least 5")
    if args.steps < 0:
        parser.error("steps must be non-negative")
    if not 0.0 <= args.density <= 1.0:
        parser.error("density must be between 0 and 1")
    return args


def run_headless(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    life = Life(args.width, args.height, rng, args.density)
    initial = len(life.live)
    peak = initial
    minimum = initial
    extinct_generation: int | None = None
    rows: list[tuple[int, int]] = [(0, initial)]

    for _ in range(args.steps):
        population = life.step()
        rows.append((life.generation, population))
        peak = max(peak, population)
        minimum = min(minimum, population)
        if population == 0 and extinct_generation is None:
            extinct_generation = life.generation

    print(f"Game of Life: {args.width}x{args.height} toroidal grid, "
          f"seed={args.seed}, density={args.density}")
    print(f"Initial population: {initial}")
    print(f"Generations run    : {args.steps}")
    print(f"Final population   : {len(life.live)}")
    print(f"Peak population    : {peak}")
    print(f"Minimum population : {minimum}")
    print(f"Extinct at         : {extinct_generation if extinct_generation else 'never'}")
    print("\nFinal grid:")
    print(life.render())

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["generation", "population"])
                writer.writerows(rows)
        except OSError as error:
            print(f"Could not write CSV: {error}")
        else:
            print(f"Statistics written to {args.csv}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.headless:
        run_headless(args)
        return

    root = tk.Tk()
    LifeApp(root, random.Random(args.seed), args.density, args.width, args.height)
    root.mainloop()


if __name__ == "__main__":
    main()
