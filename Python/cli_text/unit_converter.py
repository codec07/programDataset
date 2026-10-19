#!/usr/bin/env python3
"""Convert values between units of length, mass, temperature and more.

Supported categories: length, mass, temperature, volume, data, time,
speed and area. Unit names are case-insensitive and several aliases are
accepted (for example "metres", "lbs" or "celsius").

Usage:
    python unit_converter.py 10 km mi
    python unit_converter.py 72 f c --precision 2
    python unit_converter.py 1.5 gib mib
    python unit_converter.py 100 mph kmh
    python unit_converter.py --list
    python unit_converter.py --list temperature
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Sequence

# Factors convert a unit to its category's base unit.
CATEGORIES: dict[str, dict[str, float]] = {
    "length": {
        "m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "um": 1e-6,
        "mi": 1609.344, "yd": 0.9144, "ft": 0.3048, "in": 0.0254,
        "nmi": 1852.0,
    },
    "mass": {
        "kg": 1.0, "g": 0.001, "mg": 1e-6, "t": 1000.0,
        "lb": 0.45359237, "oz": 0.028349523125, "st": 6.35029318,
    },
    "volume": {
        "l": 1.0, "ml": 0.001, "m3": 1000.0, "gal": 3.785411784,
        "qt": 0.946352946, "pt": 0.473176473, "cup": 0.2365882365,
        "floz": 0.0295735295625, "tbsp": 0.01478676478125,
        "tsp": 0.00492892159375,
    },
    "data": {
        "b": 1.0, "kb": 1000.0, "mb": 1e6, "gb": 1e9, "tb": 1e12,
        "kib": 1024.0, "mib": 1024.0**2, "gib": 1024.0**3, "tib": 1024.0**4,
    },
    "time": {
        "s": 1.0, "ms": 0.001, "us": 1e-6, "min": 60.0, "h": 3600.0,
        "day": 86400.0, "week": 604800.0,
    },
    "speed": {
        "mps": 1.0, "kmh": 1 / 3.6, "mph": 0.44704, "knot": 0.514444,
        "fts": 0.3048,
    },
    "area": {
        "m2": 1.0, "km2": 1e6, "cm2": 1e-4, "ha": 10000.0,
        "acre": 4046.8564224, "ft2": 0.09290304, "in2": 0.00064516,
        "mi2": 2589988.110336,
    },
}

ALIASES: dict[str, str] = {
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "centimeter": "cm", "centimeters": "cm", "millimeter": "mm",
    "millimeters": "mm", "mile": "mi", "miles": "mi", "yard": "yd",
    "yards": "yd", "foot": "ft", "feet": "ft", "inch": "in", "inches": "in",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg", "gram": "g",
    "grams": "g", "pound": "lb", "pounds": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz", "stone": "st", "tonne": "t",
    "tonnes": "t", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "milliliter": "ml", "milliliters": "ml", "gallon": "gal", "gallons": "gal",
    "quart": "qt", "quarts": "qt", "pint": "pt", "pints": "pt",
    "byte": "b", "bytes": "b", "kilobyte": "kb", "megabyte": "mb",
    "gigabyte": "gb", "terabyte": "tb", "kibibyte": "kib", "mebibyte": "mib",
    "gibibyte": "gib", "tebibyte": "tib", "second": "s", "seconds": "s",
    "sec": "s", "minute": "min", "minutes": "min", "hour": "h",
    "hours": "h", "hr": "h", "hrs": "h", "days": "day", "weeks": "week",
    "mps": "mps", "m/s": "mps", "meters per second": "mps",
    "kph": "kmh", "kmph": "kmh", "knots": "knot",
    "hectare": "ha", "hectares": "ha", "acres": "acre",
}

TEMPERATURE_UNITS = {
    "c": "celsius", "celsius": "celsius", "centigrade": "celsius",
    "f": "fahrenheit", "fahrenheit": "fahrenheit",
    "k": "kelvin", "kelvin": "kelvin",
}


@dataclass(frozen=True)
class Conversion:
    """A resolved conversion request."""

    category: str
    source: str
    target: str


def list_units(category: str | None = None) -> None:
    """Print selectable units, optionally for one category."""
    names = [category.lower()] if category else sorted({*CATEGORIES, "temperature"})
    for name in names:
        if name == "temperature":
            print("temperature: c, f, k")
            continue
        if name not in CATEGORIES:
            print(f"error: unknown category: {name}", file=sys.stderr)
            continue
        units = ", ".join(sorted(CATEGORIES[name]))
        print(f"{name}: {units}")


def normalize(unit: str) -> str:
    """Lower-case a unit and apply the alias table."""
    cleaned = unit.strip().lower().replace("°", "")
    return ALIASES.get(cleaned, cleaned)


def find_category(unit: str) -> str | None:
    """Return the category containing *unit*, if any."""
    if unit in TEMPERATURE_UNITS:
        return "temperature"
    for category, factors in CATEGORIES.items():
        if unit in factors:
            return category
    return None


def resolve(source: str, target: str | None) -> Conversion:
    """Validate units and determine the shared category."""
    src = normalize(source)
    category = find_category(src)
    if category is None:
        raise ValueError(f"unknown unit: {source}")

    if target is None:
        raise ValueError("a target unit is required (try --list)")
    dst = normalize(target)
    target_category = find_category(dst)
    if target_category is None:
        raise ValueError(f"unknown unit: {target}")
    if target_category != category:
        raise ValueError(
            f"cannot convert {src} ({category}) to {dst} ({target_category})"
        )
    return Conversion(category, src, dst)


def to_celsius(value: float, unit: str) -> float:
    """Convert a temperature to Celsius, rejecting values below absolute zero."""
    if unit == "celsius":
        result = value
    elif unit == "fahrenheit":
        result = (value - 32) * 5 / 9
    else:
        result = value - 273.15
    if result < -273.15:
        raise ValueError("temperature is below absolute zero")
    return result


def from_celsius(value: float, unit: str) -> float:
    """Convert Celsius to the requested temperature unit."""
    if unit == "celsius":
        return value
    if unit == "fahrenheit":
        return value * 9 / 5 + 32
    if value < -273.15:
        raise ValueError("temperature is below absolute zero")
    return value + 273.15


def convert(value: float, conversion: Conversion) -> float:
    """Perform the actual conversion."""
    if conversion.category == "temperature":
        source = TEMPERATURE_UNITS[conversion.source]
        target = TEMPERATURE_UNITS[conversion.target]
        return from_celsius(to_celsius(value, source), target)
    factors = CATEGORIES[conversion.category]
    return value * factors[conversion.source] / factors[conversion.target]


def format_number(value: float, precision: int) -> str:
    """Format a float without trailing zeros while respecting precision."""
    if value != 0 and (abs(value) >= 1e12 or abs(value) < 1e-6):
        return f"{value:.{precision}e}"
    text = f"{value:.{precision}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert values between units.",
        epilog="Run with --list to see all supported units.",
    )
    parser.add_argument("value", nargs="?", help="numeric value to convert")
    parser.add_argument("source", nargs="?", help="unit to convert from")
    parser.add_argument("target", nargs="?", help="unit to convert to")
    parser.add_argument("--list", action="store_true", dest="show_list",
                        help="list units, optionally for one category")
    parser.add_argument("--category", help="restrict --list to a category")
    parser.add_argument("--precision", type=int, default=6, metavar="N",
                        help="decimal places (default: 6)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON")
    args = parser.parse_args(argv)

    if not 0 <= args.precision <= 12:
        parser.error("--precision must be between 0 and 12")
    if not args.show_list and (args.value is None or args.source is None):
        parser.error("value and source unit are required (or use --list)")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.show_list:
        list_units(args.category)
        return 0

    try:
        value = float(args.value)
    except ValueError:
        print(f"error: not a number: {args.value}", file=sys.stderr)
        return 1
    if value != value or value in (float("inf"), float("-inf")):
        print("error: value must be finite", file=sys.stderr)
        return 1

    try:
        conversion = resolve(args.source, args.target)
        result = convert(value, conversion)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps({
            "value": value,
            "from": conversion.source,
            "to": conversion.target,
            "category": conversion.category,
            "result": result,
        }, indent=2))
    else:
        print(
            f"{format_number(value, args.precision)} {conversion.source} = "
            f"{format_number(result, args.precision)} {conversion.target}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
