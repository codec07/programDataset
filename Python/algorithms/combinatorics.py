"""Combinatorics: counting formulas and generators.

Counting functions (all exact Python integers):

* ``factorial``            - O(n) multiplications
* ``binomial``             - O(min(k, n-k)) multiplications
* ``permutations_count``   - O(k)
* ``pascal_row``           - O(n) additions, O(n) space
* ``catalan``              - O(n) via a binomial coefficient
* ``derangements``         - O(n) time, O(1) space
* ``stars_and_bars``       - O(k) via a binomial coefficient

Generators (lazy, O(k) extra space beyond the output):

* ``combinations(items, k)`` - every k-subset in input order
* ``permutations(items)``    - every ordering

The demo checks the counts against ``math.comb``/``math.perm``, validates the
generators' sizes and ordering, and exercises the error paths.
"""

from __future__ import annotations

import itertools
import math
from typing import Iterable, Iterator, List, Sequence, Tuple


def _check_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return value


def factorial(number: int) -> int:
    """Return n! (with 0! == 1).  Raises ValueError for negative input."""
    number = _check_int(number, "number")
    if number < 0:
        raise ValueError("factorial requires a non-negative integer")
    result = 1
    for value in range(2, number + 1):
        result *= value
    return result


def binomial(total: int, chosen: int) -> int:
    """Return C(total, chosen) exactly.  O(min(k, n-k)) multiplications."""
    total = _check_int(total, "total")
    chosen = _check_int(chosen, "chosen")
    if total < 0:
        raise ValueError("total must be non-negative")
    if chosen < 0 or chosen > total:
        raise ValueError("chosen must satisfy 0 <= chosen <= total")
    chosen = min(chosen, total - chosen)
    result = 1
    for step in range(1, chosen + 1):
        result = result * (total - chosen + step) // step
    return result


def permutations_count(total: int, chosen: int) -> int:
    """Return P(total, chosen) = total! / (total - chosen)!.  O(chosen)."""
    total = _check_int(total, "total")
    chosen = _check_int(chosen, "chosen")
    if total < 0:
        raise ValueError("total must be non-negative")
    if chosen < 0 or chosen > total:
        raise ValueError("chosen must satisfy 0 <= chosen <= total")
    result = 1
    for value in range(total - chosen + 1, total + 1):
        result *= value
    return result


def pascal_row(index: int) -> List[int]:
    """Return row *index* of Pascal's triangle as a list of length index + 1."""
    index = _check_int(index, "index")
    if index < 0:
        raise ValueError("row index must be non-negative")
    row = [1]
    for _ in range(index):
        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]
    return row


def catalan(number: int) -> int:
    """Return the *number*-th Catalan number.  O(n) multiplications."""
    number = _check_int(number, "number")
    if number < 0:
        raise ValueError("catalan index must be non-negative")
    return binomial(2 * number, number) // (number + 1)


def derangements(number: int) -> int:
    """Return the number of permutations with no fixed point (!n).

    Recurrence D(n) = (n-1) * (D(n-1) + D(n-2)), D(0)=1, D(1)=0.
    Time: O(n), space: O(1).
    """
    number = _check_int(number, "number")
    if number < 0:
        raise ValueError("derangements index must be non-negative")
    if number == 0:
        return 1
    previous, current = 1, 0
    for index in range(2, number + 1):
        previous, current = current, (index - 1) * (current + previous)
    return current


def stars_and_bars(items: int, bins: int) -> int:
    """Ways to place *items* identical objects into *bins* labelled bins.

    Equals C(items + bins - 1, bins - 1).  Each bin may receive zero objects.
    """
    items = _check_int(items, "items")
    bins = _check_int(bins, "bins")
    if items < 0:
        raise ValueError("items must be non-negative")
    if bins < 1:
        raise ValueError("bins must be at least 1")
    return binomial(items + bins - 1, bins - 1)


