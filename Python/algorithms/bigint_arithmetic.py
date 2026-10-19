"""Arbitrary-precision integer arithmetic on decimal digit strings.

The core operations never convert multi-digit inputs to Python integers; they
work digit by digit on strings, exactly like hand-written arithmetic:

* addition / subtraction - O(n)
* multiplication         - O(n*m) grade-school algorithm
* division / remainder   - O(n*m) long division (at most nine subtractions per
  output digit, each subtraction O(m))

Signed results use a leading ``-`` and no ``+``; redundant leading zeros are
removed.  Division truncates toward zero, and the remainder has the dividend's
sign (so ``a == q*b + r`` always holds).

The demo checks known cases and compares every operation with Python integers
as an oracle on seeded random inputs.
"""

from __future__ import annotations

import math
import random
from typing import Tuple


def _normalize(value: str) -> Tuple[int, str]:
    """Return (sign, digits) with sign 1/-1 and no leading zeros."""
    if not isinstance(value, str):
        raise TypeError("big integers must be decimal strings")
    text = value.strip()
    if not text:
        raise ValueError("empty string is not a big integer")
    sign = 1
    if text[0] in "+-":
        sign = -1 if text[0] == "-" else 1
        text = text[1:]
    if not text or any(character < "0" or character > "9" for character in text):
        raise ValueError(f"invalid big integer literal: {value!r}")
    digits = text.lstrip("0") or "0"
    if digits == "0":
        sign = 1
    return sign, digits


def _format(sign: int, digits: str) -> str:
    return digits if sign > 0 or digits == "0" else "-" + digits


def _compare_abs(first: str, second: str) -> int:
    if len(first) != len(second):
        return -1 if len(first) < len(second) else 1
    if first == second:
        return 0
    return -1 if first < second else 1


def _add_abs(first: str, second: str) -> str:
    i, j = len(first) - 1, len(second) - 1
    carry = 0
    output = []
    while i >= 0 or j >= 0 or carry:
        total = carry
        if i >= 0:
            total += ord(first[i]) - ord("0")
            i -= 1
        if j >= 0:
            total += ord(second[j]) - ord("0")
            j -= 1
        output.append(chr(ord("0") + total % 10))
        carry = total // 10
    return "".join(reversed(output))


def _sub_abs(first: str, second: str) -> str:
    """Compute first - second for normalized strings with first >= second."""
    i, j = len(first) - 1, len(second) - 1
    borrow = 0
    output = []
    while i >= 0:
        digit = ord(first[i]) - ord("0") - borrow
        if j >= 0:
            digit -= ord(second[j]) - ord("0")
            j -= 1
        if digit < 0:
            digit += 10
            borrow = 1
        else:
            borrow = 0
        output.append(chr(ord("0") + digit))
        i -= 1
    return "".join(reversed(output)).lstrip("0") or "0"


def _multiply_abs(first: str, second: str) -> str:
    if first == "0" or second == "0":
        return "0"
    digits = [0] * (len(first) + len(second))
    for i in range(len(first) - 1, -1, -1):
        left = ord(first[i]) - ord("0")
        carry = 0
        for j in range(len(second) - 1, -1, -1):
            right = ord(second[j]) - ord("0")
            total = digits[i + j + 1] + left * right + carry
            digits[i + j + 1] = total % 10
            carry = total // 10
        digits[i] += carry
    text = "".join(chr(ord("0") + digit) for digit in digits).lstrip("0")
    return text or "0"


def _divmod_abs(first: str, second: str) -> Tuple[str, str]:
    """Return (quotient, remainder) for non-negative normalized strings."""
    if second == "0":
        raise ZeroDivisionError("division by zero")
    if _compare_abs(first, second) < 0:
        return "0", first
    quotient = []
    remainder = "0"
    for character in first:
        remainder = (remainder + character).lstrip("0") or "0"
        digit = 0
        while _compare_abs(remainder, second) >= 0:
            remainder = _sub_abs(remainder, second)
            digit += 1
        quotient.append(chr(ord("0") + digit))
    return "".join(quotient).lstrip("0") or "0", remainder


def add(first: str, second: str) -> str:
    """Return first + second.  O(n + m)."""
    sign_first, digits_first = _normalize(first)
    sign_second, digits_second = _normalize(second)
    if sign_first == sign_second:
        return _format(sign_first, _add_abs(digits_first, digits_second))
    comparison = _compare_abs(digits_first, digits_second)
    if comparison == 0:
        return "0"
    if comparison > 0:
        return _format(sign_first, _sub_abs(digits_first, digits_second))
    return _format(sign_second, _sub_abs(digits_second, digits_first))


def subtract(first: str, second: str) -> str:
    """Return first - second.  O(n + m)."""
    sign_second, digits_second = _normalize(second)
    return add(first, _format(-sign_second, digits_second))


