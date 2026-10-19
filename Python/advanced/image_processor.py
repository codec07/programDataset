"""A tiny raster image toolkit for the plain PPM format (P6 and P3).

Implements PPM decoding/encoding plus grayscale conversion, separable box
blur, Sobel edge detection, and bilinear resizing. No third-party modules
are used. A generated test image powers the ``--demo`` mode.

Usage:
    python image_processor.py --demo --output-dir demo_images
    python image_processor.py input.ppm --op blur --radius 3 -o blurred.ppm
    python image_processor.py input.ppm --op resize --size 320x240 -o small.ppm
    python image_processor.py input.ppm --op gray --ascii -o gray_p3.ppm

PPM is deliberately simple: a small ASCII header followed by either ASCII
samples (P3) or binary RGB bytes (P6).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

WHITESPACE = b" \t\r\n\v\f"


@dataclass(slots=True)
class Image:
    """A row-major 8-bit RGB image."""

    width: int
    height: int
    pixels: bytearray

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("image dimensions must be positive")
        if len(self.pixels) != self.width * self.height * 3:
            raise ValueError("pixel buffer does not match image dimensions")

    def copy(self) -> "Image":
        return Image(self.width, self.height, bytearray(self.pixels))

    def get_pixel(self, x: int, y: int) -> tuple[int, int, int]:
        index = (y * self.width + x) * 3
        return self.pixels[index], self.pixels[index + 1], self.pixels[index + 2]

    def set_pixel(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        index = (y * self.width + x) * 3
        self.pixels[index : index + 3] = bytes(rgb)


class PPMError(ValueError):
    """Raised when a PPM file is malformed."""


def _next_token(data: bytes, position: int) -> tuple[bytes, int]:
    """Read one whitespace-delimited token, skipping ``#`` comments."""
    while True:
        while position < len(data) and data[position] in WHITESPACE:
            position += 1
        if position < len(data) and data[position] == ord("#"):
            newline = data.find(b"\n", position)
            if newline < 0:
                raise PPMError("unterminated comment")
            position = newline + 1
            continue
        break
    start = position
    while position < len(data) and data[position] not in WHITESPACE:
        position += 1
    if start == position:
        raise PPMError("missing PPM header token")
    return data[start:position], position


