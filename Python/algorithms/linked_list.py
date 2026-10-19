"""Singly linked list with the usual interview operations.

Operations and complexity (n = list length):

* append / prepend                   - O(1)
* insert / remove at index           - O(n) traversal, O(1) pointer edits
* delete by value / get / find        - O(n)
* reverse in place                    - O(n) time, O(1) space
* find middle (tortoise and hare)     - O(n) time, O(1) space
* n-th node from the end              - O(n) time, O(1) space
* cycle detection (Floyd)             - O(n) time, O(1) space
* merge two sorted lists              - O(n + m) time, O(n + m) new nodes

The implementation maintains a tail pointer so appends stay constant time.
The demo builds lists, mutates them, and checks every assertion.
"""

from __future__ import annotations

from typing import Iterable, Iterator, List, Optional


class Node:
    """A single linked-list node."""

    __slots__ = ("value", "next")

    def __init__(self, value: object, next_node: Optional["Node"] = None) -> None:
        self.value = value
        self.next = next_node

    def __repr__(self) -> str:
        return f"Node({self.value!r})"


def has_cycle(head: Optional[Node]) -> bool:
    """Return True when the chain starting at *head* contains a cycle.

    Floyd's tortoise-and-hare algorithm: O(n) time, O(1) space.
    """
    slow = fast = head
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False


class SinglyLinkedList:
    """A singly linked list with a maintained tail pointer."""

    def __init__(self, values: Iterable[object] = ()) -> None:
        self.head: Optional[Node] = None
        self.tail: Optional[Node] = None
        self._size = 0
        for value in values:
            self.append(value)

    # -- basic protocol -----------------------------------------------------
    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[object]:
        current = self.head
        while current is not None:
            yield current.value
            current = current.next

    def __repr__(self) -> str:
        return f"SinglyLinkedList({self.to_list()!r})"

    def to_list(self) -> List[object]:
        return list(self)

    # -- insertion ----------------------------------------------------------
    def append(self, value: object) -> None:
        """Add *value* at the end.  O(1)."""
        node = Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._size += 1

    def prepend(self, value: object) -> None:
        """Add *value* at the front.  O(1)."""
        self.head = Node(value, self.head)
        if self.tail is None:
            self.tail = self.head
        self._size += 1

    def insert(self, index: int, value: object) -> None:
        """Insert *value* so it ends up at position *index*.  O(n).

        Raises IndexError unless ``0 <= index <= len(self)``.
        """
        if not 0 <= index <= self._size:
            raise IndexError(f"insert index {index} out of range")
        if index == 0:
            self.prepend(value)
            return
        if index == self._size:
            self.append(value)
            return
        previous = self._node_at(index - 1)
        previous.next = Node(value, previous.next)
        self._size += 1

    # -- access -------------------------------------------------------------
    def _node_at(self, index: int) -> Node:
        if not 0 <= index < self._size:
            raise IndexError(f"index {index} out of range")
        current = self.head
        for _ in range(index):
            assert current is not None
            current = current.next
        assert current is not None
        return current

    def get(self, index: int) -> object:
        """Return the value at *index*.  O(n)."""
        return self._node_at(index).value

    def find(self, value: object) -> int:
        """Return the first index of *value*, or -1.  O(n)."""
        for index, current in enumerate(self):
            if current == value:
                return index
        return -1

    # -- deletion -----------------------------------------------------------
    def delete(self, value: object) -> bool:
        """Delete the first occurrence of *value*.  Return True if removed."""
        previous: Optional[Node] = None
        current = self.head
        while current is not None:
            if current.value == value:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                if current is self.tail:
                    self.tail = previous
                self._size -= 1
                return True
            previous, current = current, current.next
        return False

    def remove_at(self, index: int) -> object:
        """Remove and return the value at *index*.  O(n)."""
        if not 0 <= index < self._size:
            raise IndexError(f"index {index} out of range")
        previous: Optional[Node] = None
        current = self.head
        for _ in range(index):
            previous, current = current, current.next
        assert current is not None
        if previous is None:
            self.head = current.next
        else:
            previous.next = current.next
        if current is self.tail:
            self.tail = previous
        self._size -= 1
        return current.value

    # -- list algorithms ----------------------------------------------------
    def reverse(self) -> None:
        """Reverse the list in place.  O(n) time, O(1) space."""
        previous: Optional[Node] = None
        current = self.head
        self.tail = self.head
        while current is not None:
            following = current.next
            current.next = previous
            previous = current
            current = following
        self.head = previous

    def middle(self) -> object:
        """Return the middle value (second middle when even).  O(n)."""
        if self.head is None:
            raise ValueError("empty list has no middle")
        slow = fast = self.head
        while fast is not None and fast.next is not None:
            slow = slow.next
            fast = fast.next.next
        assert slow is not None
        return slow.value

    def nth_from_end(self, n: int) -> object:
        """Return the n-th value counting from 1 at the tail.  O(n)."""
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError("n must be an int")
        if n < 1 or n > self._size:
            raise IndexError(f"n={n} is outside 1..{self._size}")
        fast = self.head
        for _ in range(n):
            assert fast is not None
            fast = fast.next
        slow = self.head
        while fast is not None:
            assert slow is not None
            slow = slow.next
            fast = fast.next
        assert slow is not None
        return slow.value

    def is_palindrome(self) -> bool:
        """Check palindrome using a reversed copy.  O(n) time/space."""
        values = self.to_list()
        return values == values[::-1]


