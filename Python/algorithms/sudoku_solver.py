"""Sudoku solver with constraint propagation via minimum-remaining-values search.

Puzzle representation: a 9x9 ``list[list[int]]`` where 0 marks an empty cell.
``parse_grid`` accepts an 81-character string using digits and ``.``/``_``.

Algorithm: depth-first backtracking that always fills the empty cell with the
fewest legal candidates (MRV heuristic).  Candidates come from the row, column
and 3x3 box constraints.  Cost is exponential in the worst case but trivial for
real puzzles; each placement is O(1) to validate against precomputed sets and
the recursion depth is at most 81.

The demo solves a classic puzzle (verifying against its published solution),
counts solutions (uniqueness and the limit parameter), proves a valid but
unsolvable grid returns no solution, and checks validation errors.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

SIZE = 9
BOX = 3


def parse_grid(text: str) -> List[List[int]]:
    """Parse an 81-character puzzle string into a 9x9 grid.

    Raises:
        TypeError: if *text* is not a string.
        ValueError: for the wrong length or invalid characters.
    """
    if not isinstance(text, str):
        raise TypeError("puzzle must be a string")
    compact = "".join(text.split())
    if len(compact) != SIZE * SIZE:
        raise ValueError("puzzle must contain exactly 81 cells")
    grid: List[List[int]] = []
    for row in range(SIZE):
        cells: List[int] = []
        for column in range(SIZE):
            character = compact[row * SIZE + column]
            if character in "._0":
                cells.append(0)
            elif "1" <= character <= "9":
                cells.append(int(character))
            else:
                raise ValueError(f"invalid puzzle character: {character!r}")
        grid.append(cells)
    return grid


def format_grid(grid: Sequence[Sequence[int]]) -> str:
    """Render a grid with box separators.  Raises ValueError if malformed."""
    _validate_shape(grid)
    lines: List[str] = []
    for row in range(SIZE):
        if row % BOX == 0 and row != 0:
            lines.append("------+-------+------")
        parts: List[str] = []
        for column in range(SIZE):
            if column % BOX == 0 and column != 0:
                parts.append("|")
            value = grid[row][column]
            parts.append(str(value) if value else ".")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _validate_shape(grid: Sequence[Sequence[int]]) -> None:
    if not isinstance(grid, (list, tuple)) or len(grid) != SIZE:
        raise ValueError("grid must have exactly 9 rows")
    for row in grid:
        if not isinstance(row, (list, tuple)) or len(row) != SIZE:
            raise ValueError("every row must have exactly 9 cells")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("cells must be integers")
            if not 0 <= value <= 9:
                raise ValueError("cells must be in 0..9")


def validate_grid(grid: Sequence[Sequence[int]]) -> None:
    """Check shapes, value ranges and the absence of duplicate digits.

    Raises ValueError when the puzzle already violates Sudoku rules.
    """
    _validate_shape(grid)
    for index in range(SIZE):
        row_values = [value for value in grid[index] if value]
        if len(row_values) != len(set(row_values)):
            raise ValueError(f"duplicate value in row {index}")
        column_values = [grid[row][index] for row in range(SIZE) if grid[row][index]]
        if len(column_values) != len(set(column_values)):
            raise ValueError(f"duplicate value in column {index}")
    for box_row in range(0, SIZE, BOX):
        for box_column in range(0, SIZE, BOX):
            seen = set()
            for row in range(box_row, box_row + BOX):
                for column in range(box_column, box_column + BOX):
                    value = grid[row][column]
                    if value:
                        if value in seen:
                            raise ValueError("duplicate value in a 3x3 box")
                        seen.add(value)


def _candidates(grid: List[List[int]], row: int, column: int) -> List[int]:
    used = set(grid[row])
    used.update(grid[r][column] for r in range(SIZE))
    box_row, box_column = row - row % BOX, column - column % BOX
    for r in range(box_row, box_row + BOX):
        for c in range(box_column, box_column + BOX):
            used.add(grid[r][c])
    return [value for value in range(1, 10) if value not in used]


def _best_empty(grid: List[List[int]]) -> Optional[Tuple[int, int, List[int]]]:
    best: Optional[Tuple[int, int, List[int]]] = None
    for row in range(SIZE):
        for column in range(SIZE):
            if grid[row][column] == 0:
                options = _candidates(grid, row, column)
                if not options:
                    return (row, column, [])
                if best is None or len(options) < len(best[2]):
                    best = (row, column, options)
                    if len(options) == 1:
                        return best
    return best


def _search(grid: List[List[int]]) -> bool:
    choice = _best_empty(grid)
    if choice is None:
        return True                       # every cell filled
    row, column, options = choice
    for value in options:
        grid[row][column] = value
        if _search(grid):
            return True
        grid[row][column] = 0
    return False


def solve(grid: Sequence[Sequence[int]]) -> Optional[List[List[int]]]:
    """Return a solved copy of *grid*, or None when no solution exists.

    Raises ValueError if the input already breaks the Sudoku rules.
    """
    validate_grid(grid)
    board = [list(row) for row in grid]
    return board if _search(board) else None


def count_solutions(grid: Sequence[Sequence[int]], limit: int = 2) -> int:
    """Count solutions up to *limit* (default 2, enough to test uniqueness)."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    validate_grid(grid)
    board = [list(row) for row in grid]
    found = 0

    def search() -> None:
        nonlocal found
        if found >= limit:
            return
        choice = _best_empty(board)
        if choice is None:
            found += 1
            return
        row, column, options = choice
        for value in options:
            board[row][column] = value
            search()
            board[row][column] = 0
            if found >= limit:
                return

    search()
    return found


