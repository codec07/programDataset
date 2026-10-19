"""Matrix operations with explicit dimension validation.

Representation: a matrix is a non-empty ``list[list[float]]`` with every row the
same non-zero length.  Integer entries are accepted and converted internally.

Complexity for an m x n matrix (square n x n where noted):

* add / subtract / scalar multiply - O(m*n)
* transpose                         - O(m*n)
* multiply (m x n by n x p)         - O(m*n*p)
* determinant (Gaussian elimination)- O(n^3)
* inverse (Gauss-Jordan)            - O(n^3)
* trace / identity                  - O(n)

Partial pivoting keeps elimination numerically stable.  The demo compares
results against hand-computed examples and checks dimension/singular errors.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

Number = int | float
Matrix = List[List[float]]
Vector = List[float]

_TOLERANCE = 1e-10


def _validate(matrix: Sequence[Sequence[Number]], name: str = "matrix") -> Tuple[int, int]:
    if not isinstance(matrix, (list, tuple)) or len(matrix) == 0:
        raise ValueError(f"{name} must be a non-empty list of rows")
    if not all(isinstance(row, (list, tuple)) for row in matrix):
        raise TypeError(f"{name} rows must be lists or tuples")
    columns = len(matrix[0])
    if columns == 0:
        raise ValueError(f"{name} rows must be non-empty")
    for row in matrix:
        if len(row) != columns:
            raise ValueError(f"{name} must be rectangular")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} entries must be real numbers")
    return len(matrix), columns


def _to_matrix(matrix: Sequence[Sequence[Number]]) -> Matrix:
    _validate(matrix)
    return [[float(value) for value in row] for row in matrix]


def shape(matrix: Sequence[Sequence[Number]]) -> Tuple[int, int]:
    return _validate(matrix)


def add(first: Sequence[Sequence[Number]], second: Sequence[Sequence[Number]]) -> Matrix:
    """Element-wise sum.  Raises ValueError when shapes differ."""
    rows, columns = _validate(first, "first")
    _validate(second, "second")
    if shape(second) != (rows, columns):
        raise ValueError("matrices must have the same shape for addition")
    return [
        [float(first[i][j]) + float(second[i][j]) for j in range(columns)]
        for i in range(rows)
    ]


def subtract(
    first: Sequence[Sequence[Number]], second: Sequence[Sequence[Number]]
) -> Matrix:
    """Element-wise difference.  Raises ValueError when shapes differ."""
    rows, columns = _validate(first, "first")
    if shape(second) != (rows, columns):
        raise ValueError("matrices must have the same shape for subtraction")
    return [
        [float(first[i][j]) - float(second[i][j]) for j in range(columns)]
        for i in range(rows)
    ]


def scalar_multiply(matrix: Sequence[Sequence[Number]], scalar: Number) -> Matrix:
    """Multiply every entry by *scalar*."""
    if isinstance(scalar, bool) or not isinstance(scalar, (int, float)):
        raise TypeError("scalar must be a number")
    data = _to_matrix(matrix)
    return [[value * float(scalar) for value in row] for row in data]


def transpose(matrix: Sequence[Sequence[Number]]) -> Matrix:
    """Return the transpose.  O(m*n)."""
    rows, columns = _validate(matrix)
    return [[float(matrix[i][j]) for i in range(rows)] for j in range(columns)]


def multiply(
    first: Sequence[Sequence[Number]], second: Sequence[Sequence[Number]]
) -> Matrix:
    """Matrix product.  Requires first.columns == second.rows.  O(m*n*p)."""
    left_rows, left_columns = _validate(first, "first")
    right_rows, right_columns = _validate(second, "second")
    if left_columns != right_rows:
        raise ValueError("inner dimensions do not match for multiplication")
    result: Matrix = []
    for i in range(left_rows):
        row: List[float] = []
        for j in range(right_columns):
            total = 0.0
            for k in range(left_columns):
                total += float(first[i][k]) * float(second[k][j])
            row.append(total)
        result.append(row)
    return result


def matvec(matrix: Sequence[Sequence[Number]], vector: Sequence[Number]) -> Vector:
    """Matrix-vector product.  O(m*n)."""
    rows, columns = _validate(matrix)
    if len(vector) != columns:
        raise ValueError("vector length must equal the number of columns")
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("vector entries must be real numbers")
    return [
        sum(float(matrix[i][j]) * float(vector[j]) for j in range(columns))
        for i in range(rows)
    ]


def identity(size: int) -> Matrix:
    """Return the size x size identity matrix."""
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an int")
    if size <= 0:
        raise ValueError("size must be positive")
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


def trace(matrix: Sequence[Sequence[Number]]) -> float:
    """Sum of the main diagonal; requires a square matrix."""
    rows, columns = _validate(matrix)
    if rows != columns:
        raise ValueError("trace requires a square matrix")
    return sum(float(matrix[i][i]) for i in range(rows))


def determinant(matrix: Sequence[Sequence[Number]]) -> float:
    """Determinant by Gaussian elimination with partial pivoting.  O(n^3)."""
    data = _to_matrix(matrix)
    size = len(data)
    if size != len(data[0]):
        raise ValueError("determinant requires a square matrix")
    result = 1.0
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(data[row][column]))
        if abs(data[pivot][column]) < _TOLERANCE:
            return 0.0
        if pivot != column:
            data[column], data[pivot] = data[pivot], data[column]
            result = -result
        pivot_value = data[column][column]
        result *= pivot_value
        for row in range(column + 1, size):
            factor = data[row][column] / pivot_value
            if factor == 0.0:
                continue
            for index in range(column, size):
                data[row][index] -= factor * data[column][index]
    return result


def inverse(matrix: Sequence[Sequence[Number]]) -> Matrix:
    """Invert a square matrix with Gauss-Jordan elimination.  O(n^3).

    Raises ValueError for singular (non-invertible) matrices.
    """
    data = _to_matrix(matrix)
    size = len(data)
    if size != len(data[0]):
        raise ValueError("inverse requires a square matrix")
    augmented = [
        data[row] + [1.0 if row == column else 0.0 for column in range(size)]
        for row in range(size)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < _TOLERANCE:
            raise ValueError("matrix is singular and has no inverse")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(2 * size)
            ]
    return [row[size:] for row in augmented]


def matrix_power(matrix: Sequence[Sequence[Number]], exponent: int) -> Matrix:
    """Raise a square matrix to a non-negative integer power.  O(n^3 log k)."""
    base = _to_matrix(matrix)
    size = len(base)
    if size != len(base[0]):
        raise ValueError("matrix_power requires a square matrix")
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("exponent must be an int")
    if exponent < 0:
        raise ValueError("exponent must be non-negative")
    result = identity(size)
    while exponent:
        if exponent & 1:
            result = multiply(result, base)
        exponent >>= 1
        if exponent:
            base = multiply(base, base)
    return result


def matrices_close(
    first: Sequence[Sequence[Number]],
    second: Sequence[Sequence[Number]],
    tolerance: float = 1e-9,
) -> bool:
    """Compare matrices entry-wise within *tolerance*."""
    if shape(first) != shape(second):
        return False
    return all(
        abs(float(first[i][j]) - float(second[i][j])) <= tolerance
        for i in range(len(first))
        for j in range(len(first[0]))
    )


def main() -> None:
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    assert add(a, b) == [[6.0, 8.0], [10.0, 12.0]]
    assert subtract(b, a) == [[4.0, 4.0], [4.0, 4.0]]
    assert scalar_multiply(a, 2) == [[2.0, 4.0], [6.0, 8.0]]
    assert transpose(a) == [[1.0, 3.0], [2.0, 4.0]]
    assert multiply(a, b) == [[19.0, 22.0], [43.0, 50.0]]
    assert matvec(a, [1, 1]) == [3.0, 7.0]
    assert trace(a) == 5.0
    assert determinant(a) == -2.0
    assert determinant([[6, 1, 1], [4, -2, 5], [2, 8, 7]]) == -306.0
    assert determinant([[1, 2], [2, 4]]) == 0.0

    inv = inverse(a)
    assert matrices_close(inv, [[-2.0, 1.0], [1.5, -0.5]])
    assert matrices_close(multiply(a, inv), identity(2))
    assert matrices_close(multiply(inv, a), identity(2))

    assert matrix_power(a, 0) == identity(2)
    assert matrix_power(a, 3) == multiply(multiply(a, a), a)
    assert matrix_power(identity(3), 100) == identity(3)

    for action in (
        lambda: add([[1]], [[1, 2]]),
        lambda: multiply([[1, 2]], [[1, 2]]),
        lambda: determinant([[1, 2]]),
        lambda: inverse([[1, 2], [2, 4]]),
        lambda: trace([[1, 2]]),
        lambda: matvec([[1, 2]], [1]),
        lambda: scalar_multiply([[1]], True),  # type: ignore[arg-type]
        lambda: matrix_power([[1]], -1),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid matrix operation was accepted")

    print("Self-test: matrix arithmetic, determinant, inverse and powers passed.")
    print(f"det(A)={determinant(a)}, inverse(A)={inverse(a)}")
    print(f"A^3={matrix_power(a, 3)}")


if __name__ == "__main__":
    main()
