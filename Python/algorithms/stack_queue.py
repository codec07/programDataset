"""Stack and queue data structures plus two classic applications.

Contents:

* ``Stack``                 - array-backed LIFO, O(1) push/pop/peek
* ``MinStack``              - stack with O(1) minimum via an auxiliary stack
* ``QueueTwoStacks``        - FIFO built from two stacks, amortized O(1)
* ``CircularQueue``         - fixed-capacity ring buffer, O(1) operations
* ``is_balanced_parentheses`` - bracket matching, O(n) time / O(n) space
* ``sliding_window_maximum``  - monotonic deque, O(n) time / O(k) space

All containers raise clear exceptions (IndexError/OverflowError/ValueError)
instead of returning sentinel values.  The self-test checks ordering,
wraparound, amortized queue behaviour and error paths.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, Iterator, List, Optional, Sequence


class Stack:
    """Last-in, first-out container backed by a Python list."""

    def __init__(self, items: Iterable[object] = ()) -> None:
        self._items: List[object] = list(items)

    def push(self, value: object) -> None:
        self._items.append(value)

    def pop(self) -> object:
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self) -> object:
        if not self._items:
            raise IndexError("peek at empty stack")
        return self._items[-1]

    def is_empty(self) -> bool:
        return not self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[object]:
        """Iterate from top to bottom without modifying the stack."""
        return iter(reversed(self._items))


class MinStack:
    """Stack supporting ``minimum()`` in O(1) time and O(n) extra space."""

    def __init__(self) -> None:
        self._items: List[tuple[object, object]] = []

    def push(self, value: float) -> None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("MinStack only accepts numbers")
        current_min = value if not self._items else min(value, self._items[-1][1])
        self._items.append((value, current_min))

    def pop(self) -> object:
        if not self._items:
            raise IndexError("pop from empty MinStack")
        return self._items.pop()[0]

    def peek(self) -> object:
        if not self._items:
            raise IndexError("peek at empty MinStack")
        return self._items[-1][0]

    def minimum(self) -> object:
        if not self._items:
            raise IndexError("minimum of empty MinStack")
        return self._items[-1][1]

    def __len__(self) -> int:
        return len(self._items)


class QueueTwoStacks:
    """FIFO queue implemented with an input stack and an output stack.

    Each element is moved at most once, so all operations are amortized O(1)
    time; space is O(n).
    """

    def __init__(self) -> None:
        self._incoming: List[object] = []
        self._outgoing: List[object] = []

    def enqueue(self, value: object) -> None:
        self._incoming.append(value)

    def _transfer(self) -> None:
        if not self._outgoing:
            while self._incoming:
                self._outgoing.append(self._incoming.pop())

    def dequeue(self) -> object:
        self._transfer()
        if not self._outgoing:
            raise IndexError("dequeue from empty queue")
        return self._outgoing.pop()

    def peek(self) -> object:
        self._transfer()
        if not self._outgoing:
            raise IndexError("peek at empty queue")
        return self._outgoing[-1]

    def is_empty(self) -> bool:
        return not self._incoming and not self._outgoing

    def __len__(self) -> int:
        return len(self._incoming) + len(self._outgoing)


class CircularQueue:
    """Fixed-capacity ring-buffer FIFO queue.  All operations O(1)."""

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an int")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._buffer: List[Optional[object]] = [None] * capacity
        self._head = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        return len(self._buffer)

    def enqueue(self, value: object) -> None:
        if self._size == self.capacity:
            raise OverflowError("circular queue is full")
        index = (self._head + self._size) % self.capacity
        self._buffer[index] = value
        self._size += 1

    def dequeue(self) -> object:
        if self._size == 0:
            raise IndexError("dequeue from empty circular queue")
        value = self._buffer[self._head]
        self._buffer[self._head] = None
        self._head = (self._head + 1) % self.capacity
        self._size -= 1
        return value

    def front(self) -> object:
        if self._size == 0:
            raise IndexError("front of empty circular queue")
        return self._buffer[self._head]

    def is_full(self) -> bool:
        return self._size == self.capacity

    def __len__(self) -> int:
        return self._size

    def to_list(self) -> List[object]:
        return [
            self._buffer[(self._head + offset) % self.capacity]
            for offset in range(self._size)
        ]


def is_balanced_parentheses(text: str) -> bool:
    """Return True if (), [] and {} are correctly nested and closed.

    Non-bracket characters are ignored.  O(n) time / O(n) space.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    pairs = {")": "(", "]": "[", "}": "{"}
    opening = set(pairs.values())
    stack: List[str] = []
    for character in text:
        if character in opening:
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                return False
    return not stack


