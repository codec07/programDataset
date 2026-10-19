"""Descriptive statistics implemented from scratch (no wrapping of ``statistics``).

Provided:

* mean, median, mode / modes          - O(n) / O(n log n) / O(n) with a dict
* percentile / quantile               - O(n log n), linear interpolation
* variance, standard deviation        - O(n), population or sample
* covariance, Pearson correlation     - O(n)
* simple linear regression            - O(n), returns slope/intercept/r/r^2
* z-scores                            - O(n)

All functions validate their input: sequences must be non-empty, numeric
(non-bool), and paired inputs must have equal lengths.  Sample statistics
require at least two observations.  The demo compares results with the
standard-library ``statistics`` module on a fixed dataset in addition to exact
hand-computed cases.
"""

from __future__ import annotations

import math
import statistics as stdlib_statistics
from typing import List, NamedTuple, Sequence

Number = int | float


class Regression(NamedTuple):
    """Result of a simple linear regression ``y = slope*x + intercept``."""

    slope: float
    intercept: float
    correlation: float
    r_squared: float


def _clean(values: Sequence[Number], name: str = "values") -> List[float]:
    if not isinstance(values, (list, tuple)) and not hasattr(values, "__iter__"):
        raise TypeError(f"{name} must be an iterable of numbers")
    cleaned: List[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must contain only real numbers")
        cleaned.append(float(value))
    if not cleaned:
        raise ValueError(f"{name} must not be empty")
    return cleaned


def mean(values: Sequence[Number]) -> float:
    """Arithmetic mean.  O(n) time, O(n) space for the cleaned copy."""
    data = _clean(values)
    return sum(data) / len(data)


def median(values: Sequence[Number]) -> float:
    """Median; the mean of the two central values for even lengths.

    Time: O(n log n) due to sorting.
    """
    data = sorted(_clean(values))
    size = len(data)
    middle = size // 2
    if size % 2:
        return data[middle]
    return (data[middle - 1] + data[middle]) / 2.0


def modes(values: Sequence[Number]) -> List[float]:
    """All most frequent values, sorted ascending.  O(n)."""
    data = _clean(values)
    counts: dict[float, int] = {}
    for value in data:
        counts[value] = counts.get(value, 0) + 1
    highest = max(counts.values())
    return sorted(value for value, count in counts.items() if count == highest)


def mode(values: Sequence[Number]) -> float:
    """Single mode; ties are broken by the smallest value.  O(n)."""
    return modes(values)[0]


def percentile(values: Sequence[Number], level: float) -> float:
    """Percentile with linear interpolation between closest ranks.

    ``level`` is in [0, 100].  Uses index ``(n - 1) * level / 100``.
    Time: O(n log n).
    """
    if isinstance(level, bool) or not isinstance(level, (int, float)):
        raise TypeError("percentile level must be a number")
    if not 0.0 <= float(level) <= 100.0:
        raise ValueError("percentile level must be between 0 and 100")
    data = sorted(_clean(values))
    position = (len(data) - 1) * float(level) / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return data[lower]
    fraction = position - lower
    return data[lower] * (1.0 - fraction) + data[upper] * fraction


def quantile(values: Sequence[Number], fraction: float) -> float:
    """Quantile wrapper: ``fraction`` is in [0, 1]."""
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        raise TypeError("quantile fraction must be a number")
    return percentile(values, float(fraction) * 100.0)


def variance(values: Sequence[Number], sample: bool = True) -> float:
    """Variance.  ``sample=True`` divides by n-1, otherwise by n.  O(n)."""
    data = _clean(values)
    if sample and len(data) < 2:
        raise ValueError("sample variance requires at least two values")
    average = sum(data) / len(data)
    total = sum((value - average) ** 2 for value in data)
    return total / (len(data) - 1 if sample else len(data))


def standard_deviation(values: Sequence[Number], sample: bool = True) -> float:
    """Square root of the variance.  O(n)."""
    return math.sqrt(variance(values, sample))


def covariance(
    first: Sequence[Number], second: Sequence[Number], sample: bool = True
) -> float:
    """Covariance of paired data.  O(n)."""
    left, right = _clean(first, "first"), _clean(second, "second")
    if len(left) != len(right):
        raise ValueError("paired sequences must have the same length")
    if sample and len(left) < 2:
        raise ValueError("sample covariance requires at least two pairs")
    mean_left, mean_right = mean(left), mean(right)
    total = sum(
        (a - mean_left) * (b - mean_right) for a, b in zip(left, right)
    )
    return total / (len(left) - 1 if sample else len(left))


def correlation(first: Sequence[Number], second: Sequence[Number]) -> float:
    """Pearson correlation coefficient in [-1, 1].  O(n).

    Raises ValueError when either sequence is constant (zero variance).
    """
    left, right = _clean(first, "first"), _clean(second, "second")
    if len(left) != len(right):
        raise ValueError("paired sequences must have the same length")
    deviation_left = standard_deviation(left, sample=False)
    deviation_right = standard_deviation(right, sample=False)
    if deviation_left == 0.0 or deviation_right == 0.0:
        raise ValueError("correlation is undefined for constant data")
    return covariance(left, right, sample=False) / (deviation_left * deviation_right)


def linear_regression(
    predictor: Sequence[Number], response: Sequence[Number]
) -> Regression:
    """Least-squares fit ``response = slope * predictor + intercept``.  O(n).

    Raises ValueError for mismatched lengths or zero predictor variance.
    """
    x_values, y_values = _clean(predictor, "predictor"), _clean(response, "response")
    if len(x_values) != len(y_values):
        raise ValueError("predictor and response must have the same length")
    variance_x = variance(x_values, sample=False)
    if variance_x == 0.0:
        raise ValueError("predictor must not be constant")
    slope = covariance(x_values, y_values, sample=False) / variance_x
    intercept = mean(y_values) - slope * mean(x_values)
    r_value = correlation(x_values, y_values)
    return Regression(slope, intercept, r_value, r_value * r_value)


def z_scores(values: Sequence[Number], sample: bool = True) -> List[float]:
    """Standardize each value: ``(x - mean) / stddev``.  O(n)."""
    data = _clean(values)
    deviation = standard_deviation(data, sample)
    if deviation == 0.0:
        raise ValueError("z-scores are undefined for constant data")
    average = mean(data)
    return [(value - average) / deviation for value in data]


def main() -> None:
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    assert mean(data) == 5.0
    assert median([1, 2, 3, 4]) == 2.5
    assert median([3, 1, 2]) == 2.0
    assert mode([1, 2, 2, 3, 3]) == 2.0
    assert modes([1, 2, 2, 3, 3]) == [2.0, 3.0]
    assert modes([7.0]) == [7.0]

    assert percentile([1, 2, 3, 4], 0) == 1.0
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([1, 2, 3, 4], 25) == 1.75
    assert percentile([1, 2, 3, 4], 100) == 4.0
    assert quantile([1, 2, 3, 4], 0.5) == 2.5

    assert variance(data, sample=False) == 4.0
    assert math.isclose(variance(data, sample=True), 32.0 / 7.0)
    assert math.isclose(standard_deviation(data, sample=True), math.sqrt(32.0 / 7.0))
    assert standard_deviation(data, sample=False) == 2.0

    assert covariance([1, 2, 3], [2, 4, 6], sample=True) == 2.0
    assert math.isclose(correlation([1, 2, 3], [2, 4, 6]), 1.0)
    assert math.isclose(correlation([1, 2, 3], [6, 4, 2]), -1.0)

    fit = linear_regression([1, 2, 3, 4], [3, 5, 7, 9])
    assert math.isclose(fit.slope, 2.0)
    assert math.isclose(fit.intercept, 1.0)
    assert math.isclose(fit.correlation, 1.0) and math.isclose(fit.r_squared, 1.0)

    scores = z_scores([1, 2, 3], sample=False)
    assert math.isclose(sum(scores), 0.0) and scores[1] == 0.0

    assert math.isclose(mean(data), stdlib_statistics.fmean(data))
    assert math.isclose(median(data), stdlib_statistics.median(data))
    assert modes(data) == sorted(float(v) for v in stdlib_statistics.multimode(data))
    assert math.isclose(
        variance(data, sample=True), stdlib_statistics.variance(data)
    )
    for level in (0, 10, 25, 50, 75, 90, 100):
        assert math.isclose(
            percentile(data, level),
            stdlib_statistics.quantiles(data, n=100, method="inclusive")[level - 1]
            if 0 < level < 100
            else min(data) if level == 0 else max(data),
        ), level

    for action in (
        lambda: mean([]),
        lambda: mean([1, "two"]),  # type: ignore[list-item]
        lambda: percentile([1, 2], 101),
        lambda: variance([1], sample=True),
        lambda: covariance([1, 2], [1]),
        lambda: correlation([1, 1], [1, 2]),
        lambda: linear_regression([2, 2, 2], [1, 2, 3]),
        lambda: z_scores([5, 5, 5]),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid statistics input was accepted")

    print("Self-test: descriptive statistics match hand values and the stdlib module.")
    print(f"mean={mean(data)}, median={median(data)}, modes={modes(data)}")
    print(f"variance(sample)={variance(data):.4f}, stddev(pop)={standard_deviation(data, False)}")
    print(f"regression on [1..4]->[3,5,7,9]: slope={fit.slope}, intercept={fit.intercept}")


if __name__ == "__main__":
    main()
