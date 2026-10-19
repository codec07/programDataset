"""Binary-search variants over sorted sequences.

All searches assume non-decreasing input.  Each public search validates that
precondition in O(n) time, then performs an O(log n) search; auxiliary space is
O(1).  ``lower_bound``/``upper_bound`` and the rotated-array search also use
O(1) space, and the rotated search requires distinct elements.

The demo compares the implementations against linear scans and Python's
``bisect`` module on seeded random data, and exercises the error paths.
"""

from __future__ import annotations

import bisect
import random
from typing import List, Optional, Sequence

Number = int | float


def _require_sorted(values: Sequence[Number]) -> None:
    """Raise ValueError if *values* is not in non-decreasing order."""
    for index in range(1, len(values)):
        if values[index] < values[index - 1]:
            raise ValueError("input sequence must be sorted in non-decreasing order")


def binary_search(values: Sequence[Number], target: Number) -> int:
    """Return an index of *target* in sorted *values*, or -1 when absent.

    Time: O(n) validation + O(log n) search. Space: O(1).
    """
    _require_sorted(values)
    low, high = 0, len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1


def lower_bound(values: Sequence[Number], target: Number) -> int:
    """Return the first index where *target* could be inserted (bisect_left).

    The result is in ``[0, len(values)]``.

    Time: O(n) validation + O(log n) search. Space: O(1).
    """
    _require_sorted(values)
    low, high = 0, len(values)
    while low < high:
        middle = (low + high) // 2
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low


def upper_bound(values: Sequence[Number], target: Number) -> int:
    """Return the last insertion point after equal values (bisect_right).

    Time: O(n) validation + O(log n) search. Space: O(1).
    """
    _require_sorted(values)
    low, high = 0, len(values)
    while low < high:
        middle = (low + high) // 2
        if values[middle] <= target:
            low = middle + 1
        else:
            high = middle
    return low


def first_occurrence(values: Sequence[Number], target: Number) -> int:
    """Return the index of the first *target*, or -1.

    Time: O(n) validation + O(log n) search.
    """
    index = lower_bound(values, target)
    if index < len(values) and values[index] == target:
        return index
    return -1


def last_occurrence(values: Sequence[Number], target: Number) -> int:
    """Return the index of the last *target*, or -1.

    Time: O(n) validation + O(log n) search.
    """
    index = upper_bound(values, target) - 1
    if index >= 0 and values[index] == target:
        return index
    return -1


def exponential_search(values: Sequence[Number], target: Number) -> int:
    """Search sorted *values* by doubling a bound, then binary searching.

    Useful for unbounded/streaming data.

    Time: O(n) validation + O(log n) search. Space: O(1).
    """
    _require_sorted(values)
    size = len(values)
    if size == 0:
        return -1
    if values[0] == target:
        return 0
    bound = 1
    while bound < size and values[bound] < target:
        bound *= 2
    # Target lies in (bound // 2, min(bound, size - 1)].
    low = bound // 2
    high = min(bound, size - 1)
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1


def search_rotated(values: Sequence[int], target: int) -> int:
    """Search a rotated sorted array of distinct integers.

    Example: ``[4, 5, 6, 7, 0, 1, 2]``.

    Time: O(n) duplicate check + O(log n) search. Space: O(1).

    Raises:
        ValueError: if the array contains duplicates.
    """
    if len(set(values)) != len(values):
        raise ValueError("rotated search requires distinct values")
    low, high = 0, len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[low] <= values[middle]:
            # Left half is sorted.
            if values[low] <= target < values[middle]:
                high = middle - 1
            else:
                low = middle + 1
        else:
            # Right half is sorted.
            if values[middle] < target <= values[high]:
                low = middle + 1
            else:
                high = middle - 1
    return -1


def integer_sqrt(value: int) -> int:
    """Return ``floor(sqrt(value))`` using binary search.

    Time: O(log value). Space: O(1).

    Raises:
        TypeError: if *value* is not an integer.
        ValueError: if *value* is negative.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("integer_sqrt requires an int")
    if value < 0:
        raise ValueError("integer_sqrt requires a non-negative value")
    if value < 2:
        return value
    low, high = 1, value // 2 + 1
    answer = 1
    while low <= high:
        middle = (low + high) // 2
        square = middle * middle
        if square == value:
            return middle
        if square < value:
            answer = middle
            low = middle + 1
        else:
            high = middle - 1
    return answer


def _linear_find(values: Sequence[Number], target: Number) -> int:
    """Naive reference: first matching index or -1.  Time: O(n)."""
    for index, value in enumerate(values):
        if value == target:
            return index
    return -1


def main() -> None:
    values = [1, 3, 3, 3, 5, 7, 9, 11]
    index = binary_search(values, 5)
    assert index == 4 and values[index] == 5
    found = binary_search(values, 3)
    assert found != -1 and values[found] == 3
    assert binary_search(values, 4) == -1
    assert binary_search([], 1) == -1

    assert lower_bound(values, 3) == 1
    assert upper_bound(values, 3) == 4
    assert first_occurrence(values, 3) == 1
    assert last_occurrence(values, 3) == 3
    assert first_occurrence(values, 8) == -1
    assert last_occurrence(values, 8) == -1
    assert lower_bound(values, 0) == 0
    assert upper_bound(values, 99) == len(values)

    try:
        binary_search([3, 2, 1], 2)
    except ValueError:
        pass
    else:
        raise AssertionError("binary_search accepted unsorted input")

    rotated = [4, 5, 6, 7, 0, 1, 2]
    for expected, target in enumerate(rotated):
        assert search_rotated(rotated, target) == expected
    assert search_rotated(rotated, 3) == -1
    try:
        search_rotated([1, 1, 2], 2)
    except ValueError:
        pass
    else:
        raise AssertionError("search_rotated accepted duplicates")

    for value, expected in [(0, 0), (1, 1), (15, 3), (16, 4), (17, 4), (10**12, 10**6)]:
        assert integer_sqrt(value) == expected, value
    for bad in (-1,):
        try:
            integer_sqrt(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("integer_sqrt accepted a negative value")

    rng = random.Random(99)
    for _ in range(100):
        size = rng.randint(0, 60)
        data = sorted(rng.randint(-20, 20) for _ in range(size))
        for target in range(-22, 23):
            # binary_search may return any duplicate index.
            result = binary_search(data, target)
            if result == -1:
                assert _linear_find(data, target) == -1
            else:
                assert data[result] == target
            assert lower_bound(data, target) == bisect.bisect_left(data, target)
            assert upper_bound(data, target) == bisect.bisect_right(data, target)
            if target in data:
                exp_index = exponential_search(data, target)
                assert exp_index != -1 and data[exp_index] == target
            else:
                assert exponential_search(data, target) == -1

    print("Self-test: binary search variants agree with bisect/linear scans.")
    print(f"examples: lower_bound={lower_bound(values, 3)}, "
          f"upper_bound={upper_bound(values, 3)}, "
          f"rotated index={search_rotated(rotated, 0)}, "
          f"integer_sqrt(10**12)={integer_sqrt(10**12)}")


if __name__ == "__main__":
    main()
