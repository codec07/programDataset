"""Seven classic dynamic-programming problems in memoized and tabulated form.

Each problem exposes two functions with identical results:

=====================  ==========================================  =============
problem                recurrence / state                            complexity
=====================  ==========================================  =============
Fibonacci              F(n) = F(n-1) + F(n-2)                        O(n) time
0/1 knapsack           best(i, cap) = max(skip, take)                O(n*cap)
coin change (min)      dp[a] = min(dp[a - coin]) + 1                 O(amount*k)
longest common subseq. LCS(i, j) from prefix matches                 O(n*m)
edit distance          insert / delete / replace                     O(n*m)
longest incr. subseq.  best ending at i (quadratic DP)               O(n^2)
unique grid paths      paths(r, c) = paths(r-1, c) + paths(r, c-1)    O(r*c)
=====================  ==========================================  =============

Memoized versions use explicit dictionaries (no decorators) and recurse;
tabulated versions are iterative.  Space is O(n), O(n*cap), O(amount),
O(n*m), O(n*m), O(n), O(cols) respectively for the tabulated forms.
The demo checks both versions against each other and against known answers.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple


def _check_non_negative_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


# ---------------------------------------------------------------------------
# Fibonacci
# ---------------------------------------------------------------------------
def fib_memo(n: int) -> int:
    """Return the n-th Fibonacci number using top-down memoization. O(n) time."""
    _check_non_negative_int(n, "n")
    memo: Dict[int, int] = {0: 0, 1: 1}

    def solve(k: int) -> int:
        if k not in memo:
            memo[k] = solve(k - 1) + solve(k - 2)
        return memo[k]

    return solve(n)


def fib_tab(n: int) -> int:
    """Return the n-th Fibonacci number with O(1) space. O(n) time."""
    _check_non_negative_int(n, "n")
    if n < 2:
        return n
    previous, current = 0, 1
    for _ in range(2, n + 1):
        previous, current = current, previous + current
    return current


def _fib_naive(n: int) -> int:
    """Exponential reference implementation used only for small n."""
    return n if n < 2 else _fib_naive(n - 1) + _fib_naive(n - 2)


# ---------------------------------------------------------------------------
# Coin change: minimum number of coins
# ---------------------------------------------------------------------------
def _validate_coins(coins: Sequence[int]) -> List[int]:
    if not coins:
        raise ValueError("at least one coin denomination is required")
    cleaned = list(coins)
    for coin in cleaned:
        if isinstance(coin, bool) or not isinstance(coin, int):
            raise TypeError("coin denominations must be integers")
        if coin <= 0:
            raise ValueError("coin denominations must be positive")
    return cleaned


def coin_change_memo(coins: Sequence[int], amount: int) -> int:
    """Minimum coin count for *amount*, or -1.  O(amount * len(coins)) time."""
    denominations = _validate_coins(coins)
    _check_non_negative_int(amount, "amount")
    memo: Dict[int, int] = {0: 0}

    def solve(remaining: int) -> int:
        if remaining < 0:
            return math.inf
        if remaining not in memo:
            memo[remaining] = 1 + min(solve(remaining - coin) for coin in denominations)
        return memo[remaining]

    best = solve(amount)
    return -1 if best == math.inf else best


def coin_change_tab(coins: Sequence[int], amount: int) -> int:
    """Minimum coin count for *amount*, or -1.  O(amount * len(coins)) time."""
    denominations = _validate_coins(coins)
    _check_non_negative_int(amount, "amount")
    dp = [0] + [math.inf] * amount
    for current in range(1, amount + 1):
        for coin in denominations:
            if coin <= current and dp[current - coin] + 1 < dp[current]:
                dp[current] = dp[current - coin] + 1
    return -1 if dp[amount] == math.inf else int(dp[amount])


# ---------------------------------------------------------------------------
# 0/1 knapsack
# ---------------------------------------------------------------------------
def _validate_knapsack(
    weights: Sequence[int], values: Sequence[int], capacity: int
) -> Tuple[List[int], List[int]]:
    if len(weights) != len(values):
        raise ValueError("weights and values must have the same length")
    _check_non_negative_int(capacity, "capacity")
    clean_weights, clean_values = list(weights), list(values)
    for weight in clean_weights:
        if isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0:
            raise ValueError("weights must be positive integers")
    for value in clean_values:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("values must be non-negative integers")
    return clean_weights, clean_values


def knapsack_memo(weights: Sequence[int], values: Sequence[int], capacity: int) -> int:
    """Maximum value with total weight at most *capacity*.  O(n*capacity) time."""
    weights, values = _validate_knapsack(weights, values, capacity)
    memo: Dict[Tuple[int, int], int] = {}

    def solve(index: int, remaining: int) -> int:
        if index == len(weights):
            return 0
        key = (index, remaining)
        if key not in memo:
            skip = solve(index + 1, remaining)
            take = 0
            if weights[index] <= remaining:
                take = values[index] + solve(index + 1, remaining - weights[index])
            memo[key] = max(skip, take)
        return memo[key]

    return solve(0, capacity)


def knapsack_tab(weights: Sequence[int], values: Sequence[int], capacity: int) -> int:
    """Maximum value with total weight at most *capacity*.  O(n*capacity) time."""
    weights, values = _validate_knapsack(weights, values, capacity)
    dp = [0] * (capacity + 1)
    for weight, value in zip(weights, values):
        for current in range(capacity, weight - 1, -1):
            dp[current] = max(dp[current], dp[current - weight] + value)
    return dp[capacity]


# ---------------------------------------------------------------------------
# Longest common subsequence
# ---------------------------------------------------------------------------
def lcs_memo(first: str, second: str) -> int:
    """Length of the longest common subsequence.  O(len(first)*len(second))."""
    memo: Dict[Tuple[int, int], int] = {}

    def solve(i: int, j: int) -> int:
        if i == len(first) or j == len(second):
            return 0
        key = (i, j)
        if key not in memo:
            if first[i] == second[j]:
                memo[key] = 1 + solve(i + 1, j + 1)
            else:
                memo[key] = max(solve(i + 1, j), solve(i, j + 1))
        return memo[key]

    return solve(0, 0)


def lcs_tab(first: str, second: str) -> int:
    """Length of the longest common subsequence.  O(len(first)*len(second))."""
    if not isinstance(first, str) or not isinstance(second, str):
        raise TypeError("lcs inputs must be strings")
    previous = [0] * (len(second) + 1)
    for left in first:
        current = [0] * (len(second) + 1)
        for j, right in enumerate(second, start=1):
            if left == right:
                current[j] = previous[j - 1] + 1
            else:
                current[j] = max(previous[j], current[j - 1])
        previous = current
    return previous[-1]


# ---------------------------------------------------------------------------
# Edit distance (Levenshtein, unit costs)
# ---------------------------------------------------------------------------
def edit_distance_memo(first: str, second: str) -> int:
    """Minimum insert/delete/replace operations.  O(len(first)*len(second))."""
    memo: Dict[Tuple[int, int], int] = {}

    def solve(i: int, j: int) -> int:
        if i == 0:
            return j
        if j == 0:
            return i
        key = (i, j)
        if key not in memo:
            if first[i - 1] == second[j - 1]:
                memo[key] = solve(i - 1, j - 1)
            else:
                memo[key] = 1 + min(solve(i - 1, j), solve(i, j - 1), solve(i - 1, j - 1))
        return memo[key]

    return solve(len(first), len(second))


def edit_distance_tab(first: str, second: str) -> int:
    """Minimum insert/delete/replace operations.  O(len(first)*len(second))."""
    if not isinstance(first, str) or not isinstance(second, str):
        raise TypeError("edit distance inputs must be strings")
    previous = list(range(len(second) + 1))
    for i, left in enumerate(first, start=1):
        current = [i] + [0] * len(second)
        for j, right in enumerate(second, start=1):
            if left == right:
                current[j] = previous[j - 1]
            else:
                current[j] = 1 + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return previous[-1]


# ---------------------------------------------------------------------------
# Longest increasing subsequence (quadratic DP)
# ---------------------------------------------------------------------------
def lis_memo(sequence: Sequence[int]) -> int:
    """Length of the longest strictly increasing subsequence.  O(n^2) time."""
    if not sequence:
        return 0
    memo: Dict[int, int] = {}

    def solve(index: int) -> int:
        if index not in memo:
            best = 1
            for previous in range(index):
                if sequence[previous] < sequence[index]:
                    best = max(best, solve(previous) + 1)
            memo[index] = best
        return memo[index]

    return max(solve(index) for index in range(len(sequence)))


def lis_tab(sequence: Sequence[int]) -> int:
    """Length of the longest strictly increasing subsequence.  O(n^2) time."""
    if not sequence:
        return 0
    dp = [1] * len(sequence)
    for index in range(len(sequence)):
        for previous in range(index):
            if sequence[previous] < sequence[index]:
                dp[index] = max(dp[index], dp[previous] + 1)
    return max(dp)


# ---------------------------------------------------------------------------
# Unique paths in a grid
# ---------------------------------------------------------------------------
def unique_paths_memo(rows: int, columns: int) -> int:
    """Number of right/down paths from top-left to bottom-right.  O(rows*cols)."""
    _check_non_negative_int(rows, "rows")
    _check_non_negative_int(columns, "columns")
    if rows == 0 or columns == 0:
        raise ValueError("rows and columns must be positive")
    memo: Dict[Tuple[int, int], int] = {}

    def solve(row: int, column: int) -> int:
        if row == 0 or column == 0:
            return 1
        key = (row, column)
        if key not in memo:
            memo[key] = solve(row - 1, column) + solve(row, column - 1)
        return memo[key]

    return solve(rows - 1, columns - 1)


def unique_paths_tab(rows: int, columns: int) -> int:
    """Number of right/down paths from top-left to bottom-right.  O(rows*cols)."""
    _check_non_negative_int(rows, "rows")
    _check_non_negative_int(columns, "columns")
    if rows == 0 or columns == 0:
        raise ValueError("rows and columns must be positive")
    dp = [1] * columns
    for _ in range(1, rows):
        for column in range(1, columns):
            dp[column] += dp[column - 1]
    return dp[-1]


def main() -> None:
    # Fibonacci, including a naive reference for small n.
    for n in range(16):
        assert fib_memo(n) == fib_tab(n) == _fib_naive(n), n
    assert fib_memo(50) == fib_tab(50) == 12_586_269_025

    # Coin change.
    for amount in range(30):
        assert coin_change_memo([1, 2, 5], amount) == coin_change_tab([1, 2, 5], amount)
    assert coin_change_tab([1, 2, 5], 11) == 3
    assert coin_change_tab([2], 3) == -1
    assert coin_change_tab([7], 0) == 0

    # Knapsack.
    weights, values = [1, 3, 4, 5], [1, 4, 5, 7]
    assert knapsack_memo(weights, values, 7) == 9
    assert knapsack_tab(weights, values, 7) == 9
    for capacity in range(12):
        assert knapsack_memo(weights, values, capacity) == knapsack_tab(
            weights, values, capacity
        )

    # LCS and edit distance.
    assert lcs_memo("ABCBDAB", "BDCABA") == lcs_tab("ABCBDAB", "BDCABA") == 4
    assert lcs_tab("", "abc") == 0
    assert edit_distance_memo("kitten", "sitting") == edit_distance_tab(
        "kitten", "sitting"
    ) == 3
    assert edit_distance_tab("", "abc") == 3
    assert edit_distance_tab("same", "same") == 0

    # LIS.
    data = [10, 9, 2, 5, 3, 7, 101, 18]
    assert lis_memo(data) == lis_tab(data) == 4
    assert lis_tab([]) == 0
    assert lis_tab([3, 3, 3]) == 1

    # Unique paths.
    for rows in range(1, 8):
        for columns in range(1, 8):
            assert unique_paths_memo(rows, columns) == unique_paths_tab(rows, columns)
    assert unique_paths_tab(3, 7) == 28
    assert unique_paths_tab(1, 1) == 1

    # Validation checks.
    for action in (lambda: coin_change_tab([], 5), lambda: knapsack_tab([1], [1, 2], 3),
                   lambda: unique_paths_tab(0, 4)):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid DP input was accepted")

    print("Self-test: memoized and tabulated DP versions agree on all cases.")
    print(f"fib(50)={fib_tab(50)}, coins(11)={coin_change_tab([1, 2, 5], 11)}, "
          f"knapsack(7)={knapsack_tab(weights, values, 7)}, "
          f"lcs={lcs_tab('ABCBDAB', 'BDCABA')}, "
          f"edit(kitten,sitting)={edit_distance_tab('kitten', 'sitting')}, "
          f"lis={lis_tab(data)}, paths(3x7)={unique_paths_tab(3, 7)}")


if __name__ == "__main__":
    main()
