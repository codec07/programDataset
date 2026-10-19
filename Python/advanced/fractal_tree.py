"""Draw a recursive fractal tree with turtle graphics or export PostScript.

The geometry is generated independently of any GUI, which makes the
``--save`` path deterministic and usable on headless machines. Importing this
module never opens a window; the turtle viewer is created only inside
``preview()`` when the program is run directly.

Usage:
    python fractal_tree.py                         # open turtle preview
    python fractal_tree.py --save tree.ps          # write PostScript, no window
    python fractal_tree.py --depth 12 --angle 28 --save tree.ps --preview
    python fractal_tree.py --seed 7 --save organic.ps

The generated PostScript is EPS-like single-page output that can be viewed in
Ghostscript, converted, or printed.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

PAGE_SIZE = 600.0


@dataclass(frozen=True, slots=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    depth: int


def build_tree(
    depth: int = 10,
    length: float = 118.0,
    angle: float = 24.0,
    ratio: float = 0.72,
    *,
    seed: int | None = None,
    page: float = PAGE_SIZE,
) -> list[Segment]:
    """Generate tree segments with a trunk rooted at the bottom center."""
    if depth < 1:
        raise ValueError("depth must be at least 1")
    if length <= 0 or ratio <= 0:
        raise ValueError("length and ratio must be positive")
    if not 0 < angle < 90:
        raise ValueError("angle must be between 0 and 90 degrees")
    rng = random.Random(seed) if seed is not None else None
    segments: list[Segment] = []

    def branch(
        x: float, y: float, heading: float, branch_length: float, level: int, width: float
    ) -> None:
        x2 = x + math.cos(math.radians(heading)) * branch_length
        y2 = y + math.sin(math.radians(heading)) * branch_length
        segments.append(Segment(x, y, x2, y2, width, level))
        if level <= 1:
            return
        jitter = rng.uniform(-5.0, 5.0) if rng else 0.0
        child_length = branch_length * ratio
        if rng:
            child_length *= rng.uniform(0.92, 1.08)
        branch(x2, y2, heading + angle + jitter, child_length, level - 1, width * 0.70)
        branch(x2, y2, heading - angle + jitter, child_length, level - 1, width * 0.70)

    branch(page / 2.0, 30.0, 90.0, length, depth, max(1.0, depth * 0.75))
    return segments


def _color(depth: int, max_depth: int) -> tuple[float, float, float]:
    """Blend from bark brown at the trunk to leaf green at the tips."""
    t = 1.0 - (depth - 1) / max(1, max_depth - 1)
    bark = (0.34, 0.20, 0.10)
    leaf = (0.18, 0.72, 0.38)
    return tuple(a + (b - a) * t for a, b in zip(bark, leaf))  # type: ignore[return-value]


def save_postscript(
    segments: Sequence[Segment], path: str | Path, *, page: float = PAGE_SIZE
) -> Path:
    """Write the tree as a self-contained single-page PostScript document."""
    if not segments:
        raise ValueError("no segments to export")
    max_depth = max(segment.depth for segment in segments)
    lines = [
        "%!PS-Adobe-3.0",
        "%%Creator: fractal_tree.py",
        f"%%BoundingBox: 0 0 {int(page)} {int(page)}",
        "%%Pages: 1",
        "%%EndComments",
        "1 setlinecap",
        "1 setlinejoin",
    ]
    for segment in segments:
        red, green, blue = _color(segment.depth, max_depth)
        lines.append(f"{red:.4f} {green:.4f} {blue:.4f} setrgbcolor")
        lines.append(f"{max(0.2, segment.width * 0.55):.3f} setlinewidth")
        lines.append(
            f"{segment.x1:.3f} {segment.y1:.3f} moveto "
            f"{segment.x2:.3f} {segment.y2:.3f} lineto stroke"
        )
    lines.extend(("showpage", "%%EOF", ""))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="ascii")
    return destination


def preview(segments: Sequence[Segment], *, page: float = PAGE_SIZE) -> None:
    """Open a turtle window and draw the generated segments."""
    import turtle  # Imported lazily so module import is GUI-free.

    max_depth = max(segment.depth for segment in segments)
    screen = turtle.Screen()
    screen.setup(width=720, height=720)
    screen.title("fractal_tree.py")
    screen.bgcolor("#0b1016")
    screen.setworldcoordinates(0, 0, page, page)
    screen.tracer(0, 0)
    pen = turtle.Turtle(visible=False)
    pen.speed(0)
    pen.penup()
    for segment in segments:
        red, green, blue = _color(segment.depth, max_depth)
        pen.color(red, green, blue)
        pen.pensize(max(0.5, segment.width * 0.55))
        pen.penup()
        pen.goto(segment.x1, segment.y1)
        pen.pendown()
        pen.goto(segment.x2, segment.y2)
    screen.update()
    screen.exitonclick()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recursive fractal tree (turtle/PostScript).")
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--length", type=float, default=118.0)
    parser.add_argument("--angle", type=float, default=24.0)
    parser.add_argument("--ratio", type=float, default=0.72)
    parser.add_argument("--seed", type=int, help="optional organic randomness")
    parser.add_argument("--save", metavar="FILE.ps", help="write PostScript instead of using a window")
    parser.add_argument("--preview", action="store_true", help="also open the turtle window")
    args = parser.parse_args(argv)

    try:
        segments = build_tree(
            args.depth, args.length, args.angle, args.ratio, seed=args.seed
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.save:
        destination = save_postscript(segments, args.save)
        print(
            f"wrote {destination} ({len(segments)} segments, depth={args.depth}, "
            f"angle={args.angle:g} deg, seed={args.seed})"
        )
    if args.preview or not args.save:
        try:
            preview(segments)
        except Exception as exc:  # Tk may be unavailable on headless machines.
            print(f"could not open turtle preview: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
