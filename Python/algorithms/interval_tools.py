"""Interval utilities: merging, insertion, intersection and coverage.

An interval is a closed ``(start, end)`` pair of numbers with ``start <= end``.
All inputs are validated, and every routine leaves the caller's lists untouched.

Complexity (n intervals in total, sorted where noted):

* ``merge_intervals``       - O(n log n) (sorting dominates), O(n) space
* ``insert_interval``       - O(n) for an already-sorted list, O(n) space
* ``intersect_intervals``   - O(n + m) after sorting both inputs
* ``total_covered_length``  - O(n log n)
* ``coverage_count``        - O(n)
* ``max_overlap``           - O(n log n) (sweep over 2n events)

Touching intervals such as ``[1, 2]`` and ``[2, 3]`` share the point 2 and are
treated as overlapping, matching the closed-interval convention.

The demo mixes hand-checked cases with randomized comparison against a naive
point-sampling check of total covered length.
"""

from __future__ import annotations

import random
from typing import Iterable, List, Sequence, Tuple

Interval = Tuple[float, float]


def _validate(interval: Sequence[float], name: str = "interval") -> Interval:
    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
        raise ValueError(f"{name} must be a (start, end) pair")
    start, end = interval
    for bound in (start, end):
        if isinstance(bound, bool) or not isinstance(bound, (int, float)):
            raise TypeError(f"{name} bounds must be real numbers")
    if start > end:
        raise ValueError(f"{name} start must not exceed end")
    return float(start), float(end)


def _validate_all(intervals: Iterable[Sequence[float]]) -> List[Interval]:
    return [_validate(interval) for interval in intervals]


def merge_intervals(intervals: Iterable[Sequence[float]]) -> List[Interval]:
    """Merge overlapping/touching intervals into disjoint sorted intervals.

    Time: O(n log n).  Space: O(n).  Returns [] for empty input.
    """
    data = sorted(_validate_all(intervals))
    merged: List[Interval] = []
    for start, end in data:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def insert_interval(
    intervals: Sequence[Sequence[float]], new_interval: Sequence[float]
) -> List[Interval]:
    """Insert *new_interval* into a sorted list and merge as needed.

    The input must already be sorted by start (already merged), otherwise the
    O(n) single-pass guarantee does not hold and ValueError is raised.
    """
    data = _validate_all(intervals)
    for previous, current in zip(data, data[1:]):
        if current[0] < previous[0]:
            raise ValueError("intervals must be sorted by start")
    start, end = _validate(new_interval, "new_interval")
    result: List[Interval] = []
    index = 0
    while index < len(data) and data[index][1] < start:
        result.append(data[index])
        index += 1
    while index < len(data) and data[index][0] <= end:
        start = min(start, data[index][0])
        end = max(end, data[index][1])
        index += 1
    result.append((start, end))
    result.extend(data[index:])
    return result


def intersect_intervals(
    first: Sequence[Sequence[float]], second: Sequence[Sequence[float]]
) -> List[Interval]:
    """Return pairwise intersections of two interval lists.  O(n log n + m log m)."""
    left = merge_intervals(first)
    right = merge_intervals(second)
    result: List[Interval] = []
    i = j = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if start <= end:
            result.append((start, end))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return result


def total_covered_length(intervals: Iterable[Sequence[float]]) -> float:
    """Total length covered by the union of the intervals.  O(n log n)."""
    return sum(end - start for start, end in merge_intervals(intervals))


def coverage_count(intervals: Iterable[Sequence[float]], point: float) -> int:
    """How many intervals contain *point* (inclusive).  O(n)."""
    if isinstance(point, bool) or not isinstance(point, (int, float)):
        raise TypeError("point must be a number")
    return sum(
        1 for start, end in _validate_all(intervals) if start <= point <= end
    )


def max_overlap(intervals: Iterable[Sequence[float]]) -> int:
    """Maximum number of intervals overlapping at one point.  O(n log n).

    Equivalent to the minimum number of "meeting rooms" required.
    """
    events: List[Tuple[float, int]] = []
    for start, end in _validate_all(intervals):
        events.append((start, 1))
        events.append((end, -1))
    # At equal coordinates start (+1) is processed before end (-1).
    events.sort(key=lambda event: (event[0], -event[1]))
    current = best = 0
    for _, delta in events:
        current += delta
        best = max(best, current)
    return best


