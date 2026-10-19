"""LRU (least-recently-used) cache built from a hash map and a doubly linked list.

Design:

* ``dict`` maps key -> node for O(1) lookup.
* A doubly linked list keeps recency; the head is most recent, the tail is the
  eviction candidate.  Sentinel-free code updates head/tail explicitly.

Complexity: ``get`` and ``put`` are O(1) time; space is O(capacity).  Values may
be any Python object, including ``None``; use a sentinel default to distinguish
a stored ``None`` from a miss.

The demo checks recency updates, eviction order, capacity-one behaviour,
statistics and invalid construction.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class _Node:
    """Doubly linked list node holding one cache entry."""

    __slots__ = ("key", "value", "previous", "next")

    def __init__(self, key: object, value: object) -> None:
        self.key = key
        self.value = value
        self.previous: Optional["_Node"] = None
        self.next: Optional["_Node"] = None


class LRUCache:
    """Fixed-capacity least-recently-used cache with O(1) operations."""

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an int")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._nodes: Dict[object, _Node] = {}
        self._head: Optional[_Node] = None  # most recently used
        self._tail: Optional[_Node] = None  # least recently used
        self.hits = 0
        self.misses = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, key: object) -> bool:
        """Check membership without changing recency."""
        return key in self._nodes

    # -- linked-list helpers ------------------------------------------------
    def _unlink(self, node: _Node) -> None:
        if node.previous is not None:
            node.previous.next = node.next
        else:
            self._head = node.next
        if node.next is not None:
            node.next.previous = node.previous
        else:
            self._tail = node.previous
        node.previous = node.next = None

    def _push_front(self, node: _Node) -> None:
        node.previous = None
        node.next = self._head
        if self._head is not None:
            self._head.previous = node
        self._head = node
        if self._tail is None:
            self._tail = node

    def _move_to_front(self, node: _Node) -> None:
        if node is not self._head:
            self._unlink(node)
            self._push_front(node)

    # -- public API ---------------------------------------------------------
    _MISSING = object()

    def get(self, key: object, default: object = _MISSING) -> object:
        """Return the cached value and mark *key* most recent.

        Returns *default* (or raises KeyError when no default was supplied)
        when the key is absent.  O(1).
        """
        node = self._nodes.get(key)
        if node is None:
            self.misses += 1
            if default is LRUCache._MISSING:
                raise KeyError(key)
            return default
        self.hits += 1
        self._move_to_front(node)
        return node.value

    def put(self, key: object, value: object) -> Optional[Tuple[object, object]]:
        """Insert or update *key*.  Return the evicted (key, value) or None.

        Updating an existing key marks it most recent without changing length.
        """
        existing = self._nodes.get(key)
        if existing is not None:
            existing.value = value
            self._move_to_front(existing)
            return None
        node = _Node(key, value)
        self._nodes[key] = node
        self._push_front(node)
        if len(self._nodes) > self._capacity:
            assert self._tail is not None
            victim = self._tail
            self._unlink(victim)
            del self._nodes[victim.key]
            return victim.key, victim.value
        return None

    def peek(self, key: object, default: object = _MISSING) -> object:
        """Return a value without changing recency or statistics."""
        node = self._nodes.get(key)
        if node is None:
            if default is LRUCache._MISSING:
                raise KeyError(key)
            return default
        return node.value

    def items(self) -> List[Tuple[object, object]]:
        """List entries from most recent to least recent.  O(n)."""
        result: List[Tuple[object, object]] = []
        node = self._head
        while node is not None:
            result.append((node.key, node.value))
            node = node.next
        return result

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def main() -> None:
    cache = LRUCache(2)
    assert cache.put(1, "one") is None
    assert cache.put(2, "two") is None
    assert cache.get(1) == "one"                 # 1 becomes most recent
    evicted = cache.put(3, "three")              # evicts 2
    assert evicted == (2, "two"), evicted
    assert cache.get(2, "missing") == "missing"
    assert cache.get(3) == "three"
    assert cache.items() == [(3, "three"), (1, "one")]

    # Updating an existing key does not evict and refreshes recency.
    assert cache.put(1, "ONE") is None
    assert cache.items() == [(1, "ONE"), (3, "three")]
    assert cache.get(1) == "ONE"
    assert cache.put(4, "four") == (3, "three")

    # Capacity one: every new key evicts the previous one.
    tiny = LRUCache(1)
    tiny.put("a", 1)
    assert tiny.put("b", 2) == ("a", 1)
    assert tiny.get("a", None) is None and tiny.get("b") == 2
    assert tiny.items() == [("b", 2)]

    # None is a legal cached value; the sentinel default distinguishes misses.
    evicted_none = cache.put("none", None)
    assert evicted_none == (1, "ONE"), evicted_none
    assert cache.get("none") is None
    assert cache.peek("absent", "fallback") == "fallback"

    assert cache.hits == 4, cache.hits
    assert cache.misses == 1, cache.misses
    assert 0.0 < cache.hit_rate <= 1.0
    assert "none" in cache

    for action in (
        lambda: LRUCache(0),
        lambda: LRUCache(1.5),  # type: ignore[arg-type]
        lambda: cache.get("definitely-absent"),
        lambda: cache.peek("definitely-absent"),
    ):
        try:
            action()
        except (ValueError, TypeError, KeyError):
            pass
        else:
            raise AssertionError("invalid LRU operation was accepted")

    print("Self-test: LRU eviction order, recency updates and statistics passed.")
    print(f"items (most recent first): {cache.items()}")
    print(f"hits={cache.hits}, misses={cache.misses}, hit_rate={cache.hit_rate:.2f}")


if __name__ == "__main__":
    main()
