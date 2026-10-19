"""Disjoint-set union (union-find) with path compression and union by rank.

Complexity with both optimizations, for n elements and m operations:

* ``find``  - O(alpha(n)) amortized (inverse Ackermann, effectively constant)
* ``union`` - O(alpha(n)) amortized
* space     - O(n)

The module also provides Kruskal's minimum spanning tree and undirected cycle
detection built on the same structure.  The demo checks component bookkeeping,
path compression, MST weight/edges and cycle detection.
"""

from __future__ import annotations

from typing import Dict, Hashable, Iterable, List, Sequence, Tuple

Element = Hashable
WeightedEdge = Tuple[int, int, float]


class UnionFind:
    """Union-find over hashable elements added at construction time."""

    def __init__(self, elements: Iterable[Element] = ()) -> None:
        self._parent: Dict[Element, Element] = {}
        self._rank: Dict[Element, int] = {}
        self._size: Dict[Element, int] = {}
        self._count = 0
        for element in elements:
            self.add(element)

    def add(self, element: Element) -> bool:
        """Add a singleton set; return False if already present."""
        if element in self._parent:
            return False
        self._parent[element] = element
        self._rank[element] = 0
        self._size[element] = 1
        self._count += 1
        return True

    def find(self, element: Element) -> Element:
        """Return the representative of *element* with full path compression."""
        if element not in self._parent:
            raise KeyError(f"unknown element: {element!r}")
        root = element
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[element] != element:
            parent = self._parent[element]
            self._parent[element] = root
            element = parent
        return root

    def union(self, first: Element, second: Element) -> bool:
        """Merge the sets of *first* and *second*.

        Returns True when a merge happened, False when they were already in the
        same set.
        """
        root_first = self.find(first)
        root_second = self.find(second)
        if root_first == root_second:
            return False
        if self._rank[root_first] < self._rank[root_second]:
            root_first, root_second = root_second, root_first
        self._parent[root_second] = root_first
        self._size[root_first] += self._size[root_second]
        if self._rank[root_first] == self._rank[root_second]:
            self._rank[root_first] += 1
        self._count -= 1
        return True

    def connected(self, first: Element, second: Element) -> bool:
        return self.find(first) == self.find(second)

    def size_of(self, element: Element) -> int:
        """Number of elements in *element*'s set."""
        return self._size[self.find(element)]

    @property
    def component_count(self) -> int:
        return self._count

    def groups(self) -> List[List[Element]]:
        """Return all components as lists of their elements.  O(n)."""
        buckets: Dict[Element, List[Element]] = {}
        for element in self._parent:
            buckets.setdefault(self.find(element), []).append(element)
        return list(buckets.values())

    def __len__(self) -> int:
        return len(self._parent)


def kruskal(vertex_count: int, edges: Sequence[WeightedEdge]) -> Tuple[float, List[WeightedEdge]]:
    """Return (total weight, chosen edges) of a minimum spanning forest.

    Time: O(E log E) dominated by sorting.  Space: O(V + E).

    Raises:
        ValueError: for a negative vertex count or an endpoint out of range.
        TypeError: for a non-numeric weight.
    """
    if isinstance(vertex_count, bool) or not isinstance(vertex_count, int):
        raise TypeError("vertex_count must be an int")
    if vertex_count < 0:
        raise ValueError("vertex_count must be non-negative")
    checked: List[WeightedEdge] = []
    for edge in edges:
        if len(edge) != 3:
            raise ValueError("each edge must be (source, target, weight)")
        source, target, weight = edge
        if not (0 <= source < vertex_count and 0 <= target < vertex_count):
            raise ValueError(f"edge endpoint outside 0..{vertex_count - 1}: {edge!r}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise TypeError("edge weight must be a number")
        checked.append((source, target, float(weight)))
    forest = UnionFind(range(vertex_count))
    chosen: List[WeightedEdge] = []
    total = 0.0
    for edge in sorted(checked, key=lambda item: item[2]):
        source, target, weight = edge
        if forest.union(source, target):
            chosen.append(edge)
            total += weight
            if len(chosen) == vertex_count - 1:
                break
    return total, chosen


def has_undirected_cycle(vertex_count: int, edges: Sequence[Tuple[int, int]]) -> bool:
    """Detect a cycle in an undirected graph using union-find.  O(E alpha(V))."""
    if isinstance(vertex_count, bool) or not isinstance(vertex_count, int):
        raise TypeError("vertex_count must be an int")
    if vertex_count < 0:
        raise ValueError("vertex_count must be non-negative")
    forest = UnionFind(range(vertex_count))
    for source, target in edges:
        if not (0 <= source < vertex_count and 0 <= target < vertex_count):
            raise ValueError("edge endpoint out of range")
        if not forest.union(source, target):
            return True
    return False


def main() -> None:
    forest = UnionFind(["a", "b", "c", "d", "e"])
    assert forest.component_count == 5
    assert forest.union("a", "b") is True
    assert forest.union("b", "c") is True
    assert forest.union("a", "c") is False
    assert forest.connected("a", "c") is True
    assert forest.connected("a", "d") is False
    assert forest.size_of("c") == 3
    assert forest.component_count == 3
    assert forest.add("a") is False
    assert sorted(sorted(group) for group in forest.groups()) == [
        ["a", "b", "c"],
        ["d"],
        ["e"],
    ]

    # Path compression still yields correct representatives after many finds.
    for _ in range(10):
        assert forest.find("c") == forest.find("a")

    edges: List[WeightedEdge] = [
        (0, 1, 1),
        (1, 2, 2),
        (0, 2, 3),
        (2, 3, 4),
        (3, 4, 5),
        (1, 4, 10),
    ]
    total, chosen = kruskal(5, edges)
    assert total == 12.0, total
    assert len(chosen) == 4
    assert sorted(weight for _, _, weight in chosen) == [1.0, 2.0, 4.0, 5.0]

    # Disconnected graph -> minimum spanning forest with fewer edges.
    forest_total, forest_edges = kruskal(4, [(0, 1, 2), (2, 3, 7)])
    assert forest_total == 9.0 and len(forest_edges) == 2

    assert has_undirected_cycle(3, [(0, 1), (1, 2), (2, 0)]) is True
    assert has_undirected_cycle(4, [(0, 1), (1, 2), (2, 3)]) is False

    for action in (
        lambda: forest.find("zzz"),
        lambda: kruskal(2, [(0, 5, 1)]),
        lambda: kruskal(-1, []),
        lambda: has_undirected_cycle(2, [(0, 2)]),
    ):
        try:
            action()
        except (KeyError, ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid union-find input was accepted")

    print("Self-test: union-find compression, Kruskal MST and cycle detection passed.")
    print(f"MST weight={total}, edges={chosen}")
    print(f"components after unions: {sorted(sorted(g) for g in forest.groups())}")


if __name__ == "__main__":
    main()