def merge_sorted(left: SinglyLinkedList, right: SinglyLinkedList) -> SinglyLinkedList:
    """Merge two sorted lists into a new sorted list.  O(n + m) time/space."""
    result = SinglyLinkedList()
    left_node, right_node = left.head, right.head
    while left_node is not None and right_node is not None:
        if left_node.value <= right_node.value:  # type: ignore[operator]
            result.append(left_node.value)
            left_node = left_node.next
        else:
            result.append(right_node.value)
            right_node = right_node.next
    while left_node is not None:
        result.append(left_node.value)
        left_node = left_node.next
    while right_node is not None:
        result.append(right_node.value)
        right_node = right_node.next
    return result


def main() -> None:
    values = SinglyLinkedList([2, 4, 6])
    assert len(values) == 3 and values.to_list() == [2, 4, 6]
    assert values.head is not None and values.head.value == 2
    assert values.tail is not None and values.tail.value == 6

    values.append(8)
    values.prepend(0)
    values.insert(3, 5)
    assert values.to_list() == [0, 2, 4, 5, 6, 8]
    assert values.get(3) == 5 and values.find(6) == 4 and values.find(99) == -1
    assert values.tail is not None and values.tail.value == 8

    assert values.remove_at(3) == 5
    assert values.delete(0) is True
    assert values.delete(99) is False
    assert values.to_list() == [2, 4, 6, 8]
    assert values.middle() == 6            # second middle for even length
    assert values.nth_from_end(1) == 8
    assert values.nth_from_end(4) == 2
    assert values.is_palindrome() is False

    values.reverse()
    assert values.to_list() == [8, 6, 4, 2]
    assert values.tail is not None and values.tail.value == 2
    values.append(1)
    assert values.to_list() == [8, 6, 4, 2, 1]

    merged = merge_sorted(SinglyLinkedList([1, 4, 7]), SinglyLinkedList([2, 3, 9, 10]))
    assert merged.to_list() == [1, 2, 3, 4, 7, 9, 10]
    assert merged.tail is not None and merged.tail.value == 10

    # Cycle detection on a manually built chain.
    first, second, third = Node(1), Node(2), Node(3)
    first.next, second.next = second, third
    assert has_cycle(first) is False
    third.next = second
    assert has_cycle(first) is True

    for action in (
        lambda: values.get(99),
        lambda: values.insert(-1, 0),
        lambda: values.nth_from_end(0),
        lambda: SinglyLinkedList().middle(),
    ):
        try:
            action()
        except (IndexError, ValueError):
            pass
        else:
            raise AssertionError("invalid linked-list operation was accepted")

    print("Self-test: linked-list insertion, deletion, reversal and cycle checks passed.")
    print(f"final list: {values.to_list()}, merged: {merged.to_list()}")


if __name__ == "__main__":
    main()
