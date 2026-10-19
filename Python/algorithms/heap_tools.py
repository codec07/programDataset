"""Binary heap implementations and heap-based utilities.

A binary heap is a complete binary tree stored in an array:

* parent of i      = (i - 1) // 2
* children of i    = 2*i + 1, 2*i + 2

Complexity:

* push            - O(log n)
* pop             - O(log n)
* peek            - O(1)
* build (heapify) - O(n)
* heapsort        - O(n log n) time, O(n) extra (returns a new list)
* k smallest/largest - O(n log k) time, O(k) space

The demo compares the custom heaps against the standard-library ``heapq`` on
seeded random data, and checks ordering, stability of results by value and all
error paths.
"""

from __future__ import annotations

import heapq
import random
from typing import Iterable, List, Sequence

Number = int | float


class _Heap:
    """Shared array-backed binary-heap machinery."""

    def __init__(self, items: Iterable[Number] = ()) -> None:
        self._data: List[Number] = list(items)
        for index in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(index)

    def _before(self, first: Number, second: Number) -> bool:
        """Return True when *first* must be popped before *second*.

        The base implementation defines min-heap ordering; subclasses override
        it for max-heap behaviour.
        """
        return first < second

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if self._before(self._data[index], self._data[parent]):
                self._data[index], self._data[parent] = (
                    self._data[parent],
                    self._data[index],
                )
                index = parent
            else:
                return

    def _sift_down(self, index: int) -> None:
        size = len(self._data)
        while True:
            best = index
            left, right = 2 * index + 1, 2 * index + 2
            if left < size and self._before(self._data[left], self._data[best]):
                best = left
            if right < size and self._before(self._data[right], self._data[best]):
                best = right
            if best == index:
                return
            self._data[index], self._data[best] = self._data[best], self._data[index]
            index = best

    def push(self, value: Number) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("heap values must be numbers")
        self._data.append(value)
        self._sift_up(len(self._data) - 1)

    def pop(self) -> Number:
        if not self._data:
            raise IndexError("pop from empty heap")
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return top

    def peek(self) -> Number:
        if not self._data:
            raise IndexError("peek at empty heap")
        return self._data[0]

    def is_empty(self) -> bool:
        return not self._data

    def to_list(self) -> List[Number]:
        """Return a copy of the internal array (heap order, not sorted)."""
        return list(self._data)

    def __len__(self) -> int:
        return len(self._data)


class MinHeap(_Heap):
    """Min-heap: the smallest value is popped first."""

    def _before(self, first: Number, second: Number) -> bool:
        return first < second


class MaxHeap(_Heap):
    """Max-heap: the largest value is popped first."""

    def _before(self, first: Number, second: Number) -> bool:
        return first > second


def heapsort(values: Sequence[Number]) -> List[Number]:
    """Return a sorted copy of *values* using a min-heap.  O(n log n)."""
    heap = MinHeap(values)
    return [heap.pop() for _ in range(len(heap))]


def k_smallest(values: Sequence[Number], k: int) -> List[Number]:
    """Return the *k* smallest values in ascending order.  O(n log k)."""
    _check_k(k, len(values))
    if k == 0:
        return []
    heap = MaxHeap(values[:k])
    for value in values[k:]:
        if value < heap.peek():
            heap.pop()
            heap.push(value)
    return heapsort(heap.to_list())


def k_largest(values: Sequence[Number], k: int) -> List[Number]:
    """Return the *k* largest values in descending order.  O(n log k)."""
    _check_k(k, len(values))
    if k == 0:
        return []
    heap = MinHeap(values[:k])
    for value in values[k:]:
        if value > heap.peek():
            heap.pop()
            heap.push(value)
    return sorted(heap.to_list(), reverse=True)


def _check_k(k: int, size: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an int")
    if k < 0 or k > size:
        raise ValueError(f"k must satisfy 0 <= k <= {size}")


def main() -> None:
    rng = random.Random(1234)
    data = [rng.randint(-50, 50) for _ in range(60)]

    minimums = MinHeap(data)
    assert len(minimums) == len(data)
    assert minimums.peek() == min(data)
    popped = [minimums.pop() for _ in range(len(minimums))]
    assert popped == sorted(data) and minimums.is_empty()

    maximums = MaxHeap(data)
    assert maximums.peek() == max(data)
    popped_desc = [maximums.pop() for _ in range(len(maximums))]
    assert popped_desc == sorted(data, reverse=True)

    assert heapsort(data) == sorted(data)
    assert heapsort([]) == []
    assert heapsort([5]) == [5]

    for k in range(0, 11):
        assert k_smallest(data, k) == heapq.nsmallest(k, data)
        assert k_largest(data, k) == heapq.nlargest(k, data)

    # Push/pop interleaving matches a reference sorted structure.
    heap = MinHeap()
    reference: List[Number] = []
    for value in [5, -2, 9, 0, 4, 4, 7]:
        heap.push(value)
        reference.append(value)
    while reference:
        assert heap.pop() == min(reference)
        reference.remove(min(reference))

    for action in (
        lambda: MinHeap().pop(),
        lambda: MinHeap().peek(),
        lambda: k_smallest(data, -1),
        lambda: k_largest(data, len(data) + 1),
        lambda: MinHeap().push(True),  # type: ignore[arg-type]
    ):
        try:
            action()
        except (IndexError, ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid heap operation was accepted")

    print("Self-test: custom heaps agree with heapq and sorted() on seeded data.")
    print(f"heapsort(first 10)={heapsort(data)[:10]}")
    print(f"3 smallest={k_smallest(data, 3)}, 3 largest={k_largest(data, 3)}")


if __name__ == "__main__":
    main()
