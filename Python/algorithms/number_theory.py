"""Number theory: gcd, modular arithmetic, primality, factoring and CRT.

Complexity summary (using Python's fast small-int arithmetic):

* ``gcd`` / ``extended_gcd`` - O(log min(a, b))
* ``lcm``                    - O(log min(a, b))
* ``pow_mod``                - O(log exponent) multiplications
* ``mod_inverse``            - O(log modulus)
* ``sieve``                  - O(limit log log limit) time, O(limit) space
* ``is_prime``               - O(log^3 n) deterministic Miller-Rabin (64-bit safe)
* ``factorize``              - O(sqrt(n)) trial division
* ``euler_phi`` / ``divisors`` - O(sqrt(n))
* ``crt``                    - O(k log M) for k congruences

All inputs are validated; meaningless requests (negative modulus, zero
division, inconsistent CRT systems) raise clear exceptions.  The demo compares
primality against a naive reference over a range and checks known values.
"""

from __future__ import annotations

from typing import List, Tuple


def _check_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    return value


def gcd(first: int, second: int) -> int:
    """Greatest common divisor (non-negative).  O(log min(|a|, |b|))."""
    _check_int(first, "first")
    _check_int(second, "second")
    first, second = abs(first), abs(second)
    while second:
        first, second = second, first % second
    return first


