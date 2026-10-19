"""Core graph algorithms on an adjacency-list graph.

Implemented:

* breadth-first search (BFS) with hop distances        - O(V + E)
* depth-first search (DFS)                              - O(V + E)
* Dijkstra shortest paths (non-negative weights)        - O((V + E) log V)
* Kahn topological sort (directed acyclic graphs)       - O(V + E)
* directed cycle detection (DFS colours)                - O(V + E)
* undirected cycle detection (parent-aware DFS)         - O(V + E)
* connected components (undirected graphs)              - O(V + E)

Vertices are hashable labels (the demo uses strings).  Space is O(V + E) for
the graph plus O(V) for each algorithm's bookkeeping.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, Hashable, List, Optional, Set, Tuple

Vertex = Hashable
Edge = Tuple[Vertex, Vertex, float]


class Graph:
    """A weighted graph stored as ``vertex -> {neighbour: weight}``."""

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self._adj: Dict[Vertex, Dict[Vertex, float]] = {}

    def add_vertex(self, vertex: Vertex) -> None:
        self._adj.setdefault(vertex, {})

    def add_edge(self, source: Vertex, target: Vertex, weight: float = 1.0) -> None:
        """Add an edge.  A negative weight is stored but rejected by Dijkstra."""
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise TypeError("edge weight must be a number")
        self.add_vertex(source)
        self.add_vertex(target)
        self._adj[source][target] = float(weight)
        if not self.directed:
            self._adj[target][source] = float(weight)

    def vertices(self) -> List[Vertex]:
        return list(self._adj)

    def neighbors(self, vertex: Vertex) -> Dict[Vertex, float]:
        if vertex not in self._adj:
            raise KeyError(f"unknown vertex: {vertex!r}")
        return self._adj[vertex]

    def edges(self) -> List[Edge]:
        """Return directed arcs.  Undirected edges appear once per direction."""
        result: List[Edge] = []
        for source, targets in self._adj.items():
            for target, weight in targets.items():
                result.append((source, target, weight))
        return result

    def __len__(self) -> int:
        return len(self._adj)

    def __contains__(self, vertex: Vertex) -> bool:
        return vertex in self._adj


def bfs(graph: Graph, start: Vertex) -> Tuple[List[Vertex], Dict[Vertex, int]]:
    """Breadth-first traversal order and unweighted hop distances.

    Raises KeyError when *start* is not a graph vertex.
    """
    if start not in graph:
        raise KeyError(f"unknown start vertex: {start!r}")
    order: List[Vertex] = []
    distance: Dict[Vertex, int] = {start: 0}
    queue = deque([start])
    while queue:
        vertex = queue.popleft()
        order.append(vertex)
        for neighbour in graph.neighbors(vertex):
            if neighbour not in distance:
                distance[neighbour] = distance[vertex] + 1
                queue.append(neighbour)
    return order, distance


def dfs(graph: Graph, start: Vertex) -> List[Vertex]:
    """Iterative depth-first traversal order from *start*."""
    if start not in graph:
        raise KeyError(f"unknown start vertex: {start!r}")
    order: List[Vertex] = []
    visited: Set[Vertex] = set()
    stack = [start]
    while stack:
        vertex = stack.pop()
        if vertex in visited:
            continue
        visited.add(vertex)
        order.append(vertex)
        for neighbour in reversed(list(graph.neighbors(vertex))):
            if neighbour not in visited:
                stack.append(neighbour)
    return order


def dijkstra(
    graph: Graph, start: Vertex
) -> Tuple[Dict[Vertex, float], Dict[Vertex, Optional[Vertex]]]:
    """Shortest distances and predecessor map from *start*.

    Raises:
        KeyError: unknown start vertex.
        ValueError: if any edge weight is negative.
    """
    if start not in graph:
        raise KeyError(f"unknown start vertex: {start!r}")
    if any(weight < 0 for _, _, weight in graph.edges()):
        raise ValueError("Dijkstra requires non-negative edge weights")
    distance: Dict[Vertex, float] = {start: 0.0}
    previous: Dict[Vertex, Optional[Vertex]] = {start: None}
    heap: List[Tuple[float, Vertex]] = [(0.0, start)]
    settled: Set[Vertex] = set()
    while heap:
        current, vertex = heapq.heappop(heap)
        if vertex in settled:
            continue
        settled.add(vertex)
        for neighbour, weight in graph.neighbors(vertex).items():
            candidate = current + weight
            if candidate < distance.get(neighbour, float("inf")):
                distance[neighbour] = candidate
                previous[neighbour] = vertex
                heapq.heappush(heap, (candidate, neighbour))
    return distance, previous


def reconstruct_path(
    previous: Dict[Vertex, Optional[Vertex]], start: Vertex, end: Vertex
) -> Optional[List[Vertex]]:
    """Rebuild a path from a predecessor map, or None when unreachable."""
    if end not in previous:
        return None
    path: List[Vertex] = []
    current: Optional[Vertex] = end
    while current is not None:
        path.append(current)
        if current == start:
            break
        current = previous[current]
    path.reverse()
    return path if path and path[0] == start else None


def topological_sort(graph: Graph) -> List[Vertex]:
    """Kahn's algorithm.  Raises ValueError for undirected or cyclic graphs."""
    if not graph.directed:
        raise ValueError("topological sort requires a directed graph")
    indegree = {vertex: 0 for vertex in graph.vertices()}
    for source in graph.vertices():
        for target in graph.neighbors(source):
            indegree[target] += 1
    queue = deque(vertex for vertex in graph.vertices() if indegree[vertex] == 0)
    order: List[Vertex] = []
    while queue:
        vertex = queue.popleft()
        order.append(vertex)
        for neighbour in graph.neighbors(vertex):
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                queue.append(neighbour)
    if len(order) != len(graph):
        raise ValueError("graph contains a cycle; topological order is undefined")
    return order


