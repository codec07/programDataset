"""Prefix tree (trie) for lowercase/ASCII words.

A trie stores words character by character.  With L = word length, n = number
of words and alphabet size A:

* insert / search / starts_with / delete - O(L) time
* count words with prefix                  - O(L + matches)
* list all words                           - O(total characters)

Space is O(total characters) in the worst case; each node holds a dictionary
of children plus an ``is_word`` flag.  Deletion prunes now-unused nodes.

The demo builds a small dictionary, checks prefix queries, deletion pruning,
longest common prefix of all inserted words, and error handling.
"""

from __future__ import annotations

from typing import Dict, List


class TrieNode:
    """One trie node: child links and an end-of-word marker."""

    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.is_word = False


class Trie:
    """A case-sensitive trie over strings (normally lowercase words)."""

    def __init__(self) -> None:
        self._root = TrieNode()
        self._word_count = 0

    def __len__(self) -> int:
        return self._word_count

    @staticmethod
    def _check_word(word: str) -> str:
        if not isinstance(word, str):
            raise TypeError("trie words must be strings")
        if not word:
            raise ValueError("trie words must be non-empty")
        return word

    def insert(self, word: str) -> bool:
        """Insert *word*; return False when it was already present.  O(L)."""
        word = self._check_word(word)
        node = self._root
        for character in word:
            node = node.children.setdefault(character, TrieNode())
        if node.is_word:
            return False
        node.is_word = True
        self._word_count += 1
        return True

    def search(self, word: str) -> bool:
        """Return True when *word* was inserted exactly.  O(L)."""
        word = self._check_word(word)
        node = self._find_node(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        """Return True when any inserted word begins with *prefix*.  O(L)."""
        prefix = self._check_word(prefix)
        return self._find_node(prefix) is not None

    def _find_node(self, text: str) -> TrieNode | None:
        node = self._root
        for character in text:
            node = node.children.get(character)  # type: ignore[assignment]
            if node is None:
                return None
        return node

    def count_words_with_prefix(self, prefix: str) -> int:
        """Count inserted words beginning with *prefix*.  O(L + matches)."""
        prefix = self._check_word(prefix)
        node = self._find_node(prefix)
        if node is None:
            return 0
        if node.is_word:
            return 1 + self._count_descendants(node)
        return self._count_descendants(node)

    @staticmethod
    def _count_descendants(node: TrieNode) -> int:
        total = 0
        stack = [node]
        while stack:
            current = stack.pop()
            for child in current.children.values():
                total += int(child.is_word)
                stack.append(child)
        return total

    def delete(self, word: str) -> bool:
        """Delete *word* and prune unused nodes.  Return True if removed.  O(L)."""
        word = self._check_word(word)

        def remove(node: TrieNode, depth: int) -> bool:
            if depth == len(word):
                if not node.is_word:
                    return False
                node.is_word = False
                return True
            character = word[depth]
            child = node.children.get(character)
            if child is None:
                return False
            removed = remove(child, depth + 1)
            if removed and not child.is_word and not child.children:
                del node.children[character]
            return removed

        if remove(self._root, 0):
            self._word_count -= 1
            return True
        return False

    def words_with_prefix(self, prefix: str) -> List[str]:
        """Return all words starting with *prefix*, sorted lexicographically."""
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string")
        node = self._root if prefix == "" else self._find_node(prefix)
        if node is None:
            return []
        collected: List[str] = []

        def walk(current: TrieNode, path: List[str]) -> None:
            if current.is_word:
                collected.append("".join(path))
            for character in sorted(current.children):
                path.append(character)
                walk(current.children[character], path)
                path.pop()

        walk(node, list(prefix))
        return collected

    def all_words(self) -> List[str]:
        """Return every inserted word in sorted order."""
        return self.words_with_prefix("")

    def longest_common_prefix(self) -> str:
        """Longest prefix shared by every inserted word ('' if none/empty trie)."""
        if self._word_count == 0:
            return ""
        node = self._root
        characters: List[str] = []
        while not node.is_word and len(node.children) == 1:
            character, node = next(iter(node.children.items()))
            characters.append(character)
        return "".join(characters)


def main() -> None:
    trie = Trie()
    for word in ("cat", "car", "card", "care", "dog", "do", "dot"):
        assert trie.insert(word) is True
    assert trie.insert("cat") is False
    assert len(trie) == 7

    assert trie.search("cat") and trie.search("card")
    assert not trie.search("ca") and not trie.search("cart")
    assert trie.starts_with("ca") and trie.starts_with("do")
    assert not trie.starts_with("z")

    assert trie.count_words_with_prefix("ca") == 4
    assert trie.count_words_with_prefix("car") == 3
    assert trie.count_words_with_prefix("do") == 3
    assert trie.count_words_with_prefix("z") == 0
    assert trie.words_with_prefix("car") == ["car", "card", "care"]
    assert trie.all_words() == ["car", "card", "care", "cat", "do", "dog", "dot"]

    assert trie.delete("car") is True
    assert trie.search("car") is False
    assert trie.search("card") is True       # longer word survives
    assert trie.count_words_with_prefix("car") == 2
    assert trie.delete("car") is False

    assert trie.delete("card") is True
    assert trie.delete("care") is True
    assert not trie.starts_with("car")       # branch pruned
    assert trie.delete("cat") is True
    assert trie.all_words() == ["do", "dog", "dot"]
    assert trie.longest_common_prefix() == "do"

    fresh = Trie()
    fresh.insert("apple")
    fresh.insert("apply")
    assert fresh.longest_common_prefix() == "appl"
    assert Trie().longest_common_prefix() == ""

    for action in (
        lambda: trie.insert(""),
        lambda: trie.search(""),
        lambda: trie.insert(123),  # type: ignore[arg-type]
        lambda: trie.starts_with(""),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid trie operation was accepted")

    print("Self-test: trie insert/search/prefix counts/deletion pruning passed.")
    print(f"remaining words: {trie.all_words()}")
    print(f"prefix 'do' count: {trie.count_words_with_prefix('do')}")


if __name__ == "__main__":
    main()
