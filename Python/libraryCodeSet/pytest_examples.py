"""pytest — practical single-file examples.

Install:  pip install pytest
Run:      pytest pytest_examples.py -v
          python pytest_examples.py          # also works, invokes pytest

A single file can hold both the code under test and its tests. This example
demonstrates assertions, fixtures (including yield/scope), parametrization,
exception checks, approximate comparisons, tmp_path, monkeypatch, capsys,
marks, skips, and xfail.

These examples are illustrative, not a test suite for the dataset. See ../README.md.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


# ===========================================================================
# Code under test
# ===========================================================================
def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b


def normalize_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("name must not be empty")
    return cleaned.title()


@dataclass
class Cart:
    items: list[tuple[str, float, int]]

    def add(self, name: str, price: float, quantity: int = 1) -> None:
        if price < 0:
            raise ValueError("price must be non-negative")
        if quantity < 1:
            raise ValueError("quantity must be positive")
        self.items.append((name, price, quantity))

    def total(self) -> float:
        return round(sum(price * quantity for _, price, quantity in self.items), 2)

    def to_json(self) -> str:
        return json.dumps({"items": self.items, "total": self.total()})

    @classmethod
    def from_json(cls, text: str) -> "Cart":
        payload = json.loads(text)
        cart = cls(items=[])
        for name, price, quantity in payload["items"]:
            cart.add(name, price, quantity)
        return cart


def write_config(path: Path, values: dict) -> Path:
    path.write_text(json.dumps(values, indent=2), encoding="utf-8")
    return path


def read_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ===========================================================================
# Basic tests
# ===========================================================================
def test_add_integers() -> None:
    assert add(2, 3) == 5


def test_add_floats_uses_approx() -> None:
    assert add(0.1, 0.2) == pytest.approx(0.3)


def test_divide() -> None:
    assert divide(10, 4) == 2.5


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ZeroDivisionError, match="divide by zero"):
        divide(1, 0)


def test_normalize_name() -> None:
    assert normalize_name("  ada   lovelace ") == "Ada Lovelace"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("grace hopper", "Grace Hopper"),
        ("ALAN TURING", "Alan Turing"),
        ("  linus  ", "Linus"),
        ("edsger w. dijkstra", "Edsger W. Dijkstra"),
    ],
)
def test_normalize_name_parametrized(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
def test_normalize_name_rejects_blank(bad_name: str) -> None:
    with pytest.raises(ValueError):
        normalize_name(bad_name)


# ===========================================================================
# Fixtures
# ===========================================================================
@pytest.fixture
def empty_cart() -> Cart:
    return Cart(items=[])


@pytest.fixture
def stocked_cart(empty_cart: Cart) -> Cart:
    empty_cart.add("widget", 2.50, 4)
    empty_cart.add("gadget", 9.99, 2)
    return empty_cart


def test_empty_cart_total(empty_cart: Cart) -> None:
    assert empty_cart.total() == 0


def test_stocked_cart_total(stocked_cart: Cart) -> None:
    # 4 * 2.50 + 2 * 9.99 = 29.98
    assert stocked_cart.total() == pytest.approx(29.98)


def test_cart_rejects_negative_price(empty_cart: Cart) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        empty_cart.add("bad", -1.0)


# Yield fixture with setup and teardown
@pytest.fixture
def temp_json_file(tmp_path: Path):
    path = tmp_path / "config.json"
    write_config(path, {"debug": True, "retries": 3})
    yield path
    # Teardown runs after the test; tmp_path is cleaned up by pytest anyway
    if path.exists():
        path.unlink()


def test_read_config(temp_json_file: Path) -> None:
    config = read_config(temp_json_file)
    assert config["debug"] is True
    assert config["retries"] == 3


# Module-scoped fixture: created once for all tests in this module
@pytest.fixture(scope="module")
def shared_lookup() -> dict[str, int]:
    print("\n[fixture] building shared lookup")
    return {"one": 1, "two": 2, "three": 3}


def test_lookup_has_three(shared_lookup: dict[str, int]) -> None:
    assert shared_lookup["three"] == 3


def test_lookup_size(shared_lookup: dict[str, int]) -> None:
    assert len(shared_lookup) == 3


# ===========================================================================
# Serialization and round-trips
# ===========================================================================
def test_cart_json_round_trip(stocked_cart: Cart) -> None:
    restored = Cart.from_json(stocked_cart.to_json())
    assert restored.items == stocked_cart.items
    assert restored.total() == stocked_cart.total()


def test_cart_json_shape(stocked_cart: Cart) -> None:
    payload = json.loads(stocked_cart.to_json())
    assert set(payload) == {"items", "total"}
    assert len(payload["items"]) == 2


# ===========================================================================
# tmp_path, monkeypatch, capsys
# ===========================================================================
def test_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "settings.json"
    path.parent.mkdir()
    write_config(path, {"name": "dataset", "version": 2})
    assert read_config(path) == {"name": "dataset", "version": 2}
    assert path.exists()


def test_monkeypatch_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATASET_MODE", "test")
    monkeypatch.setattr(sys, "platform", "test-platform")
    monkeypatch.delenv("DATASET_MISSING", raising=False)

    import os

    assert os.environ["DATASET_MODE"] == "test"
    assert sys.platform == "test-platform"
    assert "DATASET_MISSING" not in os.environ


def test_capsys(capsys: pytest.CaptureFixture[str]) -> None:
    print("hello from the test")
    captured = capsys.readouterr()
    assert captured.out.strip() == "hello from the test"
    assert captured.err == ""


# ===========================================================================
# Marks, skips, and expected failures
# ===========================================================================
@pytest.mark.slow
def test_marked_slow() -> None:
    # Run or exclude with: pytest -m "not slow"
    assert add(1, 1) == 2


@pytest.mark.skip(reason="demonstration of an unconditional skip")
def test_skipped() -> None:
    assert False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only demonstration")
def test_posix_only() -> None:
    assert True


@pytest.mark.xfail(reason="known limitation, tracked as an example", strict=True)
def test_expected_failure() -> None:
    assert add(2, 2) == 5


# ===========================================================================
# Test classes
# ===========================================================================
class TestCart:
    def test_add_increases_total(self, empty_cart: Cart) -> None:
        empty_cart.add("item", 5.0, 2)
        assert empty_cart.total() == 10.0

    def test_add_zero_quantity_rejected(self, empty_cart: Cart) -> None:
        with pytest.raises(ValueError):
            empty_cart.add("item", 5.0, 0)

    def test_rounding(self, empty_cart: Cart) -> None:
        empty_cart.add("a", 0.335, 3)
        assert empty_cart.total() == 1.0  # rounded to two decimals


# ===========================================================================
# Optional: run this file as a script
# ===========================================================================
def main() -> int:
    arguments = [str(Path(__file__).resolve()), "-v", "--tb=short"]
    # Uncomment to exclude the slow demonstration:
    # arguments += ["-m", "not slow"]
    return int(pytest.main(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