def read_ppm(path: str | Path) -> Image:
    """Read a binary (P6) or ASCII (P3) PPM file into an :class:`Image`."""
    data = Path(path).read_bytes()
    magic, position = _next_token(data, 0)
    if magic not in (b"P6", b"P3"):
        raise PPMError(f"unsupported PPM magic {magic!r}")
    try:
        width_token, position = _next_token(data, position)
        height_token, position = _next_token(data, position)
        maxval_token, position = _next_token(data, position)
        width, height, maxval = int(width_token), int(height_token), int(maxval_token)
    except ValueError as exc:
        raise PPMError("PPM header values must be integers") from exc
    if width <= 0 or height <= 0 or not 1 <= maxval <= 255:
        raise PPMError("invalid PPM dimensions or maxval (only 8-bit PPM is supported)")

    count = width * height * 3
    pixels = bytearray(count)
    if magic == b"P3":
        for index in range(count):
            token, position = _next_token(data, position)
            try:
                value = int(token)
            except ValueError as exc:
                raise PPMError("invalid ASCII sample") from exc
            if not 0 <= value <= maxval:
                raise PPMError("ASCII sample outside maxval")
            pixels[index] = (value * 255 + maxval // 2) // maxval
    else:
        # Exactly one whitespace character separates the header from raster
        # data. Handle CRLF as one logical separator.
        if data[position : position + 2] == b"\r\n":
            position += 2
        elif position < len(data) and data[position] in WHITESPACE:
            position += 1
        else:
            raise PPMError("missing raster separator")
        raster = data[position:]
        if len(raster) < count:
            raise PPMError(f"raster is short: expected {count} bytes, got {len(raster)}")
        if maxval == 255:
            pixels[:] = raster[:count]
        else:
            for index, value in enumerate(raster[:count]):
                pixels[index] = (value * 255 + maxval // 2) // maxval
    return Image(width, height, pixels)


def write_ppm(path: str | Path, image: Image, *, ascii_mode: bool = False) -> Path:
    """Write an :class:`Image` as P6 (default) or P3 (``ascii_mode``) PPM."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = f"{'P3' if ascii_mode else 'P6'}\n{image.width} {image.height}\n255\n"
    if not ascii_mode:
        destination.write_bytes(header.encode("ascii") + bytes(image.pixels))
        return destination
    lines: list[str] = [header]
    for y in range(image.height):
        values: list[str] = []
        base = y * image.width * 3
        for x in range(image.width):
            index = base + x * 3
            values.append(f"{image.pixels[index]} {image.pixels[index + 1]} {image.pixels[index + 2]}")
        lines.append(" ".join(values))
    destination.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    return destination


def grayscale(image: Image) -> Image:
    """Convert to luminance using Rec. 601 weights."""
    output = bytearray(len(image.pixels))
    for index in range(0, len(image.pixels), 3):
        r, g, b = image.pixels[index : index + 3]
        gray = (299 * r + 587 * g + 114 * b + 500) // 1000
        output[index : index + 3] = bytes((gray, gray, gray))
    return Image(image.width, image.height, output)


def _clamp(value: int, low: int, high: int) -> int:
    return low if value < low else high if value > high else value


def box_blur(image: Image, radius: int = 2) -> Image:
    """Blur with a separable box kernel and edge clamping."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    if radius == 0:
        return image.copy()
    width, height, source = image.width, image.height, image.pixels
    horizontal = bytearray(len(source))
    for y in range(height):
        row = y * width * 3
        for x in range(width):
            totals = [0, 0, 0]
            samples = 0
            for dx in range(-radius, radius + 1):
                sx = _clamp(x + dx, 0, width - 1)
                base = row + sx * 3
                for channel in range(3):
                    totals[channel] += source[base + channel]
                samples += 1
            base = row + x * 3
            for channel in range(3):
                horizontal[base + channel] = (totals[channel] + samples // 2) // samples

    output = bytearray(len(source))
    for y in range(height):
        for x in range(width):
            totals = [0, 0, 0]
            samples = 0
            for dy in range(-radius, radius + 1):
                sy = _clamp(y + dy, 0, height - 1)
                base = (sy * width + x) * 3
                for channel in range(3):
                    totals[channel] += horizontal[base + channel]
                samples += 1
            base = (y * width + x) * 3
            for channel in range(3):
                output[base + channel] = (totals[channel] + samples // 2) // samples
    return Image(width, height, output)


def edge_detect(image: Image) -> Image:
    """Apply a Sobel operator and return a grayscale edge map."""
    gray = grayscale(image).pixels
    width, height = image.width, image.height
    output = bytearray(len(image.pixels))
    kernel_x = (-1, 0, 1, -2, 0, 2, -1, 0, 1)
    kernel_y = (-1, -2, -1, 0, 0, 0, 1, 2, 1)
    for y in range(height):
        for x in range(width):
            gx = gy = 0
            offset = 0
            for ky in (-1, 0, 1):
                sy = _clamp(y + ky, 0, height - 1)
                for kx in (-1, 0, 1):
                    sx = _clamp(x + kx, 0, width - 1)
                    value = gray[(sy * width + sx) * 3]
                    gx += value * kernel_x[offset]
                    gy += value * kernel_y[offset]
                    offset += 1
            magnitude = min(255, int(math.hypot(gx, gy)))
            base = (y * width + x) * 3
            output[base : base + 3] = bytes((magnitude, magnitude, magnitude))
    return Image(width, height, output)


def resize(image: Image, width: int, height: int) -> Image:
    """Resize using bilinear interpolation."""
    if width <= 0 or height <= 0:
        raise ValueError("target dimensions must be positive")
    output = bytearray(width * height * 3)
    x_scale = image.width / width
    y_scale = image.height / height
    for y in range(height):
        sy = (y + 0.5) * y_scale - 0.5
        y0 = _clamp(math.floor(sy), 0, image.height - 1)
        y1 = _clamp(y0 + 1, 0, image.height - 1)
        wy = sy - math.floor(sy)
        for x in range(width):
            sx = (x + 0.5) * x_scale - 0.5
            x0 = _clamp(math.floor(sx), 0, image.width - 1)
            x1 = _clamp(x0 + 1, 0, image.width - 1)
            wx = sx - math.floor(sx)
            target = (y * width + x) * 3
            for channel in range(3):
                top = (
                    image.pixels[(y0 * image.width + x0) * 3 + channel] * (1 - wx)
                    + image.pixels[(y0 * image.width + x1) * 3 + channel] * wx
                )
                bottom = (
                    image.pixels[(y1 * image.width + x0) * 3 + channel] * (1 - wx)
                    + image.pixels[(y1 * image.width + x1) * 3 + channel] * wx
                )
                value = top * (1 - wy) + bottom * wy
                output[target + channel] = _clamp(int(value + 0.5), 0, 255)
    return Image(width, height, output)


def generate_test_image(width: int = 220, height: int = 150) -> Image:
    """Create a colorful test card with gradients, circles, and a grid."""
    pixels = bytearray(width * height * 3)
    center_x, center_y = width * 0.62, height * 0.52
    radius = min(width, height) * 0.28
    index = 0
    for y in range(height):
        for x in range(width):
            r = int(255 * x / max(1, width - 1))
            g = int(255 * y / max(1, height - 1))
            b = int(80 + 120 * math.sin((x + y) / 28.0))
            distance = math.hypot(x - center_x, y - center_y)
            if distance < radius:
                glow = 1.0 - distance / radius
                r = int(40 + 215 * glow)
                g = int(230 - 160 * glow)
                b = int(220 - 80 * glow)
            if (x // 24 + y // 24) % 2 == 0 and (x < width * 0.28 or y > height * 0.8):
                r, g, b = 245, 205, 40
            if x < 3 or y < 3 or x >= width - 3 or y >= height - 3:
                r = g = b = 245
            pixels[index : index + 3] = bytes(
                (_clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))
            )
            index += 3
    return Image(width, height, pixels)


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("size must be WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")
    return width, height


def _save_operation(image: Image, operation: str, output: Path, args: argparse.Namespace) -> None:
    operations = {
        "gray": lambda: grayscale(image),
        "blur": lambda: box_blur(image, args.radius),
        "edges": lambda: edge_detect(image),
        "resize": lambda: resize(image, *args.size),
    }
    result = operations[operation]()
    write_ppm(output, result, ascii_mode=args.ascii)
    print(
        f"wrote {output} ({result.width}x{result.height}, op={operation}, "
        f"format={'P3' if args.ascii else 'P6'})"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process PPM images using pure Python.")
    parser.add_argument("input", nargs="?", help="input P6/P3 PPM image")
    parser.add_argument("--demo", action="store_true", help="generate a test image and all operations")
    parser.add_argument("--output-dir", default="image_demo", help="directory for --demo output")
    parser.add_argument("--op", choices=("gray", "blur", "edges", "resize"), default="gray")
    parser.add_argument("--output", "-o", help="output PPM path")
    parser.add_argument("--radius", type=int, default=2, help="blur radius")
    parser.add_argument("--size", type=_parse_size, default=(110, 75), help="resize WIDTHxHEIGHT")
    parser.add_argument("--ascii", action="store_true", help="write P3 instead of P6")
    args = parser.parse_args(argv)

    if args.demo:
        directory = Path(args.output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        source = generate_test_image()
        source_path = write_ppm(directory / "image_demo.ppm", source, ascii_mode=args.ascii)
        print(f"wrote {source_path} ({source.width}x{source.height})")
        for name, operation in (
            ("gray", grayscale(source)),
            ("blur", box_blur(source, max(1, args.radius))),
            ("edges", edge_detect(source)),
            ("resize", resize(source, *args.size)),
        ):
            path = write_ppm(
                directory / f"image_demo_{name}.ppm", operation, ascii_mode=args.ascii
            )
            print(f"wrote {path} ({operation.width}x{operation.height})")
        return 0

    if not args.input:
        parser.error("provide an input PPM file or use --demo")
    try:
        source_image = read_ppm(args.input)
    except (OSError, PPMError) as exc:
        parser.error(str(exc))
    output = Path(args.output) if args.output else Path(args.input).with_name(
        f"{Path(args.input).stem}_{args.op}.ppm"
    )
    _save_operation(source_image, args.op, output, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
