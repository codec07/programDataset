"""Classic sorting algorithms implemented from scratch.

Included algorithms and complexity (n = number of items, k = value range):

* insertion sort  - O(n^2) time, O(n) extra (operates on a copy)
* selection sort  - O(n^2) time, O(n) extra
* bubble sort     - O(n^2) time, O(n) extra, early exit on sorted input
* merge sort      - O(n log n) time, O(n) extra, stable
* quick sort      - O(n log n) average, O(n^2) worst, O(log n) stack
* heap sort       - O(n log n) time, O(1) extra (in place on the copy)
* counting sort   - O(n + k) time, O(k) extra, non-negative integers only

Every public function accepts any sequence and returns a new list, leaving the
caller's data untouched.  The demo sorts fixed random data (seeded), checks the
results against Python's built-in ``sorted`` and prints a small timing table.
"""

from __future__ import annotations

import random
import time
from typing import Callable, Dict, List, Sequence

Number = int | float


def insertion_sort(items: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *items* using insertion sort.

    Time: O(n^2) comparisons and moves, best case O(n) for sorted input.
    Space: O(n) for the result copy.
    """
    data = list(items)
    for index in range(1, len(data)):
        key = data[index]
        position = index - 1
        while position >= 0 and data[position] > key:
            data[position + 1] = data[position]
            position -= 1
        data[position + 1] = key
    return data


def selection_sort(items: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *items* using selection sort.

    Time: O(n^2) always. Space: O(n) for the result copy.
    """
    data = list(items)
    size = len(data)
    for index in range(size):
        smallest = index
        for candidate in range(index + 1, size):
            if data[candidate] < data[smallest]:
                smallest = candidate
        data[index], data[smallest] = data[smallest], data[index]
    return data


def bubble_sort(items: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *items* using bubble sort with early exit.

    Time: O(n^2) worst, O(n) best (already sorted). Space: O(n).
    """
    data = list(items)
    size = len(data)
    for end in range(size - 1, 0, -1):
        swapped = False
        for index in range(end):
            if data[index] > data[index + 1]:
                data[index], data[index + 1] = data[index + 1], data[index]
                swapped = True
        if not swapped:
            break
    return data


def merge_sort(items: Sequence[Number]) -> List[Number]:
    """Return a stable sorted copy of *items* using top-down merge sort.

    Time: O(n log n) in all cases. Space: O(n) auxiliary.
    """
    data = list(items)

    def sort_range(low: int, high: int) -> None:
        if high - low <= 1:
            return
        middle = (low + high) // 2
        sort_range(low, middle)
        sort_range(middle, high)
        left = data[low:middle]
        right = data[middle:high]
        i = j = 0
        write = low
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                data[write] = left[i]
                i += 1
            else:
                data[write] = right[j]
                j += 1
            write += 1
        while i < len(left):
            data[write] = left[i]
            i += 1
            write += 1
        while j < len(right):
            data[write] = right[j]
            j += 1
            write += 1

    sort_range(0, len(data))
    return data


def quick_sort(items: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *items* using Hoare-partition quick sort.

    The pivot is the middle element, which avoids the common worst case on
    already-sorted input.  Time: O(n log n) average, O(n^2) worst.
    Space: O(log n) average recursion stack, O(n) worst.
    """
    data = list(items)

    def sort_range(low: int, high: int) -> None:
        if low >= high:
            return
        pivot = data[(low + high) // 2]
        left, right = low, high
        while left <= right:
            while data[left] < pivot:
                left += 1
            while data[right] > pivot:
                right -= 1
            if left <= right:
                data[left], data[right] = data[right], data[left]
                left += 1
                right -= 1
        sort_range(low, right)
        sort_range(left, high)

    sort_range(0, len(data) - 1)
    return data


def _sift_down(data: List[Number], root: int, end: int) -> None:
    """Restore a max-heap property between *root* and *end* (inclusive)."""
    while 2 * root + 1 <= end:
        child = 2 * root + 1
        if child + 1 <= end and data[child] < data[child + 1]:
            child += 1
        if data[root] < data[child]:
            data[root], data[child] = data[child], data[root]
            root = child
        else:
            return


def heap_sort(items: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *items* using heap sort.

    Time: O(n log n) in all cases. Space: O(n) for the copy, O(1) auxiliary.
    """
    data = list(items)
    size = len(data)
    for start in range(size // 2 - 1, -1, -1):
        _sift_down(data, start, size - 1)
    for end in range(size - 1, 0, -1):
        data[0], data[end] = data[end], data[0]
        _sift_down(data, 0, end - 1)
    return data


def counting_sort(items: Sequence[int]) -> List[int]:
    """Return a sorted copy of non-negative integer *items*.

    Time: O(n + k) where k is the largest value. Space: O(k).

    Raises:
        TypeError: if any element is not an integer.
        ValueError: if any element is negative.
    """
    data = list(items)
    for value in data:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("counting_sort only accepts integers")
        if value < 0:
            raise ValueError("counting_sort only accepts non-negative values")
    if not data:
        return []
    counts = [0] * (max(data) + 1)
    for value in data:
        counts[value] += 1
    result: List[int] = []
    for value, count in enumerate(counts):
        result.extend([value] * count)
    return result


def is_sorted(items: Sequence[Number]) -> bool:
    """Return True when *items* is in non-decreasing order."""
    return all(items[i] <= items[i + 1] for i in range(len(items) - 1))


def _check_algorithm(name: str, function: Callable, case: Sequence[Number]) -> None:
    original = list(case)
    result = function(case)
    if list(case) != original:
        raise AssertionError(f"{name} mutated its input")
    if result != sorted(case):
        raise AssertionError(f"{name} produced {result} for {original}")


def main() -> None:
    rng = random.Random(20240517)
    algorithms: Dict[str, Callable] = {
        "insertion": insertion_sort,
        "selection": selection_sort,
        "bubble": bubble_sort,
        "merge": merge_sort,
        "quick": quick_sort,
        "heap": heap_sort,
    }
    cases: List[List[Number]] = [
        [],
        [42],
        [2, 1],
        [3, 3, 3, 3],
        list(range(25)),
        list(range(25, 0, -1)),
        [rng.randint(-100, 100) for _ in range(200)],
        [0.5, -1.25, 3.0, 0.5, 2.75],
    ]
    for name, algorithm in algorithms.items():
        for case in cases:
            _check_algorithm(name, algorithm, case)
    for case in ([], [0], [5, 0, 3, 1, 0, 9], [rng.randint(0, 50) for _ in range(100)]):
        assert counting_sort(case) == sorted(case), "counting sort mismatch"
    try:
        counting_sort([1, -2])
    except ValueError:
        pass
    else:
        raise AssertionError("counting_sort accepted a negative value")
    try:
        counting_sort([1.5, 2])
    except TypeError:
        pass
    else:
        raise AssertionError("counting_sort accepted a float")
    assert is_sorted(merge_sort(cases[-1]))

    print("Self-test: all sorts match sorted() on every fixed case.")
    print(f"{'algorithm':<12}{'n':>6}{'milliseconds':>14}")
    timing_data = [rng.randint(0, 10_000) for _ in range(800)]
    for name, algorithm in algorithms.items():
        start = time.perf_counter()
        result = algorithm(timing_data)
        elapsed = (time.perf_counter() - start) * 1000.0
        assert result == sorted(timing_data)
        print(f"{name:<12}{len(timing_data):>6}{elapsed:>14.3f}")
    print("Timing values vary between machines; correctness assertions passed.")


if __name__ == "__main__":
    main()
