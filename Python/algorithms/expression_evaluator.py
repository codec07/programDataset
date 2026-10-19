"""Arithmetic expression evaluator using a tokenizer and shunting-yard parsing.

Pipeline:

1. ``tokenize`` scans the text into numbers, identifiers, operators and
   parentheses (``**`` is accepted as a synonym for ``^``).
2. ``to_rpn`` applies the shunting-yard algorithm to produce reverse Polish
   notation, handling unary minus/plus.
3. ``evaluate`` walks the RPN with an operand stack.

Complexity: O(n) time and O(n) space for an expression of n tokens.

Operator table:

* ``+ -`` precedence 1, left associative
* ``* / %`` precedence 2, left associative
* ``^`` precedence 4, right associative (so ``2^3^2 == 512``)
* unary minus precedence 4, right associative (so ``-2^2 == -4``)

The module never calls ``eval``.  Identifiers are resolved from an optional
``variables`` mapping.  Invalid characters, unknown names, misplaced operands,
bad parentheses and division by zero all raise exceptions.  The demo checks a
range of known expressions and every error path.
"""

from __future__ import annotations

import math
from typing import Dict, List, Mapping, Optional, Sequence


_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "^": 4, "u": 4}
_RIGHT_ASSOCIATIVE = {"^", "u"}
_OPERATORS = set("+-*/%^")


def _is_digit(character: str) -> bool:
    return "0" <= character <= "9"


def _is_identifier_start(character: str) -> bool:
    return character.isalpha() or character == "_"


def _is_identifier_part(character: str) -> bool:
    return character.isalnum() or character == "_"


def tokenize(expression: str) -> List[str]:
    """Split *expression* into tokens, or raise ValueError on bad input."""
    if not isinstance(expression, str):
        raise TypeError("expression must be a string")
    tokens: List[str] = []
    index, length = 0, len(expression)
    while index < length:
        character = expression[index]
        if character.isspace():
            index += 1
        elif _is_digit(character) or character == ".":
            start = index
            while index < length and (_is_digit(expression[index]) or expression[index] == "."):
                index += 1
            literal = expression[start:index]
            if literal.count(".") > 1:
                raise ValueError(f"invalid number literal: {literal!r}")
            tokens.append(literal)
        elif _is_identifier_start(character):
            start = index
            while index < length and _is_identifier_part(expression[index]):
                index += 1
            tokens.append(expression[start:index])
        elif character in _OPERATORS or character in "()":
            if (
                character == "*"
                and index + 1 < length
                and expression[index + 1] == "*"
            ):
                tokens.append("^")
                index += 2
                continue
            tokens.append(character)
            index += 1
        else:
            raise ValueError(f"unexpected character {character!r}")
    if not tokens:
        raise ValueError("expression is empty")
    return tokens


def _is_number(token: str) -> bool:
    return bool(token) and (_is_digit(token[0]) or token[0] == ".")


def to_rpn(tokens: Sequence[str]) -> List[str]:
    """Convert infix *tokens* to reverse Polish notation (shunting-yard)."""
    output: List[str] = []
    stack: List[str] = []
    previous: Optional[str] = None  # 'value', 'operator', 'open' or None
    for token in tokens:
        if _is_number(token) or _is_identifier_start(token[0]):
            output.append(token)
            previous = "value"
        elif token == "(":
            stack.append(token)
            previous = "open"
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("mismatched parentheses")
            stack.pop()
            previous = "value"
        else:
            expect_value = previous is None or previous in ("operator", "open")
            if token == "-" and expect_value:
                token = "u"
            elif token == "+" and expect_value:
                previous = "operator"
                continue
            while stack and stack[-1] != "(":
                top = stack[-1]
                if _PRECEDENCE[top] > _PRECEDENCE[token] or (
                    _PRECEDENCE[top] == _PRECEDENCE[token]
                    and token not in _RIGHT_ASSOCIATIVE
                ):
                    output.append(stack.pop())
                else:
                    break
            stack.append(token)
            previous = "operator"
    while stack:
        top = stack.pop()
        if top == "(":
            raise ValueError("mismatched parentheses")
        output.append(top)
    return output


