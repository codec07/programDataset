"""Grid maze solving with BFS, DFS and A*.

Maze format: a list (or newline string) of equal-length rows using

* ``#`` wall
* ``.`` open cell
* ``S`` the single start
* ``E`` the single goal

Algorithms (V = cells, E = adjacent pairs ~ V):

* BFS  - shortest path in an unweighted grid, O(V) time/space
* DFS  - any path, O(V) time/space
* A*   - shortest path with the Manhattan-distance heuristic, O(V log V)

The demo checks exact paths on a tiny maze, compares BFS and A* lengths, shows
that DFS agrees on reachability, renders the path and exercises the error paths.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

Position = Tuple[int, int]
Grid = List[str]

_WALL = "#"
_START = "S"
_GOAL = "E"
_ALLOWED = set("#.SE")


def parse_maze(lines: Sequence[str] | str) -> Tuple[Grid, Position, Position]:
    """Normalize *lines* and locate start/goal.

    Raises:
        ValueError: for empty, ragged, multi-start/multi-goal or invalid mazes.
        TypeError: when the input is not a sequence of strings.
    """
    if isinstance(lines, str):
        rows = [row for row in lines.splitlines() if row.strip()]
    elif isinstance(lines, (list, tuple)):
        rows = list(lines)
    else:
        raise TypeError("maze must be a string or a sequence of strings")
    if not rows:
        raise ValueError("maze must not be empty")
    for row in rows:
        if not isinstance(row, str):
            raise TypeError("every maze row must be a string")
    width = len(rows[0])
    if width == 0:
        raise ValueError("maze rows must not be empty")
    starts: List[Position] = []
    goals: List[Position] = []
    for row_index, row in enumerate(rows):
        if len(row) != width:
            raise ValueError("maze rows must all have the same length")
        for column_index, character in enumerate(row):
            if character not in _ALLOWED:
                raise ValueError(f"invalid maze character: {character!r}")
            if character == _START:
                starts.append((row_index, column_index))
            elif character == _GOAL:
                goals.append((row_index, column_index))
    if len(starts) != 1 or len(goals) != 1:
        raise ValueError("maze must contain exactly one 'S' and one 'E'")
    return list(rows), starts[0], goals[0]


def _neighbors(grid: Grid, position: Position) -> List[Position]:
    row, column = position
    result: List[Position] = []
    for delta_row, delta_column in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        next_row, next_column = row + delta_row, column + delta_column
        if (
            0 <= next_row < len(grid)
            and 0 <= next_column < len(grid[0])
            and grid[next_row][next_column] != _WALL
        ):
            result.append((next_row, next_column))
    return result


def _rebuild(parent: Dict[Position, Optional[Position]], goal: Position) -> List[Position]:
    path: List[Position] = []
    current: Optional[Position] = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def bfs_shortest_path(lines: Sequence[str] | str) -> Optional[List[Position]]:
    """Return a shortest path (inclusive of start and goal) or None.  O(V)."""
    grid, start, goal = parse_maze(lines)
    parent: Dict[Position, Optional[Position]] = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current == goal:
            return _rebuild(parent, goal)
        for neighbour in _neighbors(grid, current):
            if neighbour not in parent:
                parent[neighbour] = current
                queue.append(neighbour)
    return None


def dfs_path(lines: Sequence[str] | str) -> Optional[List[Position]]:
    """Return any start-to-goal path or None using depth-first search.  O(V)."""
    grid, start, goal = parse_maze(lines)
    parent: Dict[Position, Optional[Position]] = {start: None}
    stack = [start]
    while stack:
        current = stack.pop()
        if current == goal:
            return _rebuild(parent, goal)
        for neighbour in reversed(_neighbors(grid, current)):
            if neighbour not in parent:
                parent[neighbour] = current
                stack.append(neighbour)
    return None


def a_star_path(lines: Sequence[str] | str) -> Optional[List[Position]]:
    """Shortest path using A* with the Manhattan heuristic.  O(V log V)."""
    grid, start, goal = parse_maze(lines)

    def heuristic(position: Position) -> int:
        return abs(position[0] - goal[0]) + abs(position[1] - goal[1])

    best: Dict[Position, int] = {start: 0}
    parent: Dict[Position, Optional[Position]] = {start: None}
    frontier: List[Tuple[int, int, Position]] = [(heuristic(start), 0, start)]
    settled = set()
    while frontier:
        _, cost, current = heapq.heappop(frontier)
        if current in settled:
            continue
        settled.add(current)
        if current == goal:
            return _rebuild(parent, goal)
        for neighbour in _neighbors(grid, current):
            candidate = cost + 1
            if candidate < best.get(neighbour, 1 << 30):
                best[neighbour] = candidate
                parent[neighbour] = current
                heapq.heappush(frontier, (candidate + heuristic(neighbour), candidate, neighbour))
    return None


def render_path(lines: Sequence[str] | str, path: Sequence[Position]) -> List[str]:
    """Overlay *path* with '*' on a copy of the maze."""
    grid, start, goal = parse_maze(lines)
    canvas = [list(row) for row in grid]
    for row, column in path:
        if (row, column) not in (start, goal):
            canvas[row][column] = "*"
    return ["".join(row) for row in canvas]


def main() -> None:
    tiny = [
        "#####",
        "#S.E#",
        "#####",
    ]
    path = bfs_shortest_path(tiny)
    assert path == [(1, 1), (1, 2), (1, 3)], path
    assert a_star_path(tiny) == path
    assert dfs_path(tiny) == path
    assert render_path(tiny, path) == ["#####", "#S*E#", "#####"]

    maze = [
        "#########",
        "#S..#...#",
        "#.#.#.#.#",
        "#.#...#.#",
        "#.#####.#",
        "#.......#",
        "#######E#",
        "#########",
    ]
    shortest = bfs_shortest_path(maze)
    assert shortest is not None and shortest[0] == (1, 1) and shortest[-1] == (6, 7)
    assert len(shortest) == 12, len(shortest)          # 11 steps via column 1
    assert a_star_path(maze) == shortest
    other = dfs_path(maze)
    assert other is not None and len(other) >= len(shortest)
    grid, _, _ = parse_maze(maze)
    for (row, column), (next_row, next_column) in zip(shortest, shortest[1:]):
        assert abs(row - next_row) + abs(column - next_column) == 1
        assert grid[row][column] != "#"
    rendered = render_path(maze, shortest)
    assert rendered[2][1] == "*" and rendered[6][7] == "E"

    blocked = ["#####", "#S#E#", "#####"]
    assert bfs_shortest_path(blocked) is None
    assert dfs_path(blocked) is None
    assert a_star_path(blocked) is None

    # Multi-line string input works the same way.
    assert bfs_shortest_path("\n".join(tiny)) == path

    for action in (
        lambda: parse_maze([]),
        lambda: parse_maze(["###", "##"]),
        lambda: parse_maze(["S.."]),
        lambda: parse_maze(["SSE"]),
        lambda: parse_maze(["S#X"]),
        lambda: parse_maze(123),  # type: ignore[arg-type]
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid maze input was accepted")

    print("Self-test: BFS/DFS/A* maze solving, rendering and validation passed.")
    print(f"tiny shortest path: {path}")
    print(f"larger maze shortest length: {len(shortest)} cells")
    print("\n".join(rendered))


if __name__ == "__main__":
    main()
