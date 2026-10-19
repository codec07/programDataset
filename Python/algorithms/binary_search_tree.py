"""Binary search tree with insertion, search, deletion and traversals.

Complexity (h = tree height, n = node count):

* insert / search / delete - O(h) time, O(1) extra space (iterative search,
  recursive insert/delete)
* min / max                  - O(h)
* inorder traversal           - O(n) time, O(n) space for the result
* height                     - O(n) worst
* k-th smallest               - O(h) with an iterative walk
* validation                 - O(n)

A random/balanced tree has h = O(log n); a sorted insertion order degrades to
h = O(n).  Duplicate keys are ignored (the tree stores a set of keys).
The demo exercises every operation, including corruption detection.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


class BSTNode:
    """A binary search tree node holding an integer key."""

    __slots__ = ("key", "left", "right")

    def __init__(self, key: int) -> None:
        self.key = key
        self.left: Optional["BSTNode"] = None
        self.right: Optional["BSTNode"] = None


class BinarySearchTree:
    """Unbalanced binary search tree over integer keys."""

    def __init__(self) -> None:
        self.root: Optional[BSTNode] = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        return isinstance(key, int) and not isinstance(key, bool) and self.contains(key)

    @staticmethod
    def _check_key(key: object) -> int:
        if isinstance(key, bool) or not isinstance(key, int):
            raise TypeError("BST keys must be integers")
        return key

    # -- insertion / search -------------------------------------------------
    def insert(self, key: int) -> bool:
        """Insert *key*; return False when it was already present.  O(h)."""
        key = self._check_key(key)
        if self.root is None:
            self.root = BSTNode(key)
            self._size = 1
            return True
        node = self.root
        while True:
            if key == node.key:
                return False
            if key < node.key:
                if node.left is None:
                    node.left = BSTNode(key)
                    self._size += 1
                    return True
                node = node.left
            else:
                if node.right is None:
                    node.right = BSTNode(key)
                    self._size += 1
                    return True
                node = node.right

    def contains(self, key: int) -> bool:
        """Return True when *key* is present.  O(h)."""
        key = self._check_key(key)
        node = self.root
        while node is not None:
            if key == node.key:
                return True
            node = node.left if key < node.key else node.right
        return False

    # -- deletion -----------------------------------------------------------
    def delete(self, key: int) -> bool:
        """Remove *key*; return True when found and removed.  O(h)."""
        key = self._check_key(key)
        self.root, removed = self._delete(self.root, key)
        if removed:
            self._size -= 1
        return removed

    def _delete(self, node: Optional[BSTNode], key: int) -> Tuple[Optional[BSTNode], bool]:
        if node is None:
            return None, False
        if key < node.key:
            node.left, removed = self._delete(node.left, key)
            return node, removed
        if key > node.key:
            node.right, removed = self._delete(node.right, key)
            return node, removed
        # Found the node: zero or one child, then two children.
        if node.left is None:
            return node.right, True
        if node.right is None:
            return node.left, True
        successor = node.right
        while successor.left is not None:
            successor = successor.left
        node.key = successor.key
        node.right, _ = self._delete(node.right, successor.key)
        return node, True

    # -- extrema and traversals --------------------------------------------
    def minimum(self) -> int:
        if self.root is None:
            raise ValueError("minimum of empty tree")
        node = self.root
        while node.left is not None:
            node = node.left
        return node.key

    def maximum(self) -> int:
        if self.root is None:
            raise ValueError("maximum of empty tree")
        node = self.root
        while node.right is not None:
            node = node.right
        return node.key

    def inorder(self) -> List[int]:
        result: List[int] = []
        stack: List[BSTNode] = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            result.append(node.key)
            node = node.right
        return result

    def preorder(self) -> List[int]:
        result: List[int] = []
        stack = [self.root] if self.root is not None else []
        while stack:
            node = stack.pop()
            result.append(node.key)
            if node.right is not None:
                stack.append(node.right)
            if node.left is not None:
                stack.append(node.left)
        return result

    def postorder(self) -> List[int]:
        result: List[int] = []
        stack: List[Tuple[BSTNode, bool]] = (
            [(self.root, False)] if self.root is not None else []
        )
        while stack:
            node, visited = stack.pop()
            if visited:
                result.append(node.key)
            else:
                stack.append((node, True))
                if node.right is not None:
                    stack.append((node.right, False))
                if node.left is not None:
                    stack.append((node.left, False))
        return result

    def height(self) -> int:
        """Return the number of edges on the longest root-to-leaf path (-1 if empty)."""
        def measure(node: Optional[BSTNode]) -> int:
            if node is None:
                return -1
            return 1 + max(measure(node.left), measure(node.right))

        return measure(self.root)

    def kth_smallest(self, k: int) -> int:
        """Return the 1-based k-th smallest key.  Raises ValueError if absent."""
        if isinstance(k, bool) or not isinstance(k, int):
            raise TypeError("k must be an int")
        if k < 1 or k > self._size:
            raise ValueError(f"k={k} outside 1..{self._size}")
        stack: List[BSTNode] = []
        node = self.root
        while node is not None or stack:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            k -= 1
            if k == 0:
                return node.key
            node = node.right
        raise AssertionError("unreachable")

    def range_sum(self, low: int, high: int) -> int:
        """Sum of keys in the inclusive range [low, high].  O(n) worst."""
        if low > high:
            raise ValueError("low must not exceed high")
        total = 0
        stack = [self.root] if self.root is not None else []
        while stack:
            node = stack.pop()
            if low <= node.key <= high:
                total += node.key
            if node.left is not None and node.key > low:
                stack.append(node.left)
            if node.right is not None and node.key < high:
                stack.append(node.right)
        return total

    def is_valid(self) -> bool:
        """Check the BST ordering invariant with inclusive bounds.  O(n)."""
        def check(node: Optional[BSTNode], low: Optional[int], high: Optional[int]) -> bool:
            if node is None:
                return True
            if low is not None and node.key <= low:
                return False
            if high is not None and node.key >= high:
                return False
            return check(node.left, low, node.key) and check(node.right, node.key, high)

        return check(self.root, None, None)


def main() -> None:
    tree = BinarySearchTree()
    for key in (50, 30, 70, 20, 40, 60, 80, 30):
        tree.insert(key)
    assert len(tree) == 7, "duplicate key should be ignored"
    assert tree.inorder() == [20, 30, 40, 50, 60, 70, 80]
    assert tree.preorder() == [50, 30, 20, 40, 70, 60, 80]
    assert tree.postorder() == [20, 40, 30, 60, 80, 70, 50]
    assert tree.height() == 2
    assert tree.minimum() == 20 and tree.maximum() == 80
    assert tree.contains(60) and not tree.contains(65)
    assert tree.kth_smallest(1) == 20 and tree.kth_smallest(7) == 80
    assert tree.range_sum(30, 70) == 30 + 40 + 50 + 60 + 70
    assert tree.is_valid()

    assert tree.delete(20) is True        # leaf
    assert tree.delete(30) is True        # one child (40)
    assert tree.delete(70) is True        # two children (successor 80)
    assert tree.delete(999) is False
    assert tree.inorder() == [40, 50, 60, 80]
    assert len(tree) == 4 and tree.is_valid()

    # Deliberately break the ordering invariant.
    if tree.root is not None:
        tree.root.left = BSTNode(999)
    assert tree.is_valid() is False

    for action in (
        lambda: BinarySearchTree().minimum(),
        lambda: tree.kth_smallest(0),
        lambda: tree.insert("x"),  # type: ignore[arg-type]
        lambda: tree.range_sum(10, 0),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid BST operation was accepted")

    print("Self-test: BST insert/search/delete/traversals/validation passed.")
    print(f"remaining inorder: {tree.inorder()}, len={len(tree)}")


if __name__ == "__main__":
    main()
