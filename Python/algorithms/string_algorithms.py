"""Classic string algorithms: matching, palindromes, encoding and anagrams.

Complexity (n = text length, m = pattern length):

* ``kmp_search``            - O(n + m) time, O(m) space
* ``rabin_karp_search``     - O(n + m) average, O(n*m) worst, O(1) rolling space
* ``z_algorithm``           - O(n) time, O(n) space
* ``manacher``              - O(n) time, O(n) space (longest palindrome)
* ``longest_common_prefix`` - O(total characters) time
* ``run_length_encode/decode`` - O(n) time
* ``are_anagrams``          - O(n) time with counting dictionaries
* ``is_palindrome``         - O(n) time

KMP and Rabin-Karp are cross-checked against a naive scan on seeded random
data, and Manacher's output is verified to be a palindrome with the maximum
possible length.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_pattern(pattern: object) -> str:
    _require_string(pattern, "pattern")
    if not pattern:
        raise ValueError("pattern must be non-empty")
    return pattern


def naive_search(text: str, pattern: str) -> List[int]:
    """Reference implementation returning all (possibly overlapping) matches.

    Time: O(n*m).  Used by the demo to validate the fast algorithms.
    """
    _require_string(text, "text")
    _require_pattern(pattern)
    matches: List[int] = []
    for start in range(len(text) - len(pattern) + 1):
        if text[start:start + len(pattern)] == pattern:
            matches.append(start)
    return matches


def kmp_table(pattern: str) -> List[int]:
    """Prefix-function (failure) table for KMP: O(m) time."""
    _require_pattern(pattern)
    table = [0] * len(pattern)
    length = 0
    index = 1
    while index < len(pattern):
        if pattern[index] == pattern[length]:
            length += 1
            table[index] = length
            index += 1
        elif length:
            length = table[length - 1]
        else:
            table[index] = 0
            index += 1
    return table


def kmp_search(text: str, pattern: str) -> List[int]:
    """Return all starting indices of *pattern* in *text* (KMP).  O(n + m)."""
    _require_string(text, "text")
    _require_pattern(pattern)
    table = kmp_table(pattern)
    matches: List[int] = []
    index = matched = 0
    while index < len(text):
        if text[index] == pattern[matched]:
            index += 1
            matched += 1
            if matched == len(pattern):
                matches.append(index - matched)
                matched = table[matched - 1]
        elif matched:
            matched = table[matched - 1]
        else:
            index += 1
    return matches


def rabin_karp_search(text: str, pattern: str, base: int = 257, modulus: int = 1_000_000_007) -> List[int]:
    """Return all matches with a rolling hash, verifying each candidate.  O(n+m)."""
    _require_string(text, "text")
    _require_pattern(pattern)
    if base <= 1 or modulus <= 1:
        raise ValueError("base and modulus must be greater than 1")
    length = len(pattern)
    if length > len(text):
        return []
    highest = pow(base, length - 1, modulus)
    pattern_hash = 0
    window_hash = 0
    for character in pattern:
        pattern_hash = (pattern_hash * base + ord(character)) % modulus
    for character in text[:length]:
        window_hash = (window_hash * base + ord(character)) % modulus
    matches: List[int] = []
    for start in range(len(text) - length + 1):
        if window_hash == pattern_hash and text[start:start + length] == pattern:
            matches.append(start)
        if start + length < len(text):
            window_hash = (
                (window_hash - ord(text[start]) * highest) * base
                + ord(text[start + length])
            ) % modulus
    return matches


def z_algorithm(text: str) -> List[int]:
    """Return the Z-array where z[i] is the LCP length of text and text[i:].

    Time: O(n) time and O(n) space.
    """
    _require_string(text, "text")
    size = len(text)
    z = [0] * size
    if size == 0:
        return z
    z[0] = size
    left = right = 0
    for index in range(1, size):
        if index < right:
            z[index] = min(right - index, z[index - left])
        while index + z[index] < size and text[z[index]] == text[index + z[index]]:
            z[index] += 1
        if index + z[index] > right:
            left, right = index, index + z[index]
    return z


def manacher(text: str) -> str:
    """Return the longest palindromic substring (first one on ties).  O(n)."""
    _require_string(text, "text")
    if not text:
        return ""
    # Transform "abc" -> "^#a#b#c#$" so all palindromes have odd length.
    transformed = "^#" + "#".join(text) + "#$"
    radius = [0] * len(transformed)
    center = right = 0
    best_length = best_center = 0
    for index in range(1, len(transformed) - 1):
        if index < right:
            radius[index] = min(right - index, radius[2 * center - index])
        while transformed[index + radius[index] + 1] == transformed[index - radius[index] - 1]:
            radius[index] += 1
        if index + radius[index] > right:
            center, right = index, index + radius[index]
        if radius[index] > best_length:
            best_length, best_center = radius[index], index
    start = (best_center - best_length) // 2
    return text[start:start + best_length]


def is_palindrome(text: str, normalize: bool = True) -> bool:
    """Return True if *text* reads the same forwards and backwards.

    With ``normalize=True`` (default) case is ignored and non-alphanumeric
    characters are skipped.  Time: O(n), space: O(n).
    """
    _require_string(text, "text")
    if normalize:
        cleaned = [character.lower() for character in text if character.isalnum()]
    else:
        cleaned = list(text)
    return cleaned == cleaned[::-1]


def longest_common_prefix(strings: Sequence[str]) -> str:
    """Longest prefix shared by all strings ('' for no common prefix).  O(total)."""
    values = list(strings)
    if not values:
        raise ValueError("at least one string is required")
    for value in values:
        _require_string(value, "input string")
    prefix = values[0]
    for value in values[1:]:
        limit = min(len(prefix), len(value))
        index = 0
        while index < limit and prefix[index] == value[index]:
            index += 1
        prefix = prefix[:index]
        if not prefix:
            break
    return prefix


def run_length_encode(text: str) -> str:
    """Encode runs as character + count, e.g. ``aaabbc`` -> ``a3b2c1``.  O(n)."""
    _require_string(text, "text")
    if not text:
        return ""
    parts: List[str] = []
    count = 1
    for index in range(1, len(text)):
        if text[index] == text[index - 1]:
            count += 1
        else:
            parts.append(f"{text[index - 1]}{count}")
            count = 1
    parts.append(f"{text[-1]}{count}")
    return "".join(parts)


def run_length_decode(encoded: str) -> str:
    """Inverse of :func:`run_length_encode`.  O(n).

    Raises ValueError for malformed input (missing count, zero/negative count).
    """
    _require_string(encoded, "encoded")
    output: List[str] = []
    index = 0
    while index < len(encoded):
        character = encoded[index]
        if character.isdigit():
            raise ValueError("encoded text must alternate character and count")
        index += 1
        start = index
        while index < len(encoded) and encoded[index].isdigit():
            index += 1
        if start == index:
            raise ValueError("missing run length")
        count = int(encoded[start:index])
        if count <= 0:
            raise ValueError("run lengths must be positive")
        output.append(character * count)
    return "".join(output)


def are_anagrams(first: str, second: str) -> bool:
    """Return True when both strings contain the same characters.  O(n)."""
    _require_string(first, "first")
    _require_string(second, "second")
    if len(first) != len(second):
        return False
    counts: Dict[str, int] = {}
    for character in first:
        counts[character] = counts.get(character, 0) + 1
    for character in second:
        if counts.get(character, 0) == 0:
            return False
        counts[character] -= 1
    return True


def reverse_words(sentence: str) -> str:
    """Reverse the order of whitespace-separated words.  O(n)."""
    _require_string(sentence, "sentence")
    return " ".join(reversed(sentence.split()))


def main() -> None:
    assert kmp_table("ababaca") == [0, 0, 1, 2, 3, 0, 1]
    assert kmp_search("abxabcabcaby", "abcaby") == [6]
    assert kmp_search("aaaaa", "aa") == [0, 1, 2, 3]
    assert kmp_search("hello", "z") == []

    assert rabin_karp_search("abxabcabcaby", "abcaby") == [6]
    assert rabin_karp_search("aaaaa", "aa") == [0, 1, 2, 3]
    assert rabin_karp_search("abc", "abcd") == []

    expected_z = [12, 1, 0, 0, 3, 1, 0, 0, 2, 2, 1, 0]
    z = z_algorithm("aabcaabxaaaz")
    assert z == expected_z, z

    assert manacher("babad") in ("bab", "aba")
    assert manacher("forgeeksskeegfor") == "geeksskeeg"
    assert manacher("abaxyzzyxf") == "xyzzyx"
    assert manacher("cbbd") == "bb"
    assert manacher("") == ""
    assert manacher("abc") == "a"

    assert is_palindrome("A man, a plan, a canal: Panama") is True
    assert is_palindrome("racecar") is True
    assert is_palindrome("hello") is False
    assert is_palindrome("Step on no pets") is True

    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"
    assert longest_common_prefix(["dog", "racecar"]) == ""
    assert longest_common_prefix(["same"]) == "same"
    assert longest_common_prefix(["", "abc"]) == ""

    assert run_length_encode("aaabbc") == "a3b2c1"
    assert run_length_encode("") == ""
    assert run_length_decode("a3b2c1") == "aaabbc"
    for text in ("", "a", "aabbccddeeff", "xyz", "aaaabbbaaaa"):
        assert run_length_decode(run_length_encode(text)) == text, text

    assert are_anagrams("listen", "silent") is True
    assert are_anagrams("hello", "world") is False
    assert are_anagrams("", "") is True
    assert are_anagrams("a", "a ") is False
    assert reverse_words("the quick brown fox") == "fox brown quick the"

    rng = random.Random(2026)
    alphabet = "abc"
    for _ in range(120):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 40)))
        pattern = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 4)))
        reference = naive_search(text, pattern)
        assert kmp_search(text, pattern) == reference, (text, pattern)
        assert rabin_karp_search(text, pattern) == reference, (text, pattern)
        z_values = z_algorithm(text)
        for index in range(len(text)):
            suffix = text[index:]
            naive_z = 0
            while naive_z < len(suffix) and suffix[naive_z] == text[naive_z]:
                naive_z += 1
            assert z_values[index] == naive_z, (text, index)

    for action in (
        lambda: kmp_search("abc", ""),
        lambda: rabin_karp_search("abc", ""),
        lambda: rabin_karp_search("abc", "a", base=1),
        lambda: kmp_search(123, "a"),  # type: ignore[arg-type]
        lambda: longest_common_prefix([]),
        lambda: run_length_decode("abc"),
        lambda: run_length_decode("a0"),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid string-algorithm input was accepted")

    print("Self-test: KMP/Rabin-Karp/Z/Manacher and text utilities passed.")
    print(f"kmp matches of 'abcaby': {kmp_search('abxabcabcaby', 'abcaby')}")
    print(f"longest palindrome in 'forgeeksskeegfor': {manacher('forgeeksskeegfor')}")
    print(f"RLE round-trip: {run_length_encode('aaabbc')} <-> "
          f"{run_length_decode('a3b2c1')}")


if __name__ == "__main__":
    main()
