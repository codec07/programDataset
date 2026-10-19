"""N-Queens: count or construct placements of n non-attacking queens.

The board is n x n and a solution is stored as a list of n column indices, one
per row (so ``solution[row] == column``).  Both routines use bitmask
backtracking: columns, "/" diagonals and "\\" diagonals are tracked as bit sets,
giving O(1) candidate enumeration per node.

Complexity: worst case O(n!) nodes, but pruning makes the real work far
smaller (n=8 explores a few thousand nodes).  Recursion depth is n, so space is
O(n) beyond the bit masks.

The demo verifies the classic counts (n=4 -> 2, n=5 -> 10, n=6 -> 4, n=8 -> 92),
checks the validity predicate, renders one board and exercises validation.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Sequence

MAX_N = 15


def _check_size(n: object) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n < 1:
        raise ValueError("n must be at least 1")
    if n > MAX_N:
        raise ValueError(f"n must be at most {MAX_N}")
    return n


def solve_n_queens(n: int) -> Optional[List[int]]:
    """Return one solution for an n x n board, or None when none exists.

    The returned list maps row -> column.  Time/space: O(n) depth, exponential
    worst case.
    """
    n = _check_size(n)
    full = (1 << n) - 1
    placement: List[int] = []

    def place(row: int, columns: int, down_diagonal: int, up_diagonal: int) -> bool:
        if row == n:
            return True
        available = full & ~(columns | down_diagonal | up_diagonal)
        while available:
            bit = available & -available
            available ^= bit
            placement.append(bit.bit_length() - 1)
            if place(
                row + 1,
                columns | bit,
                ((down_diagonal | bit) << 1) & full,
                (up_diagonal | bit) >> 1,
            ):
                return True
            placement.pop()
        return False

    return placement if place(0, 0, 0, 0) else None


def all_solutions(n: int) -> Iterator[List[int]]:
    """Yield every solution for an n x n board (lazy generator)."""
    n = _check_size(n)
    full = (1 << n) - 1
    placement: List[int] = []

    def place(row: int, columns: int, down_diagonal: int, up_diagonal: int):
        if row == n:
            yield list(placement)
            return
        available = full & ~(columns | down_diagonal | up_diagonal)
        while available:
            bit = available & -available
            available ^= bit
            placement.append(bit.bit_length() - 1)
            yield from place(
                row + 1,
                columns | bit,
                ((down_diagonal | bit) << 1) & full,
                (up_diagonal | bit) >> 1,
            )
            placement.pop()

    return place(0, 0, 0, 0)


def count_n_queens(n: int) -> int:
    """Return the number of solutions for an n x n board."""
    n = _check_size(n)
    full = (1 << n) - 1

    def count(columns: int, down_diagonal: int, up_diagonal: int) -> int:
        if columns == full:
            return 1
        total = 0
        available = full & ~(columns | down_diagonal | up_diagonal)
        while available:
            bit = available & -available
            available ^= bit
            total += count(
                columns | bit,
                ((down_diagonal | bit) << 1) & full,
                (up_diagonal | bit) >> 1,
            )
        return total

    return count(0, 0, 0)


def is_valid(solution: Sequence[int]) -> bool:
    """Check that *solution* places queens with no shared column or diagonal."""
    if not isinstance(solution, (list, tuple)):
        return False
    size = len(solution)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in solution):
        return False
    if any(not 0 <= value < size for value in solution):
        return False
    if len(set(solution)) != size:
        return False
    for row in range(size):
        for other in range(row + 1, size):
            if abs(solution[row] - solution[other]) == other - row:
                return False
    return True


def board_lines(solution: Sequence[int]) -> List[str]:
    """Render a solution as n strings ('.' empty, 'Q' queen)."""
    if not is_valid(solution):
        raise ValueError("cannot render an invalid solution")
    size = len(solution)
    return ["." * solution[row] + "Q" + "." * (size - solution[row] - 1) for row in range(size)]


def main() -> None:
    assert solve_n_queens(1) == [0]
    assert solve_n_queens(2) is None
    assert solve_n_queens(3) is None

    for size, expected in [(1, 1), (4, 2), (5, 10), (6, 4), (7, 40), (8, 92)]:
        assert count_n_queens(size) == expected, (size, count_n_queens(size))
        assert len(list(all_solutions(size))) == expected

    first = solve_n_queens(4)
    assert first is not None and is_valid(first)
    enemies = list(all_solutions(4))
    assert sorted(enemies) == [[1, 3, 0, 2], [2, 0, 3, 1]]

    eight = solve_n_queens(8)
    assert eight is not None and is_valid(eight)
    assert board_lines(eight) == [
        "." * eight[row] + "Q" + "." * (7 - eight[row]) for row in range(8)
    ]

    assert is_valid([1, 3, 0, 2]) is True
    assert is_valid([0, 0, 0, 0]) is False       # shared column
    assert is_valid([0, 1, 2, 3]) is False       # shared diagonal
    assert is_valid([0, 2, 1, 3]) is False
    assert is_valid([]) is True

    for action in (
        lambda: solve_n_queens(0),
        lambda: solve_n_queens(-3),
        lambda: count_n_queens(MAX_N + 1),
        lambda: solve_n_queens("8"),  # type: ignore[arg-type]
        lambda: board_lines([0, 0]),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid n-queens input was accepted")

    print("Self-test: n-queens counts and solution construction passed.")
    print(f"counts: {[count_n_queens(n) for n in range(1, 9)]}")
    print(f"one 8-queens solution: {eight}")
    print("\n".join(board_lines(eight)))


if __name__ == "__main__":
    main()