def _resolve(token: str, variables: Mapping[str, float]) -> float:
    if token in variables:
        value = variables[token]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"variable {token!r} is not a number")
        return float(value)
    raise ValueError(f"unknown identifier: {token!r}")


def evaluate(expression: str, variables: Optional[Mapping[str, float]] = None) -> float:
    """Evaluate *expression* and return a float.

    Supports ``+ - * / % ^``, parentheses, unary plus/minus and named variables.

    Raises:
        ValueError: syntax errors, unknown identifiers, bad parentheses,
            non-integer powers of negative numbers.
        ZeroDivisionError: division or modulo by zero.
        TypeError: non-numeric variable values.
    """
    if variables is None:
        variables = {}
    if not isinstance(variables, Mapping):
        raise TypeError("variables must be a mapping")
    operands: List[float] = []
    for token in to_rpn(tokenize(expression)):
        if token == "u":
            if not operands:
                raise ValueError("unary minus without an operand")
            operands.append(-operands.pop())
        elif _is_number(token):
            operands.append(float(token))
        elif _is_identifier_start(token[0]):
            operands.append(_resolve(token, variables))
        else:
            if len(operands) < 2:
                raise ValueError(f"operator {token!r} is missing an operand")
            right = operands.pop()
            left = operands.pop()
            if token == "+":
                operands.append(left + right)
            elif token == "-":
                operands.append(left - right)
            elif token == "*":
                operands.append(left * right)
            elif token == "/":
                if right == 0.0:
                    raise ZeroDivisionError("division by zero")
                operands.append(left / right)
            elif token == "%":
                if right == 0.0:
                    raise ZeroDivisionError("modulo by zero")
                operands.append(left % right)
            else:  # '^'
                operands.append(math.pow(left, right))
    if len(operands) != 1:
        raise ValueError("malformed expression")
    return operands[0]


def main() -> None:
    assert evaluate("3 + 4 * 2") == 11.0
    assert evaluate("(3 + 4) * 2") == 14.0
    assert evaluate("2^3^2") == 512.0          # right associative
    assert evaluate("2**10") == 1024.0         # ** synonym
    assert evaluate("-2^2") == -4.0            # unary minus binds looser than ^
    assert evaluate("2^-3") == 0.125
    assert evaluate("2 * -3") == -6.0
    assert evaluate("--5") == 5.0
    assert evaluate("10 % 3") == 1.0
    assert evaluate("7 / 2") == 3.5
    assert evaluate("1.5 + .5") == 2.0
    assert evaluate("((((1))))") == 1.0
    assert evaluate("x + y * 2", {"x": 1, "y": 5}) == 11.0
    assert abs(evaluate("pi_ish", {"pi_ish": 3.14159}) - 3.14159) < 1e-12

    # Unary handling inside parentheses and after operators.
    assert evaluate("(-3) * (+2)") == -6.0
    assert evaluate("4 - -2") == 6.0
    assert evaluate("2 ^ (-1)") == 0.5

    for action, expected in [
        (lambda: evaluate("3 +"), ValueError),
        (lambda: evaluate("(1 + 2"), ValueError),
        (lambda: evaluate("1 + 2)"), ValueError),
        (lambda: evaluate("1 $ 2"), ValueError),
        (lambda: evaluate("1.2.3"), ValueError),
        (lambda: evaluate("unknown + 1"), ValueError),
        (lambda: evaluate(""), ValueError),
        (lambda: evaluate("3 / 0"), ZeroDivisionError),
        (lambda: evaluate("3 % 0"), ZeroDivisionError),
        (lambda: evaluate("x", {"x": "text"}), TypeError),
    ]:
        try:
            action()
        except expected:
            pass
        else:
            raise AssertionError(f"expected {expected.__name__}")

    print("Self-test: tokenizer, shunting-yard and RPN evaluation passed.")
    print(f"3 + 4 * 2 = {evaluate('3 + 4 * 2')}")
    print(f"2^3^2 = {evaluate('2^3^2')}, -2^2 = {evaluate('-2^2')}, 2^-3 = {evaluate('2^-3')}")
    print(f"x + y*2 with x=1,y=5 -> {evaluate('x + y * 2', {'x': 1, 'y': 5})}")


if __name__ == "__main__":
    main()