def _directed_cycle(graph: Graph) -> bool:
    colour: Dict[Vertex, int] = {vertex: 0 for vertex in graph.vertices()}  # 0/1/2

    def visit(vertex: Vertex) -> bool:
        colour[vertex] = 1
        for neighbour in graph.neighbors(vertex):
            if colour[neighbour] == 1:
                return True
            if colour[neighbour] == 0 and visit(neighbour):
                return True
        colour[vertex] = 2
        return False

    return any(colour[vertex] == 0 and visit(vertex) for vertex in graph.vertices())


def _undirected_cycle(graph: Graph) -> bool:
    visited: Set[Vertex] = set()

    def visit(vertex: Vertex, parent: Optional[Vertex]) -> bool:
        visited.add(vertex)
        for neighbour in graph.neighbors(vertex):
            if neighbour not in visited:
                if visit(neighbour, vertex):
                    return True
            elif neighbour != parent:
                return True
        return False

    return any(vertex not in visited and visit(vertex, None) for vertex in graph.vertices())


def has_cycle(graph: Graph) -> bool:
    """Detect a cycle in a directed or undirected graph.  O(V + E)."""
    return _directed_cycle(graph) if graph.directed else _undirected_cycle(graph)


def connected_components(graph: Graph) -> List[List[Vertex]]:
    """Return components of an undirected graph.  Raises for directed graphs."""
    if graph.directed:
        raise ValueError("connected_components requires an undirected graph")
    seen: Set[Vertex] = set()
    components: List[List[Vertex]] = []
    for vertex in graph.vertices():
        if vertex in seen:
            continue
        order, _ = bfs(graph, vertex)
        seen.update(order)
        components.append(order)
    return components


def main() -> None:
    undirected = Graph()
    for source, target in [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]:
        undirected.add_edge(source, target)
    undirected.add_vertex("F")

    order, distance = bfs(undirected, "A")
    assert order == ["A", "B", "C", "D", "E"], order
    assert distance == {"A": 0, "B": 1, "C": 1, "D": 2, "E": 3}, distance
    assert dfs(undirected, "A") == ["A", "B", "D", "C", "E"]  # deterministic stack order

    components = connected_components(undirected)
    assert sorted(sorted(component) for component in components) == [
        ["A", "B", "C", "D", "E"],
        ["F"],
    ]
    assert has_cycle(undirected) is True   # A-B-D-C-A
    tree = Graph()
    tree.add_edge("A", "B")
    tree.add_edge("B", "C")
    tree.add_edge("A", "D")
    assert not has_cycle(tree)
    undirected.add_edge("E", "A")
    assert has_cycle(undirected)
    try:
        topological_sort(undirected)
    except ValueError:
        pass
    else:
        raise AssertionError("topological_sort accepted an undirected graph")
    try:
        connected_components(Graph(directed=True))
    except ValueError:
        pass
    else:
        raise AssertionError("connected_components accepted a directed graph")

    weighted = Graph(directed=True)
    weighted.add_edge("A", "B", 4)
    weighted.add_edge("A", "C", 1)
    weighted.add_edge("C", "B", 2)
    weighted.add_edge("B", "D", 5)
    weighted.add_edge("C", "D", 8)
    weighted.add_edge("D", "E", 3)
    distances, previous = dijkstra(weighted, "A")
    assert distances == {"A": 0.0, "B": 3.0, "C": 1.0, "D": 8.0, "E": 11.0}, distances
    path = reconstruct_path(previous, "A", "E")
    assert path == ["A", "C", "B", "D", "E"], path
    assert reconstruct_path(previous, "A", "Z") is None

    topo = topological_sort(weighted)
    position = {vertex: index for index, vertex in enumerate(topo)}
    for source, target, _ in weighted.edges():
        assert position[source] < position[target]
    assert len(topo) == 5 and not has_cycle(weighted)

    weighted.add_edge("E", "A", 1)
    assert has_cycle(weighted)
    try:
        topological_sort(weighted)
    except ValueError:
        pass
    else:
        raise AssertionError("topological_sort accepted a cycle")

    negative = Graph()
    negative.add_edge("A", "B", -1)
    try:
        dijkstra(negative, "A")
    except ValueError:
        pass
    else:
        raise AssertionError("Dijkstra accepted a negative weight")

    print("Self-test: BFS, DFS, Dijkstra, topological sort, cycles and components passed.")
    print(f"BFS order: {order}")
    print(f"shortest A->E: {path} = {distances['E']}")
    print(f"topological order: {topo}")


if __name__ == "__main__":
    main()