def lcm(first: int, second: int) -> int:
    """Least common multiple (0 when either argument is 0)."""
    _check_int(first, "first")
    _check_int(second, "second")
    if first == 0 or second == 0:
        return 0
    return abs(first // gcd(first, second) * second)


def extended_gcd(first: int, second: int) -> Tuple[int, int, int]:
    """Return (g, x, y) with ``first*x + second*y == g == gcd(first, second)``.

    Iterative extended Euclidean algorithm.  O(log min(|a|, |b|)).
    """
    _check_int(first, "first")
    _check_int(second, "second")
    old_r, remainder = first, second
    old_x, x = 1, 0
    old_y, y = 0, 1
    while remainder:
        quotient = old_r // remainder
        old_r, remainder = remainder, old_r - quotient * remainder
        old_x, x = x, old_x - quotient * x
        old_y, y = y, old_y - quotient * y
    return old_r, old_x, old_y


def mod_inverse(value: int, modulus: int) -> int:
    """Return the inverse of *value* modulo *modulus* in ``[0, modulus)``.

    Raises ValueError when no inverse exists (non-coprime inputs).
    """
    _check_int(value, "value")
    modulus = _check_int(modulus, "modulus")
    if modulus <= 1:
        raise ValueError("modulus must be greater than 1")
    g, x, _ = extended_gcd(value % modulus, modulus)
    if g != 1:
        raise ValueError(f"{value} has no inverse modulo {modulus}")
    return x % modulus


def pow_mod(base: int, exponent: int, modulus: int) -> int:
    """Return ``base ** exponent % modulus`` by square-and-multiply."""
    _check_int(base, "base")
    exponent = _check_int(exponent, "exponent")
    modulus = _check_int(modulus, "modulus")
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    if exponent < 0:
        raise ValueError("exponent must be non-negative")
    result = 1
    base %= modulus
    while exponent:
        if exponent & 1:
            result = result * base % modulus
        base = base * base % modulus
        exponent >>= 1
    return result


_MILLER_RABIN_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


def is_prime(number: int) -> bool:
    """Deterministic Miller-Rabin primality test for all 64-bit integers.

    Time: O(log^3 n).  Space: O(1).
    """
    _check_int(number, "number")
    if number < 2:
        return False
    for small in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if number % small == 0:
            return number == small
    odd_part, power = number - 1, 0
    while odd_part % 2 == 0:
        odd_part //= 2
        power += 1
    for base in _MILLER_RABIN_BASES:
        if base % number == 0:
            continue
        witness = pow_mod(base, odd_part, number)
        if witness in (1, number - 1):
            continue
        for _ in range(power - 1):
            witness = witness * witness % number
            if witness == number - 1:
                break
        else:
            return False
    return True


def _is_prime_naive(number: int) -> bool:
    """O(sqrt(n)) reference implementation used for testing."""
    if number < 2:
        return False
    divisor = 2
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 1
    return True


def sieve(limit: int) -> List[int]:
    """Return all primes <= *limit* with the sieve of Eratosthenes."""
    limit = _check_int(limit, "limit")
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit < 2:
        return []
    flags = bytearray([1]) * (limit + 1)
    flags[0] = flags[1] = 0
    divisor = 2
    while divisor * divisor <= limit:
        if flags[divisor]:
            start = divisor * divisor
            flags[start::divisor] = bytearray(len(range(start, limit + 1, divisor)))
        divisor += 1
    return [value for value in range(limit + 1) if flags[value]]


def factorize(number: int) -> List[Tuple[int, int]]:
    """Return the prime factorization as sorted (prime, exponent) pairs."""
    number = _check_int(number, "number")
    if number < 1:
        raise ValueError("factorization requires a positive integer")
    factors: List[Tuple[int, int]] = []
    exponent = 0
    while number % 2 == 0:
        number //= 2
        exponent += 1
    if exponent:
        factors.append((2, exponent))
    divisor = 3
    while divisor * divisor <= number:
        exponent = 0
        while number % divisor == 0:
            number //= divisor
            exponent += 1
        if exponent:
            factors.append((divisor, exponent))
        divisor += 2
    if number > 1:
        factors.append((number, 1))
    return factors


def euler_phi(number: int) -> int:
    """Euler's totient: count of integers in [1, n] coprime to n."""
    number = _check_int(number, "number")
    if number < 1:
        raise ValueError("phi requires a positive integer")
    result = number
    for prime, _ in factorize(number):
        result -= result // prime
    return result


def divisors(number: int) -> List[int]:
    """Return all positive divisors in ascending order.  O(sqrt(n))."""
    number = _check_int(number, "number")
    if number < 1:
        raise ValueError("divisors requires a positive integer")
    small: List[int] = []
    large: List[int] = []
    candidate = 1
    while candidate * candidate <= number:
        if number % candidate == 0:
            small.append(candidate)
            if candidate != number // candidate:
                large.append(number // candidate)
        candidate += 1
    return small + large[::-1]


def crt(
    remainders: List[int], moduli: List[int]
) -> Tuple[int, int]:
    """Generalized Chinese Remainder Theorem.

    Returns (x, M) with ``x mod M`` the smallest non-negative solution of
    ``x == remainders[i] (mod moduli[i])``.  Moduli need not be coprime, but the
    system must be consistent.

    Raises ValueError for empty/mismatched input, non-positive moduli, or an
    inconsistent system.
    """
    if not remainders or len(remainders) != len(moduli):
        raise ValueError("remainders and moduli must be non-empty and equal length")
    for modulus in moduli:
        if _check_int(modulus, "modulus") <= 0:
            raise ValueError("moduli must be positive")
    solution, current = 0, 1
    for remainder, modulus in zip(remainders, moduli):
        _check_int(remainder, "remainder")
        target = remainder % modulus
        g, _, _ = extended_gcd(current, modulus)
        if (target - solution) % g != 0:
            raise ValueError("inconsistent congruence system")
        reduced = modulus // g
        if reduced > 1:
            step = (
                (target - solution) // g % reduced
                * mod_inverse((current // g) % reduced, reduced)
            ) % reduced
        else:
            step = 0
        solution += current * step
        current = current // g * modulus
        solution %= current
    return solution, current


def main() -> None:
    assert gcd(0, 5) == 5 and gcd(-12, 18) == 6 and gcd(17, 5) == 1
    assert lcm(4, 6) == 12 and lcm(0, 9) == 0

    for first, second in [(240, 46), (-7, 13), (0, 0), (99, 78)]:
        g, x, y = extended_gcd(first, second)
        assert g == gcd(first, second)
        assert first * x + second * y == g, (first, second, g, x, y)

    assert mod_inverse(3, 11) == 4 and 3 * 4 % 11 == 1
    assert mod_inverse(7, 40) == 23
    assert pow_mod(2, 10, 1000) == 24
    assert pow_mod(3, 0, 7) == 1

    primes = sieve(100)
    assert primes[:5] == [2, 3, 5, 7, 11] and len(primes) == 25
    assert sieve(1) == []
    for number in range(2, 3000):
        assert is_prime(number) == _is_prime_naive(number), number
    for carmichael in (561, 1105, 1729, 2465):
        assert _is_prime_naive(carmichael) is False and is_prime(carmichael) is False
    assert is_prime(2_147_483_647) is True          # 2^31 - 1
    assert is_prime(9_007_199_254_740_993) is False  # 2^53 + 1 is divisible by 3

    assert factorize(360) == [(2, 3), (3, 2), (5, 1)]
    assert factorize(97) == [(97, 1)]
    assert euler_phi(36) == 12 and euler_phi(1) == 1
    assert divisors(36) == [1, 2, 3, 4, 6, 9, 12, 18, 36]
    assert divisors(97) == [1, 97]

    solution, modulus = crt([2, 3, 2], [3, 5, 7])
    assert solution == 23 and modulus == 105
    assert solution % 3 == 2 and solution % 5 == 3 and solution % 7 == 2
    # Non-coprime but consistent system.
    solution2, modulus2 = crt([1, 3], [4, 6])
    assert solution2 % 4 == 1 and solution2 % 6 == 3

    for action in (
        lambda: mod_inverse(2, 4),
        lambda: pow_mod(2, -1, 5),
        lambda: pow_mod(2, 3, 0),
        lambda: factorize(0),
        lambda: sieve(-1),
        lambda: crt([1], [0]),
        lambda: crt([1, 2], [2, 4]),
        lambda: crt([], []),
    ):
        try:
            action()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("invalid number-theory input was accepted")

    print("Self-test: gcd/EGCD, modular arithmetic, primality, factoring, CRT passed.")
    print(f"primes below 100: {primes}")
    print(f"factorize(360)={factorize(360)}, phi(36)={euler_phi(36)}")
    print(f"CRT solution to x=2(3),3(5),2(7): {solution} mod {modulus}")


if __name__ == "__main__":
    main()