def merge_adjacent(intervals: Iterable[Sequence[float]], gap: float = 0.0) -> List[Interval]:
    """Merge intervals whose gap is at most *gap* (0 merges touching ones)."""
    if isinstance(gap, bool) or not isinstance(gap, (int, float)) or gap < 0:
        raise ValueError("gap must be a non-negative number")
    data = sorted(_validate_all(intervals))
    merged: List[Interval] = []
    for start, end in data:
        if merged and start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _naive_total_length(intervals: Sequence[Interval]) -> float:
    """Reference length via a fine integer grid of unit cells.  O(span * n)."""
    if not intervals:
        return 0.0
    low = min(start for start, _ in intervals)
    high = max(end for _, end in intervals)
    if high == low:
        return 0.0
    covered = 0
    for step in range(int(low), int(high)):
        midpoint = step + 0.5
        if any(start <= midpoint < end for start, end in intervals):
            covered += 1
    return float(covered)


def main() -> None:
    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [
        (1.0, 6.0),
        (8.0, 10.0),
        (15.0, 18.0),
    ]
    assert merge_intervals([[1, 2], [2, 3]]) == [(1.0, 3.0)]   # touching
    assert merge_intervals([]) == []
    assert merge_intervals([[5, 5]]) == [(5.0, 5.0)]

    assert insert_interval([[1, 3], [6, 9]], [2, 5]) == [(1.0, 5.0), (6.0, 9.0)]
    assert insert_interval(
        [[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], [4, 8]
    ) == [(1.0, 2.0), (3.0, 10.0), (12.0, 16.0)]
    assert insert_interval([], [4, 8]) == [(4.0, 8.0)]

    assert intersect_intervals(
        [[0, 2], [5, 10], [13, 23], [24, 25]],
        [[1, 5], [8, 12], [15, 24], [25, 26]],
    ) == [
        (1.0, 2.0),
        (5.0, 5.0),
        (8.0, 10.0),
        (15.0, 23.0),
        (24.0, 24.0),
        (25.0, 25.0),
    ]
    assert intersect_intervals([[1, 2]], [[3, 4]]) == []

    assert total_covered_length([[1, 3], [2, 6], [8, 10]]) == 7.0
    assert total_covered_length([[1, 2], [2, 3], [3, 4]]) == 3.0
    assert coverage_count([[1, 5], [3, 7]], 3) == 2
    assert coverage_count([[1, 5], [3, 7]], 8) == 0

    assert max_overlap([[0, 30], [5, 10], [15, 20]]) == 2
    assert max_overlap([[7, 10], [2, 4]]) == 1
    assert max_overlap([[1, 4], [4, 5]]) == 2    # share the point 4
    assert max_overlap([]) == 0

    assert merge_adjacent([[1, 2], [2.5, 3]], gap=0.5) == [(1.0, 3.0)]
    assert merge_adjacent([[1, 2], [3, 4]], gap=0.0) == [(1.0, 2.0), (3.0, 4.0)]

    rng = random.Random(777)
    for _ in range(80):
        intervals: List[Interval] = []
        for _ in range(rng.randint(0, 8)):
            start = rng.randint(0, 20)
            end = start + rng.randint(0, 5)
            intervals.append((float(start), float(end)))
        merged = merge_intervals(intervals)
        assert all(a[1] <= b[0] for a, b in zip(merged, merged[1:]))
        for index in range(len(merged) - 1):
            assert merged[index][1] < merged[index + 1][0]
        sampled = _naive_total_length(intervals)
        assert abs(total_covered_length(intervals) - sampled) < 1e-9, intervals

    for action in (
        lambda: merge_intervals([(3, 1)]),
        lambda: merge_intervals([(1, 2, 3)]),
        lambda: insert_interval([[5, 6], [1, 2]], [3, 4]),
        lambda: coverage_count([[1, 2]], "x"),
        lambda: merge_adjacent([[1, 2]], gap=-1),
        lambda: max_overlap([("a", 1)]),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid interval input was accepted")

    print("Self-test: merge/insert/intersect/coverage/max-overlap passed.")
    print(f"merged: {merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])}")
    print(f"max concurrent meetings: {max_overlap([[0, 30], [5, 10], [15, 20]])}")
    print(f"total covered length: {total_covered_length([[1, 3], [2, 6], [8, 10]])}")


if __name__ == "__main__":
    main()
