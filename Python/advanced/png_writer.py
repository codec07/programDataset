"""Write valid 8-bit RGB PNG files using only the standard library.

The encoder builds the PNG container from scratch: the 8-byte signature,
IHDR/IDAT/IEND chunks, big-endian lengths, and CRC-32 checksums. Pixel rows
use filter type 0 (None), which keeps the encoder small while remaining
fully spec-compliant.

Usage:
    python png_writer.py --output gradient.png --width 320 --height 200
    python png_writer.py --pattern checker --output checker.png
    python png_writer.py --pattern plasma --width 256 --height 256

The module can also be imported::

    from png_writer import write_png
    write_png("tiny.png", 2, 1, bytes([255, 0, 0, 0, 255, 0]))
"""

from __future__ import annotations

import argparse
import math
import struct
import zlib
from pathlib import Path
from typing import Callable, Sequence

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RGB = tuple[int, int, int]


def _chunk(tag: bytes, payload: bytes) -> bytes:
    """Return one PNG chunk: length, type, data, and CRC-32."""
    if len(tag) != 4:
        raise ValueError("PNG chunk tags must be exactly four bytes")
    crc = zlib.crc32(tag)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def write_png(
    path: str | Path,
    width: int,
    height: int,
    rgb: bytes | bytearray,
    *,
    compress_level: int = 9,
) -> Path:
    """Encode ``rgb`` (width * height * 3 bytes) as an 8-bit RGB PNG.

    Args:
        path: Destination file.
        width: Image width in pixels, greater than zero.
        height: Image height in pixels, greater than zero.
        rgb: Row-major RGB triples.
        compress_level: zlib compression level from 0 to 9.

    Raises:
        ValueError: If dimensions or the pixel buffer are invalid.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if not 0 <= compress_level <= 9:
        raise ValueError("compress_level must be between 0 and 9")
    expected = width * height * 3
    if len(rgb) != expected:
        raise ValueError(f"expected {expected} RGB bytes, received {len(rgb)}")

    stride = width * 3
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)  # PNG filter type 0: None.
        start = y * stride
        filtered.extend(rgb[start : start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(filtered), compress_level))
        + _chunk(b"IEND", b"")
    )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(png)
    return destination


def _gradient(x: int, y: int, width: int, height: int) -> RGB:
    r = int(255 * x / max(1, width - 1))
    g = int(255 * y / max(1, height - 1))
    b = int(110 + 100 * math.sin((x + y) / 24.0))
    return r, g, max(0, min(255, b))


def _checker(x: int, y: int, width: int, height: int) -> RGB:
    size = max(8, min(width, height) // 10)
    bright = ((x // size) + (y // size)) % 2 == 0
    base = 235 if bright else 30
    return base, (base * 3) % 256, 255 - base


def _plasma(x: int, y: int, width: int, height: int) -> RGB:
    a = math.sin(x / 11.0) + math.sin(y / 13.0)
    b = math.sin((x + y) / 17.0) + math.cos(math.hypot(x - width / 2, y - height / 2) / 12.0)
    c = math.sin(math.hypot(x, y) / 9.0)
    return (
        int(127 + 120 * a / 2),
        int(127 + 120 * b / 2),
        int(127 + 120 * c),
    )


def make_image(width: int, height: int, pattern: str = "gradient") -> bytearray:
    """Render a generated test pattern into an RGB byte buffer."""
    shaders: dict[str, Callable[[int, int, int, int], RGB]] = {
        "gradient": _gradient,
        "checker": _checker,
        "plasma": _plasma,
    }
    try:
        shader = shaders[pattern]
    except KeyError as exc:
        raise ValueError(f"unknown pattern {pattern!r}; choose from {sorted(shaders)}") from exc

    pixels = bytearray(width * height * 3)
    index = 0
    for y in range(height):
        for x in range(width):
            r, g, b = shader(x, y, width, height)
            pixels[index] = max(0, min(255, r))
            pixels[index + 1] = max(0, min(255, g))
            pixels[index + 2] = max(0, min(255, b))
            index += 3
    return pixels


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("size must look like WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")
    return width, height


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a dependency-free RGB PNG.")
    parser.add_argument("--output", "-o", default="png_demo.png", help="output PNG path")
    parser.add_argument("--size", type=_parse_size, default=(320, 200), help="WIDTHxHEIGHT")
    parser.add_argument(
        "--pattern",
        choices=("gradient", "checker", "plasma"),
        default="gradient",
        help="generated test pattern",
    )
    parser.add_argument("--compress-level", type=int, default=9, choices=range(0, 10))
    args = parser.parse_args(argv)

    width, height = args.size
    pixels = make_image(width, height, args.pattern)
    destination = write_png(
        args.output, width, height, pixels, compress_level=args.compress_level
    )
    print(
        f"wrote {destination} ({width}x{height}, {destination.stat().st_size} bytes, "
        f"pattern={args.pattern})"
    )
    print("signature:", " ".join(f"{byte:02x}" for byte in PNG_SIGNATURE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
