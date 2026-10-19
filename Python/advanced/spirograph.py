"""Generate hypotrochoid spirograph art in turtle or as a PostScript file.

A hypotrochoid is traced by a point attached to a circle of radius ``r``
rolling inside a fixed circle of radius ``R``. Changing ``d`` (pen offset)
and the number of turns produces flowers, stars, and woven rings. Geometry is
computed without a GUI; importing this module does not create a window.

Usage:
    python spirograph.py                                  # turtle preview
    python spirograph.py --R 240 --r 67 --d 130 --turns 14 --save star.ps
    python spirograph.py --R 180 --r 40 --d 90 --turns 20 --preview
    python spirograph.py --R 220 --r 70 --d 110 --save woven.ps --preview

The ``--save`` mode writes a single-page PostScript document and is safe for
headless use. The default mode opens a turtle window when run directly.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Sequence

PAGE_SIZE = 600.0
Color = tuple[float, float, float]
PALETTE: tuple[Color, ...] = (
    (0.20, 0.85, 0.95),
    (0.35, 0.55, 1.00),
    (0.85, 0.38, 0.95),
    (1.00, 0.62, 0.28),
    (1.00, 0.92, 0.50),
)


def build_curve(
    R: float, r: float, d: float, turns: float, points_per_turn: int = 240
) -> list[tuple[float, float]]:
    """Sample a hypotrochoid in mathematical coordinates (y up)."""
    if R <= 0 or r <= 0 or d < 0 or turns <= 0:
        raise ValueError("R, r, and turns must be positive; d must be non-negative")
    if points_per_turn < 16:
        raise ValueError("points_per_turn must be at least 16")
    count = max(64, int(abs(turns) * points_per_turn))
    denominator = max(1e-9, r)
    phase = (R - r) / denominator
    points: list[tuple[float, float]] = []
    for index in range(count + 1):
        theta = 2.0 * math.pi * turns * index / count
        x = (R - r) * math.cos(theta) + d * math.cos(phase * theta)
        y = (R - r) * math.sin(theta) - d * math.sin(phase * theta)
        points.append((x, y))
    return points


def _color(t: float) -> Color:
    """Interpolate the five-stop palette."""
    t = max(0.0, min(1.0, t))
    scaled = t * (len(PALETTE) - 1)
    index = min(len(PALETTE) - 2, int(scaled))
    fraction = scaled - index
    left, right = PALETTE[index], PALETTE[index + 1]
    return tuple(a + (b - a) * fraction for a, b in zip(left, right))  # type: ignore[return-value]


def _fit(points: Sequence[tuple[float, float]], page: float) -> list[tuple[float, float]]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    margin = 34.0
    usable = page - 2.0 * margin
    scale = usable / max(1e-9, span_x, span_y)
    center_x, center_y = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return [
        (page / 2 + (x - center_x) * scale, page / 2 + (y - center_y) * scale)
        for x, y in points
    ]


def save_postscript(points: Sequence[tuple[float, float]], path: str | Path) -> Path:
    """Write the spirograph as single-page PostScript."""
    if len(points) < 2:
        raise ValueError("not enough points to draw")
    fitted = _fit(points, PAGE_SIZE)
    lines = [
        "%!PS-Adobe-3.0",
        "%%Creator: spirograph.py",
        f"%%BoundingBox: 0 0 {int(PAGE_SIZE)} {int(PAGE_SIZE)}",
        "%%Pages: 1",
        "%%EndComments",
        "0.035 0.045 0.075 setrgbcolor",
        f"0 0 {PAGE_SIZE:g} {PAGE_SIZE:g} rectfill",
        "1 setlinecap",
        "1 setlinejoin",
    ]
    last = len(fitted) - 1
    for index in range(last):
        red, green, blue = _color(index / last)
        x1, y1 = fitted[index]
        x2, y2 = fitted[index + 1]
        lines.append(f"{red:.4f} {green:.4f} {blue:.4f} setrgbcolor")
        lines.append("1.15 setlinewidth")
        lines.append(f"{x1:.3f} {y1:.3f} moveto {x2:.3f} {y2:.3f} lineto stroke")
    lines.extend(("showpage", "%%EOF", ""))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="ascii")
    return destination


def preview(points: Sequence[tuple[float, float]]) -> None:
    """Draw the fitted curve in a turtle window."""
    import turtle  # Lazy import keeps the module import headless-safe.

    fitted = _fit(points, PAGE_SIZE)
    screen = turtle.Screen()
    screen.setup(width=720, height=720)
    screen.title("spirograph.py")
    screen.bgcolor("#090c12")
    screen.setworldcoordinates(0, 0, PAGE_SIZE, PAGE_SIZE)
    screen.tracer(0, 0)
    pen = turtle.Turtle(visible=False)
    pen.speed(0)
    pen.penup()
    last = len(fitted) - 1
    for index in range(last):
        pen.color(*_color(index / last))
        pen.pensize(1.2)
        pen.penup()
        pen.goto(*fitted[index])
        pen.pendown()
        pen.goto(*fitted[index + 1])
    screen.update()
    screen.exitonclick()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hypotrochoid spirograph renderer.")
    parser.add_argument("--R", type=float, default=240.0, help="fixed circle radius")
    parser.add_argument("--r", type=float, default=67.0, help="rolling circle radius")
    parser.add_argument("--d", type=float, default=125.0, help="pen offset")
    parser.add_argument("--turns", type=float, default=12.0)
    parser.add_argument("--points-per-turn", type=int, default=240)
    parser.add_argument("--save", metavar="FILE.ps")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    try:
        points = build_curve(args.R, args.r, args.d, args.turns, args.points_per_turn)
    except ValueError as exc:
        parser.error(str(exc))
    if args.save:
        destination = save_postscript(points, args.save)
        print(
            f"wrote {destination} ({len(points)} points, R={args.R:g}, "
            f"r={args.r:g}, d={args.d:g}, turns={args.turns:g})"
        )
    if args.preview or not args.save:
        try:
            preview(points)
        except Exception as exc:
            print(f"could not open turtle preview: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
