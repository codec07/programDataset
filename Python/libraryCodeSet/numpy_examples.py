"""NumPy — practical single-file examples.

Install:  pip install numpy
Run:      python numpy_examples.py

Covers array creation, dtypes, reshaping, indexing, broadcasting, ufuncs,
reductions, linear algebra, random numbers, FFTs, structured arrays, and
saving/loading .npy/.npz files.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Creating arrays
# ---------------------------------------------------------------------------
def creating_arrays() -> None:
    section("1. Array creation")

    print("from list:        ", np.array([1, 2, 3]))
    print("2-D from nested:  \n", np.array([[1, 2], [3, 4]]))
    print("arange(0, 10, 2): ", np.arange(0, 10, 2))
    print("linspace(0, 1, 5):", np.linspace(0.0, 1.0, 5))
    print("zeros(2, 3):      \n", np.zeros((2, 3)))
    print("ones_like:        ", np.ones_like(np.array([[2, 5], [7, 1]])))
    print("full((2, 2), 7):  \n", np.full((2, 2), 7))
    print("identity(3):      \n", np.eye(3))
    print("empty (uninit):   ", np.empty((2, 2)).shape)

    # Ranges with step, inclusive stop via endpoint=True (default)
    print("logspace:         ", np.logspace(0, 3, 4))  # 1, 10, 100, 1000

    # Random arrays from a seeded generator (reproducible)
    rng = np.random.default_rng(seed=42)
    print("uniform [0, 1):   ", rng.random(5))
    print("normal(0, 1):     ", rng.normal(loc=0.0, scale=1.0, size=5))
    print("integers(1, 7, 5):", rng.integers(1, 7, size=5))


# ---------------------------------------------------------------------------
# 2. dtypes and memory
# ---------------------------------------------------------------------------
def dtypes() -> None:
    section("2. dtypes, casting, and memory")

    a = np.array([1, 2, 3], dtype=np.int32)
    b = np.array([1.5, 2.5], dtype=np.float64)
    c = np.array([True, False, True], dtype=np.bool_)

    print("int32:", a.dtype, "itemsize:", a.itemsize)
    print("float64:", b.dtype, "itemsize:", b.itemsize)
    print("bool:", c.dtype, "itemsize:", c.itemsize)

    # Safe vs unsafe casting
    print("astype float:", a.astype(np.float64))
    print("float -> int (truncates):", np.array([1.9, -1.9]).astype(np.int64))

    # Unsigned overflow wraps; use a wider dtype to avoid surprises
    small = np.array([250], dtype=np.uint8)
    print("uint8 250 + 10 =", (small + 10)[0], "(wraps around)")

    # Structured dtype: like a lightweight table row
    person = np.dtype([("name", "U10"), ("age", "i4"), ("score", "f4")])
    people = np.array([("Ada", 36, 91.5), ("Linus", 54, 88.0)], dtype=person)
    print("structured:", people)
    print("ages:", people["age"])


# ---------------------------------------------------------------------------
# 3. Shape manipulation
# ---------------------------------------------------------------------------
def shapes() -> None:
    section("3. Reshaping and stacking")

    a = np.arange(12)
    print("original:", a)
    print("reshape(3, 4):\n", a.reshape(3, 4))
    print("reshape(2, -1):\n", a.reshape(2, -1))  # -1 infers dimension
    print("flatten:", a.reshape(3, 4).flatten())
    print("ravel (view when possible):", a.reshape(3, 4).ravel())
    print("transpose:\n", a.reshape(3, 4).T)

    # Adding/removing axes
    row = np.array([1, 2, 3])
    print("row shape:", row.shape)
    print("column shape:", row[:, np.newaxis].shape)
    print("expand_dims:", np.expand_dims(row, axis=0).shape)
    print("squeeze:", np.squeeze(np.zeros((1, 3, 1))).shape)

    x = np.array([[1, 2], [3, 4]])
    y = np.array([[5, 6], [7, 8]])
    print("vstack:\n", np.vstack([x, y]))
    print("hstack:\n", np.hstack([x, y]))
    print("stack axis=0 shape:", np.stack([x, y], axis=0).shape)
    print("concatenate axis=1:\n", np.concatenate([x, y], axis=1))


# ---------------------------------------------------------------------------
# 4. Indexing and slicing
# ---------------------------------------------------------------------------
def indexing() -> None:
    section("4. Indexing, slicing, boolean and fancy indexing")

    a = np.arange(1, 13).reshape(3, 4)
    print("array:\n", a)
    print("a[0, 0]:", a[0, 0])
    print("a[1]:", a[1])                 # row
    print("a[:, 1]:", a[:, 1])           # column
    print("a[0:2, 1:3]:\n", a[0:2, 1:3])
    print("a[::2]:\n", a[::2])           # every other row
    print("a[::-1]:\n", a[::-1])         # reversed rows

    # Boolean masks
    print("values > 6:", a[a > 6])
    print("even values:", a[a % 2 == 0])
    print("mask shape:", (a > 6).shape)

    # np.where: choose elementwise
    print("where(a > 6, a, 0):\n", np.where(a > 6, a, 0))

    # Fancy indexing with index arrays
    rows = np.array([0, 2])
    cols = np.array([1, 3])
    print("a[rows, cols]:", a[rows, cols])
    print("take columns [3, 0]:\n", a[:, [3, 0]])

    # Set values through a mask
    b = a.copy()
    b[b < 5] = 0
    print("clipped mask assignment:\n", b)

    # np.clip is often clearer for range limiting
    print("clip(3, 9):\n", np.clip(a, 3, 9))


# ---------------------------------------------------------------------------
# 5. Broadcasting and vectorization
# ---------------------------------------------------------------------------
def broadcasting() -> None:
    section("5. Broadcasting and vectorization")

    a = np.array([[1, 2, 3], [4, 5, 6]])
    row = np.array([10, 20, 30])
    col = np.array([[100], [200]])

    print("a + row:\n", a + row)          # row broadcasts across rows
    print("a + col:\n", a + col)          # column broadcasts across columns
    print("a * 2 + 1:\n", a * 2 + 1)

    # Outer product via broadcasting
    x = np.array([1, 2, 3])
    y = np.array([10, 20])
    print("outer via x[:, None] * y:\n", x[:, None] * y)

    # Normalize each column: (x - mean) / std, shape (2, 3)
    data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    means = data.mean(axis=0)             # shape (3,)
    stds = data.std(axis=0)
    print("column-standardized:\n", (data - means) / stds)

    # Avoid Python loops for speed and clarity
    values = np.arange(1_000_000)
    print("vectorized sum:", values.sum())
    print("vectorized squares mean:", (values ** 2).mean())


# ---------------------------------------------------------------------------
# 6. Universal functions and reductions
# ---------------------------------------------------------------------------
def math_and_reductions() -> None:
    section("6. ufuncs and reductions")

    a = np.array([1.0, 2.0, 3.0, 4.0])
    print("sqrt:", np.sqrt(a))
    print("exp:", np.exp(a))
    print("log1p:", np.log1p(a))
    print("sin(pi/2):", np.sin(np.pi / 2))

    # Elementwise binary ufuncs
    b = np.array([10.0, 20.0, 30.0, 40.0])
    print("add:", np.add(a, b))
    print("maximum:", np.maximum(a, 2.5))
    print("power:", np.power(a, 2))

    matrix = np.arange(1, 13).reshape(3, 4)
    print("sum all:", matrix.sum())
    print("sum axis=0 (columns):", matrix.sum(axis=0))
    print("sum axis=1 (rows):", matrix.sum(axis=1))
    print("mean:", matrix.mean(), "std:", matrix.std())
    print("min/max:", matrix.min(), matrix.max())
    print("argmin/argmax:", matrix.argmin(), matrix.argmax())
    print("cumsum:", matrix.cumsum(axis=1))
    print("percentiles:", np.percentile(matrix, [25, 50, 75]))

    # NaN-aware reductions
    with_nan = np.array([1.0, np.nan, 3.0])
    print("nanmean:", np.nanmean(with_nan), "nansum:", np.nansum(with_nan))


# ---------------------------------------------------------------------------
# 7. Linear algebra
# ---------------------------------------------------------------------------
def linear_algebra() -> None:
    section("7. Linear algebra")

    a = np.array([[3.0, 1.0], [1.0, 2.0]])
    b = np.array([9.0, 8.0])

    print("determinant:", np.linalg.det(a))
    print("inverse:\n", np.linalg.inv(a))
    print("solve a x = b:", np.linalg.solve(a, b))
    print("matrix power a^3:\n", np.linalg.matrix_power(a, 3))

    # Eigen decomposition (symmetric matrix gives real eigenvalues)
    eigenvalues, eigenvectors = np.linalg.eigh(a)
    print("eigenvalues:", eigenvalues)
    print("eigenvectors:\n", eigenvectors)

    # Singular value decomposition
    u, s, vt = np.linalg.svd(a)
    print("singular values:", s)

    # Norms and rank
    print("Frobenius norm:", np.linalg.norm(a))
    print("2-norm of b:", np.linalg.norm(b))
    print("rank:", np.linalg.matrix_rank(a))

    # Least squares: fit y = m*x + c
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([2.1, 4.0, 6.2, 7.9, 10.1])
    design = np.column_stack([x, np.ones_like(x)])
    coefficients, residuals, rank, sv = np.linalg.lstsq(design, y, rcond=None)
    print("least squares m, c:", coefficients)


# ---------------------------------------------------------------------------
# 8. Random numbers and statistics
# ---------------------------------------------------------------------------
def randomness() -> None:
    section("8. Random numbers and simple statistics")

    rng = np.random.default_rng(2026)

    sample = rng.normal(loc=100.0, scale=15.0, size=10_000)
    print("sample mean/std:", round(float(sample.mean()), 2), round(float(sample.std()), 2))

    # Sampling without replacement
    population = np.arange(1, 51)
    print("choice without replacement:", rng.choice(population, size=5, replace=False))

    # Shuffle in place
    cards = np.arange(1, 11)
    rng.shuffle(cards)
    print("shuffled:", cards)

    # Correlated data: y = 2x + noise
    x = rng.normal(size=1_000)
    y = 2.0 * x + rng.normal(scale=0.3, size=1_000)
    correlation = np.corrcoef(x, y)[0, 1]
    print("correlation:", round(float(correlation), 4))

    # Histogram counts and bin edges
    counts, edges = np.histogram(sample, bins=10)
    print("histogram counts:", counts)
    print("bin edges (first 3):", edges[:3])

    # Weighted mean
    values = np.array([1.0, 2.0, 3.0])
    weights = np.array([0.1, 0.3, 0.6])
    print("weighted mean:", np.average(values, weights=weights))


# ---------------------------------------------------------------------------
# 9. FFT and signal basics
# ---------------------------------------------------------------------------
def fft_examples() -> None:
    section("9. FFT and signal basics")

    sample_rate = 1000.0
    duration = 1.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    signal = 1.0 * np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 120 * t)

    spectrum = np.fft.rfft(signal)
    frequencies = np.fft.rfftfreq(signal.size, d=1.0 / sample_rate)
    magnitudes = np.abs(spectrum) / signal.size

    # Ignore the DC peak at index 0 when looking for tones
    peaks = np.argsort(magnitudes[1:])[-3:] + 1
    print("top frequencies:", np.round(frequencies[peaks], 2))
    print("top magnitudes:", np.round(magnitudes[peaks], 4))

    # Simple moving average (convolution with a box filter)
    noisy = signal + np.random.default_rng(7).normal(scale=0.2, size=signal.size)
    kernel = np.ones(25) / 25
    smoothed = np.convolve(noisy, kernel, mode="same")
    print("noisy std:", round(float(noisy.std()), 4))
    print("smoothed std:", round(float(smoothed.std()), 4))


# ---------------------------------------------------------------------------
# 10. Saving and loading
# ---------------------------------------------------------------------------
def persistence() -> None:
    section("10. Saving and loading arrays")

    workdir = Path(tempfile.mkdtemp(prefix="numpy_examples_"))
    array = np.arange(12).reshape(3, 4).astype(np.float64)

    np.save(workdir / "matrix.npy", array)
    loaded = np.load(workdir / "matrix.npy")
    print("npy round-trip equal:", np.array_equal(array, loaded))

    np.savez_compressed(
        workdir / "bundle.npz",
        matrix=array,
        labels=np.array(["a", "b", "c"]),
        metadata=np.array([1.0, 2.0]),
    )
    with np.load(workdir / "bundle.npz") as bundle:
        print("npz keys:", list(bundle.keys()))
        print("matrix recovered equal:", np.array_equal(bundle["matrix"], array))
        print("labels:", bundle["labels"])

    # Plain-text exchange (human readable, larger, no dtype metadata)
    np.savetxt(workdir / "matrix.csv", array, delimiter=",", fmt="%.2f")
    from_text = np.loadtxt(workdir / "matrix.csv", delimiter=",")
    print("savetxt/loadtxt equal:", np.allclose(array, from_text))

    print("files written to:", workdir)


def main() -> None:
    np.set_printoptions(precision=3, suppress=True, linewidth=100)
    creating_arrays()
    dtypes()
    shapes()
    indexing()
    broadcasting()
    math_and_reductions()
    linear_algebra()
    randomness()
    fft_examples()
    persistence()

    print("\nAll NumPy example sections completed.")


if __name__ == "__main__":
    main()
