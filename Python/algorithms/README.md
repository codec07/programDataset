# Algorithms & Data Structures (Python, standard library only)

Twenty-two standalone Python 3.10+ programs. Every file has a module docstring
with complexity notes, type hints, input validation, and a `main()` self-test
with assertions. Run any file directly:

```console
python sorting_algorithms.py
```

## Programs

| File | Description | Notable complexity |
| --- | --- | --- |
| `sorting_algorithms.py` | Insertion, selection, bubble, merge, quick, heap and counting sorts; seeded timing comparison. | Merge/heap O(n log n); quick O(n log n) average; insertion/selection/bubble O(n^2); counting O(n + k) |
| `binary_search.py` | Binary search, lower/upper bound, first/last occurrence, exponential search, rotated-array search, integer square root. | O(n) sortedness check + O(log n) search, O(1) space |
| `graph_algorithms.py` | BFS, DFS, Dijkstra, topological sort, directed/undirected cycle detection, connected components. | BFS/DFS/topo/cycles O(V + E); Dijkstra O((V + E) log V) |
| `dynamic_programming.py` | Fibonacci, coin change, 0/1 knapsack, LCS, edit distance, LIS and unique paths, each memoized and tabulated. | O(n), O(n·C), O(n·m) depending on problem |
| `linked_list.py` | Singly linked list with append/prepend/insert/delete, reversal, middle, n-th from end, merge and Floyd cycle detection. | Traversals O(n); append/prepend O(1); reverse O(n)/O(1) space |
| `stack_queue.py` | Stack, O(1)-minimum stack, two-stack queue, fixed-capacity circular queue, bracket matching, sliding-window maximum. | All container ops O(1) amortized; sliding maximum O(n) |
| `binary_search_tree.py` | BST insertion, search, deletion, traversals, height, k-th smallest, range sum, validation. | O(h) per operation; O(n) worst, O(log n) balanced |
| `heap_tools.py` | Min-heap and max-heap from scratch, heapify, heapsort, k-smallest and k-largest. | push/pop O(log n), build O(n), heapsort O(n log n), top-k O(n log k) |
| `trie.py` | Prefix tree with insert/search/prefix queries, counted prefixes, pruning deletion, word listing. | O(L) per word operation; O(total characters) space |
| `union_find.py` | Disjoint-set union with path compression and union by rank, Kruskal MST, undirected cycle detection. | O(α(n)) amortized; Kruskal O(E log E) |
| `lru_cache_impl.py` | LRU cache from a hash map plus doubly linked list, with hit/miss statistics. | get/put O(1), O(capacity) space |
| `matrix_ops.py` | Addition, subtraction, multiplication, transpose, determinant, inverse, powers, matrix-vector product. | Multiply O(m·n·p); determinant/inverse O(n^3) |
| `bigint_arithmetic.py` | Signed arbitrary-precision add/subtract/multiply/divide on digit strings without native big ints for the core ops. | Add O(n); multiply/divide O(n·m) |
| `number_theory.py` | GCD/EGCD, modular inverse and power, Miller-Rabin primality, sieve, factorization, totient, divisors, generalized CRT. | O(log n) modular ops; sieve O(n log log n); factor O(√n) |
| `combinatorics.py` | Factorial, binomial, permutations, Pascal rows, Catalan, derangements, stars-and-bars, lazy subset/permutation generators. | Counting O(n) or O(k); generators O(k) extra space |
| `statistics_kit.py` | Mean, median, mode(s), percentile, variance, stddev, covariance, correlation, linear regression, z-scores, from scratch. | O(n), except median/percentile O(n log n) |
| `expression_evaluator.py` | Tokenizer plus shunting-yard parser and RPN evaluator for `+ - * / % ^`, parentheses, unary signs and variables. | O(n) time and space |
| `sudoku_solver.py` | Constraint-checked backtracking solver with MRV heuristic, solution counting and puzzle rendering. | Exponential worst case; practical puzzles solved quickly |
| `n_queens.py` | Bitmask backtracking to count or construct non-attacking queen placements. | Exponential worst case; O(n) depth and mask space |
| `maze_solver.py` | Grid maze parser with BFS shortest path, DFS path, A* and path rendering. | O(V) BFS/DFS; A* O(V log V) |
| `string_algorithms.py` | KMP, Rabin-Karp, Z-algorithm, Manacher, palindrome/anagram checks, LCP, run-length encoding, word reversal. | Matching O(n + m); Manacher/Z O(n) |
| `interval_tools.py` | Merge, insert, intersect, total covered length, point coverage, maximum overlap (meeting rooms). | O(n log n); insertion O(n) for sorted input |

## Notes

- No third-party packages, no network access, no files written.
- Demos use fixed random seeds, so correctness output is deterministic; the
  sorting timing column naturally varies by machine.
- Inputs are validated and invalid operations raise `ValueError`, `TypeError`,
  `IndexError`, `OverflowError` or `ZeroDivisionError` with meaningful messages.
