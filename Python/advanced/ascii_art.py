"""Convert PPM or PNG images into text art, with a procedural demo image.

Includes a small PNG decoder (8-bit grayscale, RGB, grayscale+alpha, and
RGBA, non-interlaced) and a PPM reader, so no image libraries are needed.
The demo synthesizes a landscape and prints it; it can also save the source
image as PPM for inspection.

Usage:
    python ascii_art.py --demo --width 90
    python ascii_art.py photo.png --width 100 --invert
    python ascii_art.py scan.ppm -w 72 -o scan.txt
    python ascii_art.py --demo --save-demo demo.ppm
"""

from __future__ import annotations

import argparse
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DEFAULT_CHARSET = " .:-=+*#%@"


class ImageFormatError(ValueError):
    """Raised for malformed or unsupported image files."""


@dataclass(slots=True)
class Raster:
    width: int
    height: int
    pixels: bytearray  # Row-major RGB triples.

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("raster dimensions must be positive")
        if len(self.pixels) != self.width * self.height * 3:
            raise ValueError("pixel buffer size mismatch")


def _paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    pa, pb, pc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: str | Path) -> Raster:
    """Decode a non-interlaced 8-bit PNG into RGB."""
    blob = Path(path).read_bytes()
    if not blob.startswith(PNG_SIGNATURE):
        raise ImageFormatError("not a PNG file")
    position = len(PNG_SIGNATURE)
    header: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    while position + 12 <= len(blob):
        length = struct.unpack(">I", blob[position : position + 4])[0]
        tag = blob[position + 4 : position + 8]
        payload = blob[position + 8 : position + 8 + length]
        stored_crc = struct.unpack(
            ">I", blob[position + 8 + length : position + 12 + length]
        )[0]
        if len(payload) != length:
            raise ImageFormatError("truncated PNG chunk")
        if zlib.crc32(tag + payload) & 0xFFFFFFFF != stored_crc:
            raise ImageFormatError(f"CRC mismatch in {tag!r} chunk")
        position += 12 + length
        if tag == b"IHDR":
            if length != 13:
                raise ImageFormatError("invalid IHDR length")
            header = struct.unpack(">IIBBBBB", payload)
        elif tag == b"IDAT":
            compressed.extend(payload)
        elif tag == b"IEND":
            break
    if header is None:
        raise ImageFormatError("PNG has no IHDR chunk")
    width, height, bit_depth, color_type, compression, filter_method, interlace = header
    if bit_depth != 8 or compression != 0 or filter_method != 0:
        raise ImageFormatError("only 8-bit, deflate-filtered PNGs are supported")
    if interlace != 0:
        raise ImageFormatError("interlaced PNGs are not supported")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ImageFormatError(f"unsupported PNG color type {color_type}")
    if not compressed:
        raise ImageFormatError("PNG contains no image data")

    raw = zlib.decompress(bytes(compressed))
    stride = width * channels
    if len(raw) < (stride + 1) * height:
        raise ImageFormatError("PNG image data is truncated")
    previous = bytearray(stride)
    rows: list[bytearray] = []
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = raw[offset : offset + stride]
        offset += stride
        recon = bytearray(stride)
        for index, value in enumerate(scan):
            left = recon[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = _paeth(left, above, upper_left)
            else:
                raise ImageFormatError(f"invalid PNG filter {filter_type}")
            recon[index] = (value + predictor) & 0xFF
        rows.append(recon)
        previous = recon

    pixels = bytearray(width * height * 3)
    target = 0
    for row in rows:
        if color_type == 2:
            pixels[target : target + width * 3] = row
            target += width * 3
        else:
            for x in range(width):
                if color_type == 0:
                    gray = row[x]
                    rgb = (gray, gray, gray)
                elif color_type == 4:
                    gray = row[x * 2]
                    rgb = (gray, gray, gray)
                elif color_type == 6:
                    base = x * 4
                    rgb = (row[base], row[base + 1], row[base + 2])
                else:  # color_type == 2 handled above; keeps type checkers happy.
                    base = x * 3
                    rgb = (row[base], row[base + 1], row[base + 2])
                pixels[target : target + 3] = bytes(rgb)
                target += 3
    return Raster(width, height, pixels)


def _next_ppm_token(data: bytes, position: int) -> tuple[bytes, int]:
    while True:
        while position < len(data) and data[position] in b" \t\r\n\v\f":
            position += 1
        if position < len(data) and data[position] == ord("#"):
            newline = data.find(b"\n", position)
            if newline < 0:
                raise ImageFormatError("unterminated PPM comment")
            position = newline + 1
            continue
        break
    start = position
    while position < len(data) and data[position] not in b" \t\r\n\v\f":
        position += 1
    if start == position:
        raise ImageFormatError("missing PPM token")
    return data[start:position], position


def read_ppm(path: str | Path) -> Raster:
    """Read an 8-bit P3/P6 PPM image."""
    data = Path(path).read_bytes()
    magic, position = _next_ppm_token(data, 0)
    if magic not in (b"P3", b"P6"):
        raise ImageFormatError("expected a P3 or P6 PPM file")
    try:
        width_token, position = _next_ppm_token(data, position)
        height_token, position = _next_ppm_token(data, position)
        maxval_token, position = _next_ppm_token(data, position)
        width, height, maxval = int(width_token), int(height_token), int(maxval_token)
    except ValueError as exc:
        raise ImageFormatError("invalid PPM header") from exc
    if not (0 < width and 0 < height and 1 <= maxval <= 255):
        raise ImageFormatError("invalid PPM size or maxval")
    count = width * height * 3
    pixels = bytearray(count)
    if magic == b"P6":
        if data[position : position + 2] == b"\r\n":
            position += 2
        elif position < len(data) and data[position] in b" \t\r\n\v\f":
            position += 1
        raster = data[position : position + count]
        if len(raster) != count:
            raise ImageFormatError("truncated PPM raster")
        if maxval == 255:
            pixels[:] = raster
        else:
            for index, value in enumerate(raster):
                pixels[index] = (value * 255 + maxval // 2) // maxval
    else:
        for index in range(count):
            token, position = _next_ppm_token(data, position)
            value = int(token)
            if not 0 <= value <= maxval:
                raise ImageFormatError("PPM sample out of range")
            pixels[index] = (value * 255 + maxval // 2) // maxval
    return Raster(width, height, pixels)


def load_image(path: str | Path) -> Raster:
    """Load a PNG or PPM image based on its signature or extension."""
    source = Path(path)
    with source.open("rb") as handle:
        signature = handle.read(8)
    if signature == PNG_SIGNATURE:
        return read_png(source)
    return read_ppm(source)


def _average_cell(
    raster: Raster, x0: int, y0: int, x1: int, y1: int, invert: bool
) -> float:
    total = 0.0
    samples = 0
    for y in range(y0, y1):
        base = y * raster.width * 3
        for x in range(x0, x1):
            index = base + x * 3
            r, g, b = raster.pixels[index : index + 3]
            total += 0.299 * r + 0.587 * g + 0.114 * b
            samples += 1
    value = total / max(1, samples)
    return 255.0 - value if invert else value


def to_ascii(
    raster: Raster,
    width: int = 80,
    *,
    charset: str = DEFAULT_CHARSET,
    aspect: float = 0.5,
    invert: bool = False,
) -> str:
    """Resize by cell averaging and map luminance to characters."""
    if width <= 0:
        raise ValueError("ASCII width must be positive")
    if not charset:
        raise ValueError("charset must not be empty")
    target_height = max(
        1, int(round(raster.height * (width / raster.width) * max(0.1, aspect)))
    )
    lines: list[str] = []
    levels = len(charset) - 1
    for row in range(target_height):
        y0 = row * raster.height // target_height
        y1 = max(y0 + 1, (row + 1) * raster.height // target_height)
        characters: list[str] = []
        for column in range(width):
            x0 = column * raster.width // width
            x1 = max(x0 + 1, (column + 1) * raster.width // width)
            luminance = _average_cell(raster, x0, y0, x1, y1, invert)
            index = int(luminance / 255.0 * levels + 0.5)
            characters.append(charset[max(0, min(levels, index))])
        lines.append("".join(characters).rstrip())
    return "\n".join(lines)


def generate_demo_image(width: int = 360, height: int = 220) -> Raster:
    """Generate a simple sunset landscape entirely in memory."""
    pixels = bytearray(width * height * 3)
    horizon = int(height * 0.62)
    for y in range(height):
        for x in range(width):
            if y < horizon:
                sky = y / horizon
                r = int(35 + 210 * sky)
                g = int(45 + 150 * sky * sky)
                b = int(95 + 80 * (1 - sky))
            else:
                depth = (y - horizon) / max(1, height - horizon)
                r = int(20 + 40 * (1 - depth))
                g = int(35 + 55 * (1 - depth))
                b = int(60 + 70 * (1 - depth))
            sun_x, sun_y = width * 0.7, horizon * 0.52
            distance = math.hypot(x - sun_x, y - sun_y)
            if distance < height * 0.13:
                r, g, b = 255, int(190 + 50 * (1 - distance / (height * 0.13))), 90
            mountain = horizon - int(
                28 * math.sin(x / 31.0) + 15 * math.sin(x / 11.0 + 1.4) + 35
            )
            if horizon - 20 < y and y > mountain:
                shade = 25 + int(20 * math.sin(x / 7.0))
                r, g, b = shade, shade + 15, shade + 28
            index = (y * width + x) * 3
            pixels[index : index + 3] = bytes(
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            )
    return Raster(width, height, pixels)


def write_ppm(path: str | Path, raster: Raster) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = f"P6\n{raster.width} {raster.height}\n255\n".encode("ascii")
    destination.write_bytes(header + bytes(raster.pixels))
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render PPM/PNG images as ASCII art.")
    parser.add_argument("input", nargs="?", help="input image (.ppm or .png)")
    parser.add_argument("--demo", action="store_true", help="use the procedural landscape")
    parser.add_argument("--save-demo", metavar="PPM", help="save the demo image as PPM")
    parser.add_argument("--width", "-w", type=int, default=80, help="output columns")
    parser.add_argument("--charset", default=DEFAULT_CHARSET)
    parser.add_argument("--aspect", type=float, default=0.5, help="character cell height ratio")
    parser.add_argument("--invert", action="store_true", help="use dark characters on light")
    parser.add_argument("--output", "-o", help="also write the text art to this file")
    args = parser.parse_args(argv)

    if args.demo:
        raster = generate_demo_image()
        if args.save_demo:
            print(f"saved demo image to {write_ppm(args.save_demo, raster)}")
    elif args.input:
        try:
            raster = load_image(args.input)
        except (OSError, ImageFormatError, zlib.error) as exc:
            parser.error(str(exc))
    else:
        parser.error("provide an image path or use --demo")

    art = to_ascii(
        raster,
        args.width,
        charset=args.charset,
        aspect=args.aspect,
        invert=args.invert,
    )
    print(art)
    if args.output:
        Path(args.output).write_text(art + "\n", encoding="utf-8")
        print(f"\n[ascii art written to {args.output}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