PUZZLE = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)

PUBLISHED_SOLUTION = [
    [5, 3, 4, 6, 7, 8, 9, 1, 2],
    [6, 7, 2, 1, 9, 5, 3, 4, 8],
    [1, 9, 8, 3, 4, 2, 5, 6, 7],
    [8, 5, 9, 7, 6, 1, 4, 2, 3],
    [4, 2, 6, 8, 5, 3, 7, 9, 1],
    [7, 1, 3, 9, 2, 4, 8, 5, 6],
    [9, 6, 1, 5, 3, 7, 2, 8, 4],
    [2, 8, 7, 4, 1, 9, 6, 3, 5],
    [3, 4, 5, 2, 8, 6, 1, 7, 9],
]


def main() -> None:
    grid = parse_grid(PUZZLE)
    assert len(grid) == 9 and len(grid[0]) == 9
    assert grid[0][0] == 5 and grid[0][2] == 0
    validate_grid(grid)

    solution = solve(grid)
    assert solution == PUBLISHED_SOLUTION, "solver did not reproduce the known solution"
    assert count_solutions(grid) == 1, "published puzzle should have one solution"

    # Every placement obeys the Sudoku constraints.
    for index in range(SIZE):
        assert sorted(solution[index]) == list(range(1, 10))
        assert sorted(solution[row][index] for row in range(SIZE)) == list(range(1, 10))
    for box_row in range(0, SIZE, BOX):
        for box_column in range(0, SIZE, BOX):
            values = [
                solution[row][column]
                for row in range(box_row, box_row + BOX)
                for column in range(box_column, box_column + BOX)
            ]
            assert sorted(values) == list(range(1, 10))

    # An empty grid has many solutions; the limit stops the search early.
    empty = [[0] * SIZE for _ in range(SIZE)]
    assert count_solutions(empty, limit=2) == 2
    assert solve(empty) is not None

    # Valid input that is still unsatisfiable: row 0 needs a 9 in column 8,
    # but column 8 already contains a 9.
    unsolvable = [[0] * SIZE for _ in range(SIZE)]
    unsolvable[0] = [1, 2, 3, 4, 5, 6, 7, 8, 0]
    unsolvable[1][8] = 9
    validate_grid(unsolvable)
    assert solve(unsolvable) is None
    assert count_solutions(unsolvable) == 0

    try:
        parse_grid(PUZZLE + "0")
    except ValueError:
        pass
    else:
        raise AssertionError("parser accepted an over-long puzzle")
    for action in (
        lambda: parse_grid("0" * 81 + "x"),
        lambda: solve([[1] * 9] * 3),
        lambda: solve([[1, 1] + [0] * 7] + [[0] * 9] * 8),
        lambda: count_solutions(empty, limit=0),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid sudoku input was accepted")

    print("Self-test: sudoku solver reproduces the published solution and edge cases.")
    print(format_grid(solution))
    print("solutions for the puzzle: 1, for the empty grid (limit 2): 2, "
          "unsolvable grid: 0")


if __name__ == "__main__":
    main()