def multiply(first: str, second: str) -> str:
    """Return first * second using grade-school multiplication.  O(n*m)."""
    sign_first, digits_first = _normalize(first)
    sign_second, digits_second = _normalize(second)
    product = _multiply_abs(digits_first, digits_second)
    return _format(sign_first * sign_second, product)


def divmod_big(first: str, second: str) -> Tuple[str, str]:
    """Return (quotient, remainder) truncated toward zero.  O(n*m)."""
    sign_first, digits_first = _normalize(first)
    sign_second, digits_second = _normalize(second)
    quotient, remainder = _divmod_abs(digits_first, digits_second)
    quotient_sign = sign_first * sign_second
    remainder_sign = sign_first
    return _format(quotient_sign, quotient), _format(remainder_sign, remainder)


def divide(first: str, second: str) -> str:
    """Return the truncated quotient.  Raises ZeroDivisionError for zero."""
    return divmod_big(first, second)[0]


def mod(first: str, second: str) -> str:
    """Return the remainder with the dividend's sign."""
    return divmod_big(first, second)[1]


def compare(first: str, second: str) -> int:
    """Return -1, 0 or 1 as first <, == or > second."""
    sign_first, digits_first = _normalize(first)
    sign_second, digits_second = _normalize(second)
    if sign_first != sign_second:
        return -1 if sign_first < sign_second else 1
    comparison = _compare_abs(digits_first, digits_second)
    return comparison if sign_first > 0 else -comparison


def power(base: str, exponent: int) -> str:
    """Return base ** exponent by repeated squaring.  O(log exponent) multiplies."""
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("exponent must be an int")
    if exponent < 0:
        raise ValueError("exponent must be non-negative")
    _normalize(base)
    result = "1"
    factor = base
    while exponent:
        if exponent & 1:
            result = multiply(result, factor)
        exponent >>= 1
        if exponent:
            factor = multiply(factor, factor)
    return result


def factorial(value: int) -> str:
    """Return value! as a decimal string.  O(value^2 log value) digit work."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("factorial input must be an int")
    if value < 0:
        raise ValueError("factorial input must be non-negative")
    result = "1"
    for number in range(2, value + 1):
        result = multiply(result, str(number))
    return result


def main() -> None:
    assert add("0", "0") == "0"
    assert add("999", "1") == "1000"
    assert add("+0012", "-000") == "12"
    assert subtract("1000", "1") == "999"
    assert subtract("5", "8") == "-3"
    assert add("-5", "3") == "-2"
    assert multiply("123", "456") == "56088"
    assert multiply("-12", "0") == "0"
    assert multiply("-12", "-12") == "144"
    assert divmod_big("1000", "7") == ("142", "6")
    assert divmod_big("-1000", "7") == ("-142", "-6")
    assert divmod_big("1000", "-7") == ("-142", "6")
    assert divmod_big("-1", "2") == ("0", "-1")
    assert divide("12345678901234567890", "1000000000") == "12345678901"
    assert mod("17", "5") == "2"
    assert compare("-10", "2") == -1 and compare("10", "010") == 0
    assert power("2", 100) == str(2**100)
    assert factorial(0) == "1" and factorial(50) == str(math.factorial(50))

    rng = random.Random(4242)
    for _ in range(150):
        digits_a = rng.randint(1, 40)
        digits_b = rng.randint(1, 25)
        raw_a = "".join(rng.choice("0123456789") for _ in range(digits_a))
        raw_b = "".join(rng.choice("0123456789") for _ in range(digits_b))
        if rng.random() < 0.5:
            raw_a = "-" + raw_a
        if rng.random() < 0.5:
            raw_b = "-" + raw_b
        value_a, value_b = int(raw_a), int(raw_b)
        assert add(raw_a, raw_b) == str(value_a + value_b)
        assert subtract(raw_a, raw_b) == str(value_a - value_b)
        assert multiply(raw_a, raw_b) == str(value_a * value_b)
        if value_b != 0:
            quotient = abs(value_a) // abs(value_b)
            if (value_a < 0) != (value_b < 0):
                quotient = -quotient
            remainder = value_a - quotient * value_b
            assert divmod_big(raw_a, raw_b) == (str(quotient), str(remainder))

    for action in (
        lambda: add("", "1"),
        lambda: add("12a", "1"),
        lambda: add("+", "1"),
        lambda: divmod_big("1", "0"),
        lambda: power("2", -1),
        lambda: factorial(-1),
        lambda: compare("--1", "2"),
    ):
        try:
            action()
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        else:
            raise AssertionError("invalid bigint operation was accepted")

    print("Self-test: bigint add/subtract/multiply/divide match Python int oracle.")
    print(f"2^100 = {power('2', 100)}")
    print(f"50! has {len(factorial(50))} digits")
    print(f"(-1000) divmod 7 = {divmod_big('-1000', '7')}")


if __name__ == "__main__":
    main()
