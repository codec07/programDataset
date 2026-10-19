"""Maze Generator and Explorer (terminal / simulation).

What it does
------------
Generates a perfect maze with randomised depth-first search, prints it as
ASCII, optionally shows the shortest solution, and lets you walk through it.
Every open cell is reachable and there is exactly one path between any two
cells (the maze is a spanning tree).

Controls (play mode)
--------------------
* Arrow keys or W A S D - move
* Q                     - quit
On systems without raw keyboard access, type ``w``, ``a``, ``s``, ``d`` or
``q`` and press Enter.

Options
-------
    python maze_generator.py [--width 21] [--height 15] [--seed N]
                             [--solve] [--play] [--csv PATH]

``--csv`` writes the solution path as ``step,row,col`` rows.
Ctrl+C exits cleanly.

Run
---
    python maze_generator.py --solve
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from collections import deque

DEFAULT_WIDTH, DEFAULT_HEIGHT = 31, 19


class Maze:
    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 rng: random.Random | None = None) -> None:
        width = max(7, width)
        height = max(7, height)
        self.width = width if width % 2 == 1 else width + 1
        self.height = height if height % 2 == 1 else height + 1
        self.rng = rng or random.Random()
        self.grid: list[list[str]] = [["#"] * self.width for _ in range(self.height)]
        self.start = (1, 1)
        self.goal = (self.height - 2, self.width - 2)
        self._carve()

    def _carve(self) -> None:
        """Randomised iterative DFS: carve two cells at a time."""
        start_r, start_c = self.start
        self.grid[start_r][start_c] = " "
        stack = [self.start]
        directions = ((0, 2), (0, -2), (2, 0), (-2, 0))

        while stack:
            row, col = stack[-1]
            options = []
            for dr, dc in directions:
                nr, nc = row + dr, col + dc
                if (0 < nr < self.height - 1 and 0 < nc < self.width - 1
                        and self.grid[nr][nc] == "#"):
                    options.append((nr, nc, row + dr // 2, col + dc // 2))
            if not options:
                stack.pop()
                continue
            nr, nc, wall_r, wall_c = self.rng.choice(options)
            self.grid[wall_r][wall_c] = " "
            self.grid[nr][nc] = " "
            stack.append((nr, nc))

        self.grid[self.goal[0]][self.goal[1]] = " "

    @property
    def open_cells(self) -> int:
        return sum(cell == " " for row in self.grid for cell in row)

    def neighbours(self, row: int, col: int) -> list[tuple[int, int]]:
        result = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.height and 0 <= nc < self.width and self.grid[nr][nc] != "#":
                result.append((nr, nc))
        return result

    def solve(self) -> list[tuple[int, int]]:
        """BFS shortest path from start to goal, inclusive."""
        queue: deque[tuple[int, int]] = deque([self.start])
        parent: dict[tuple[int, int], tuple[int, int] | None] = {self.start: None}
        while queue:
            cell = queue.popleft()
            if cell == self.goal:
                break
            for neighbour in self.neighbours(*cell):
                if neighbour not in parent:
                    parent[neighbour] = cell
                    queue.append(neighbour)

        if self.goal not in parent:
            return []
        path = []
        current: tuple[int, int] | None = self.goal
        while current is not None:
            path.append(current)
            current = parent[current]
        return path[::-1]

    def render(self, path: list[tuple[int, int]] | None = None,
               player: tuple[int, int] | None = None) -> str:
        marks = set(path or [])
        lines = []
        for row in range(self.height):
            chars = []
            for col in range(self.width):
                cell = (row, col)
                if player == cell:
                    chars.append("@")
                elif cell == self.start:
                    chars.append("S")
                elif cell == self.goal:
                    chars.append("E")
                elif cell in marks:
                    chars.append(".")
                else:
                    chars.append(self.grid[row][col])
            lines.append("".join(chars))
        return "\n".join(lines)


def keyboard_available() -> bool:
    if os.name == "nt":
        return True
    try:
        return os.name == "posix" and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def read_key() -> str | None:
    """Return 'up', 'down', 'left', 'right', a character, or None."""
    if os.name == "nt":
        import msvcrt

        char = msvcrt.getwch()
        if char in {"\x00", "\xe0"}:
            second = msvcrt.getwch()
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(second)
        if char == "\x03":
            raise KeyboardInterrupt
        return char.lower()

    if os.name == "posix" and sys.stdin.isatty():
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
            if char == "\x1b":
                sequence = sys.stdin.read(2)
                return {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}.get(sequence)
            if char == "\x03":
                raise KeyboardInterrupt
            return char.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def play(maze: Maze) -> bool:
    """Walk the maze. Return True if the player reached the exit."""
    player = maze.start
    moves = 0
    use_raw = keyboard_available()
    if not use_raw:
        print("Raw keyboard input is unavailable. Type moves and press Enter.")

    valid = {
        "up": (-1, 0), "w": (-1, 0), "down": (1, 0), "s": (1, 0),
        "left": (0, -1), "a": (0, -1), "right": (0, 1), "d": (0, 1),
    }
    while True:
        clear_screen()
        print(maze.render(player=player))
        print(f"\nMoves: {moves}   Find E.  Arrow keys/WASD to move, Q to quit.")
        if player == maze.goal:
            print("\n*** You escaped the maze! ***")
            return True
        try:
            if use_raw:
                key = read_key()
            else:
                key = input("Move (w/a/s/d, q): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nLeaving the maze.")
            return False
        if key is None:
            continue
        if key in {"q", "quit", "exit"}:
            return False
        if key not in valid:
            continue
        dr, dc = valid[key]
        nr, nc = player[0] + dr, player[1] + dc
        if maze.grid[nr][nc] != "#":
            player = (nr, nc)
            moves += 1


def positive_odd(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 7:
        raise argparse.ArgumentTypeError("must be at least 7")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and explore an ASCII maze.")
    parser.add_argument("--width", type=positive_odd, default=DEFAULT_WIDTH,
                        help="maze width (odd numbers are used; default 31)")
    parser.add_argument("--height", type=positive_odd, default=DEFAULT_HEIGHT,
                        help="maze height (odd numbers are used; default 19)")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--solve", action="store_true", help="draw the shortest path")
    parser.add_argument("--play", action="store_true", help="walk the maze")
    parser.add_argument("--csv", metavar="PATH", help="write the solution path to CSV")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    maze = Maze(args.width, args.height, random.Random(seed))
    path = maze.solve()

    if args.play:
        play(maze)
        print(f"\nMaze {maze.width}x{maze.height}, seed {seed}, "
              f"open cells {maze.open_cells}, shortest path {len(path)} steps.")
        return

    print(f"Maze {maze.width}x{maze.height}  seed={seed}  open cells={maze.open_cells}")
    print(maze.render(path=path if args.solve else None))
    if path:
        print(f"Shortest path from S to E: {len(path) - 1} steps.")
        if args.solve:
            print("Path drawn with '.' characters.")

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["step", "row", "col"])
                for step, (row, col) in enumerate(path):
                    writer.writerow([step, row, col])
        except OSError as error:
            print(f"Could not write CSV: {error}")
        else:
            print(f"Solution written to {args.csv}")


if __name__ == "__main__":
    main()
