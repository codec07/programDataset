"""Render the Mandelbrot set to PNG or PPM with no external dependencies.

Escape-time iteration uses smooth (continuous) coloring and a five-stop
palette. The PNG path contains a small encoder built on ``zlib`` and
``struct``; the PPM path writes a plain P6 image.

Usage:
    python mandelbrot.py --size 800x600 --iterations 256 -o mandelbrot.png
    python mandelbrot.py --size 64x64 --iterations 80 -o tiny.png
    python mandelbrot.py --size 400x300 --zoom 8 --center=-0.743643,0.131825 -o zoom.ppm

For a quick smoke test use ``--size 64x64``.
"""

from __future__ import annotations

import argparse
import math
import struct
import zlib
from pathlib import Path
from typing import Sequence

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
Color = tuple[int, int, int]
PALETTE: tuple[tuple[float, Color], ...] = (
    (0.00, (7, 10, 28)),
    (0.16, (26, 62, 164)),
    (0.40, (10, 190, 201)),
    (0.68, (252, 176, 58)),
    (0.86, (255, 245, 210)),
    (1.00, (120, 38, 122)),
)


def _chunk(tag: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(tag)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def write_png(path: str | Path, width: int, height: int, rgb: bytes | bytearray) -> Path:
    """Write an 8-bit RGB PNG (filter type 0 for every scanline)."""
    if len(rgb) != width * height * 3:
        raise ValueError("RGB buffer does not match dimensions")
    stride = width * 3
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        start = row * stride
        raw.extend(rgb[start : start + stride])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    blob = (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    return destination


def write_ppm(path: str | Path, width: int, height: int, rgb: bytes | bytearray) -> Path:
    """Write a binary P6 PPM file."""
    if len(rgb) != width * height * 3:
        raise ValueError("RGB buffer does not match dimensions")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    destination.write_bytes(header + bytes(rgb))
    return destination


def palette(value: float) -> Color:
    """Interpolate a color for a normalized value in [0, 1]."""
    value = max(0.0, min(1.0, value))
    for index in range(len(PALETTE) - 1):
        left_pos, left_color = PALETTE[index]
        right_pos, right_color = PALETTE[index + 1]
        if value <= right_pos:
            span = max(1e-9, right_pos - left_pos)
            t = (value - left_pos) / span
            return tuple(  # type: ignore[return-value]
                int(round(a + (b - a) * t))
                for a, b in zip(left_color, right_color)
            )
    return PALETTE[-1][1]


def escape(c_real: float, c_imag: float, max_iterations: int) -> float:
    """Return the smooth iteration count, or -1 for points inside the set."""
    z_real = z_imag = 0.0
    z_real_sq = z_imag_sq = 0.0
    for iteration in range(max_iterations):
        z_imag = 2.0 * z_real * z_imag + c_imag
        z_real = z_real_sq - z_imag_sq + c_real
        z_real_sq = z_real * z_real
        z_imag_sq = z_imag * z_imag
        if z_real_sq + z_imag_sq > 4.0:
            magnitude = math.sqrt(z_real_sq + z_imag_sq)
            return iteration + 1.0 - math.log(math.log(magnitude), 2.0)
    return -1.0


def render(
    width: int,
    height: int,
    *,
    max_iterations: int = 180,
    center: tuple[float, float] = (-0.6, 0.0),
    zoom: float = 1.0,
) -> bytearray:
    """Render the set into a row-major RGB buffer."""
    if width <= 0 or height <= 0:
        raise ValueError("dimensions must be positive")
    if max_iterations <= 0:
        raise ValueError("iterations must be positive")
    if zoom <= 0:
        raise ValueError("zoom must be positive")
    span_x = 3.2 / zoom
    span_y = span_x * height / width
    x_min = center[0] - span_x / 2.0
    y_min = center[1] - span_y / 2.0
    pixels = bytearray(width * height * 3)
    denominator = math.log1p(max_iterations)
    index = 0
    for y in range(height):
        c_imag = y_min + (y + 0.5) * span_y / height
        for x in range(width):
            c_real = x_min + (x + 0.5) * span_x / width
            smooth = escape(c_real, c_imag, max_iterations)
            if smooth < 0:
                color = (3, 4, 10)
            else:
                # log scaling keeps detail in both fast and slow escape zones.
                normalized = math.log1p(max(0.0, smooth)) / denominator
                color = palette(normalized ** 0.85)
            pixels[index : index + 3] = bytes(color)
            index += 3
    return pixels


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("size must be WIDTHxHEIGHT") from exc
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise argparse.ArgumentTypeError("dimensions must be between 1 and 4096")
    return width, height


def _parse_center(value: str) -> tuple[float, float]:
    try:
        real, imag = (float(part) for part in value.split(",", 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("center must be REAL,IMAG") from exc
    return real, imag


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the Mandelbrot set.")
    parser.add_argument("--size", type=_parse_size, default=(640, 480), help="WIDTHxHEIGHT")
    parser.add_argument("--iterations", type=int, default=180)
    parser.add_argument("--center", type=_parse_center, default=(-0.6, 0.0))
    parser.add_argument("--zoom", type=float, default=1.0)
    parser.add_argument("--format", choices=("png", "ppm"), default="png")
    parser.add_argument("--output", "-o", default="mandelbrot.png")
    args = parser.parse_args(argv)
    if not 1 <= args.iterations <= 20_000:
        parser.error("iterations must be between 1 and 20000")

    width, height = args.size
    pixels = render(
        width,
        height,
        max_iterations=args.iterations,
        center=args.center,
        zoom=args.zoom,
    )
    output = Path(args.output)
    if args.format == "ppm":
        path = write_ppm(output, width, height, pixels)
    else:
        path = write_png(output, width, height, pixels)
    print(
        f"wrote {path}: {width}x{height}, {args.iterations} iterations, "
        f"zoom={args.zoom:g}, {path.stat().st_size} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