def sliding_window_maximum(values: Sequence[float], window: int) -> List[float]:
    """Return the maximum of every contiguous window of size *window*.

    Uses a monotonic deque of indices: O(n) time / O(window) space.

    Raises ValueError for a non-positive or oversized window.
    """
    if isinstance(window, bool) or not isinstance(window, int):
        raise TypeError("window must be an int")
    if window <= 0 or window > len(values):
        raise ValueError("window must satisfy 1 <= window <= len(values)")
    candidates: Deque[int] = deque()
    result: List[float] = []
    for index, value in enumerate(values):
        while candidates and values[candidates[-1]] <= value:
            candidates.pop()
        candidates.append(index)
        if candidates[0] <= index - window:
            candidates.popleft()
        if index >= window - 1:
            result.append(values[candidates[0]])
    return result


def main() -> None:
    stack = Stack([1, 2])
    stack.push(3)
    assert list(stack) == [3, 2, 1]
    assert stack.peek() == 3 and stack.pop() == 3 and len(stack) == 2
    assert Stack().is_empty()

    minimums = MinStack()
    for value in (5, 3, 7, 2):
        minimums.push(value)
    assert minimums.minimum() == 2 and minimums.peek() == 2
    assert minimums.pop() == 2 and minimums.minimum() == 3

    queue = QueueTwoStacks()
    for value in range(5):
        queue.enqueue(value)
    assert queue.dequeue() == 0
    queue.enqueue(5)
    assert queue.peek() == 1
    assert [queue.dequeue() for _ in range(5)] == [1, 2, 3, 4, 5]
    assert queue.is_empty()

    ring = CircularQueue(3)
    ring.enqueue("a")
    ring.enqueue("b")
    assert ring.dequeue() == "a"
    ring.enqueue("c")
    ring.enqueue("d")
    assert ring.to_list() == ["b", "c", "d"] and ring.is_full()
    assert ring.front() == "b"
    assert ring.dequeue() == "b"
    ring.enqueue("e")
    assert ring.to_list() == ["c", "d", "e"]

    assert is_balanced_parentheses("({[]})") is True
    assert is_balanced_parentheses("([)]") is False
    assert is_balanced_parentheses("if (x[0] > 0) { y(); }") is True
    assert is_balanced_parentheses("((") is False
    assert is_balanced_parentheses("") is True

    assert sliding_window_maximum([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
    assert sliding_window_maximum([4], 1) == [4]

    for action in (
        lambda: Stack().pop(),
        lambda: MinStack().minimum(),
        lambda: QueueTwoStacks().dequeue(),
        lambda: CircularQueue(0),
        lambda: ring.enqueue("overflow"),
        lambda: sliding_window_maximum([1, 2], 0),
    ):
        try:
            action()
        except (IndexError, ValueError, OverflowError):
            pass
        else:
            raise AssertionError("invalid stack/queue operation was accepted")

    print("Self-test: stack, min-stack, two-stack queue, ring buffer and applications passed.")
    print(f"sliding maxima: {sliding_window_maximum([1, 3, -1, -3, 5, 3, 6, 7], 3)}")


if __name__ == "__main__":
    main()