def combinations(items: Sequence[object], chosen: int) -> Iterator[Tuple[object, ...]]:
    """Yield every *chosen*-length combination in input order (lazy)."""
    chosen = _check_int(chosen, "chosen")
    pool = list(items)
    if chosen < 0 or chosen > len(pool):
        raise ValueError("chosen must satisfy 0 <= chosen <= len(items)")

    def generate(start: int, current: List[object]) -> Iterator[Tuple[object, ...]]:
        if len(current) == chosen:
            yield tuple(current)
            return
        remaining = chosen - len(current)
        for index in range(start, len(pool) - remaining + 1):
            current.append(pool[index])
            yield from generate(index + 1, current)
            current.pop()

    return generate(0, [])


def permutations(items: Sequence[object]) -> Iterator[Tuple[object, ...]]:
    """Yield every permutation of *items* in lexicographic index order (lazy)."""
    pool = list(items)

    def generate(remaining: List[object], current: List[object]) -> Iterator[Tuple[object, ...]]:
        if not remaining:
            yield tuple(current)
            return
        for index in range(len(remaining)):
            current.append(remaining[index])
            yield from generate(remaining[:index] + remaining[index + 1:], current)
            current.pop()

    return generate(pool, [])


def main() -> None:
    assert factorial(0) == 1 and factorial(5) == 120
    assert binomial(10, 3) == 120 == math.comb(10, 3)
    for total in range(0, 30):
        for chosen in range(0, total + 1):
            assert binomial(total, chosen) == math.comb(total, chosen)
            assert permutations_count(total, chosen) == math.perm(total, chosen)
    assert permutations_count(5, 2) == 20

    assert pascal_row(0) == [1]
    assert pascal_row(5) == [1, 5, 10, 10, 5, 1]
    for index in range(15):
        row = pascal_row(index)
        assert len(row) == index + 1 and sum(row) == 2**index
        assert row == [binomial(index, k) for k in range(index + 1)]

    assert [catalan(n) for n in range(7)] == [1, 1, 2, 5, 14, 42, 132]
    assert [derangements(n) for n in range(7)] == [1, 0, 1, 2, 9, 44, 265]
    assert stars_and_bars(5, 3) == 21          # C(7, 2)
    assert stars_and_bars(0, 4) == 1           # everything in one bin
    assert stars_and_bars(4, 1) == 1           # only one bin
    assert sum(1 for _ in combinations(range(6), 3)) == binomial(6, 3)
    assert sum(1 for _ in permutations(range(5))) == factorial(5)

    assert list(combinations([1, 2, 3], 2)) == [(1, 2), (1, 3), (2, 3)]
    assert list(combinations([1, 2, 3], 0)) == [()]
    assert list(combinations([1, 2, 3], 3)) == [(1, 2, 3)]
    assert list(permutations([1, 2, 3])) == [
        (1, 2, 3),
        (1, 3, 2),
        (2, 1, 3),
        (2, 3, 1),
        (3, 1, 2),
        (3, 2, 1),
    ]
    assert list(combinations([1, 2, 3], 2)) == list(itertools.combinations([1, 2, 3], 2))

    # Derangements really are permutations without fixed points for small n.
    for n in range(1, 6):
        count = 0
        for arrangement in permutations(range(n)):
            if all(arrangement[i] != i for i in range(n)):
                count += 1
        assert count == derangements(n), n

    for action in (
        lambda: factorial(-1),
        lambda: binomial(3, 4),
        lambda: pascal_row(-1),
        lambda: catalan(-2),
        lambda: derangements(-1),
        lambda: stars_and_bars(2, 0),
        lambda: combinations([1, 2], 3),
        lambda: factorial(2.5),  # type: ignore[arg-type]
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid combinatorics input was accepted")

    print("Self-test: combinatorics counts match math.comb/math.perm and enumerations.")
    print(f"Pascal row 6: {pascal_row(6)}")
    print(f"Catalan 0..8: {[catalan(n) for n in range(9)]}")
    print(f"subsets of size 2 from 5 elements: {binomial(5, 2)}")


if __name__ == "__main__":
    main()
