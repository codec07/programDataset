#!/usr/bin/env python3
"""Encode and decode Base64 for files, stdin or literal text.

Input defaults to a file path; use `--text` to encode a literal string,
or "-" to read raw bytes from stdin. Decoding to stdout is only allowed
when the result is valid UTF-8 - otherwise specify an output file.

Usage:
    python base64_tool.py encode notes.txt
    python base64_tool.py encode --text "hello world"
    python base64_tool.py encode photo.png -o photo.b64 --wrap 76
    python base64_tool.py decode photo.b64 -o restored.png
    python base64_tool.py encode --url-safe --text "a+b/c?"
    type data.bin | python base64_tool.py encode - -o data.b64
"""

from __future__ import annotations

import argparse
import base64
import binascii
import sys
from pathlib import Path
from typing import Sequence


def read_input(source: str) -> bytes:
    """Read raw bytes from a file or stdin."""
    if source == "-":
        return sys.stdin.buffer.read()
    try:
        return Path(source).read_bytes()
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {source}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {source}")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {source}: {exc}")


def encode_bytes(data: bytes, url_safe: bool) -> bytes:
    """Base64-encode *data*, choosing the URL-safe alphabet if requested."""
    encoder = base64.urlsafe_b64encode if url_safe else base64.b64encode
    return encoder(data)


def decode_bytes(data: bytes, url_safe: bool, ignore_garbage: bool) -> bytes:
    """Decode Base64 input with strict validation unless garbage is ignored."""
    cleaned = b"".join(data.split())
    if ignore_garbage:
        # Strip characters outside both standard and URL-safe alphabets.
        alphabet = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=_-")
        cleaned = bytes(byte for byte in cleaned if byte in alphabet)
    decoder = base64.b64decode
    try:
        if url_safe:
            return decoder(cleaned, altchars=b"-_", validate=True)
        return decoder(cleaned, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SystemExit(f"error: invalid Base64 input: {exc}")


def wrap_text(text: str, width: int) -> str:
    """Wrap encoded text into fixed-width lines."""
    if width <= 0:
        return text
    return "\n".join(text[i : i + width] for i in range(0, len(text), width))


def write_output(data: bytes, destination: str | None, *, text_ok: bool) -> None:
    """Write bytes to a file, or print text to stdout when safe."""
    if destination is None or destination == "-":
        if text_ok:
            text = data.decode("utf-8")
            print(text, end="" if text.endswith("\n") else "\n")
            return
        raise SystemExit(
            "error: decoded data is not valid UTF-8; use -o FILE to write raw bytes"
        )
    try:
        with open(destination, "wb") as handle:
            handle.write(data)
    except OSError as exc:
        raise SystemExit(f"error: cannot write {destination}: {exc}")
    print(f"wrote {len(data)} byte(s) to {destination}", file=sys.stderr)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encode or decode Base64 data.",
        epilog="Use '-' as the input path to read stdin.",
    )
    parser.add_argument("mode", choices=("encode", "decode"), help="operation to perform")
    parser.add_argument("input", help="input file, or '-' for stdin")
    parser.add_argument("-o", "--output", help="output file (default: stdout when possible)")
    parser.add_argument("--text", action="store_true",
                        help="treat INPUT as literal UTF-8 text instead of a path")
    parser.add_argument("--url-safe", action="store_true",
                        help="use the URL-safe Base64 alphabet")
    parser.add_argument("--wrap", type=int, default=0, metavar="N",
                        help="wrap encoded output at N columns (default: no wrapping)")
    parser.add_argument("--ignore-garbage", action="store_true",
                        help="skip whitespace and unknown characters while decoding")
    args = parser.parse_args(argv)

    if args.text and args.mode == "decode":
        parser.error("--text only applies to encoding")
    if args.text and args.input == "-":
        parser.error("--text cannot be combined with stdin input")
    if not 0 <= args.wrap <= 200:
        parser.error("--wrap must be between 0 and 200")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.mode == "encode":
        raw = args.input.encode("utf-8") if args.text else read_input(args.input)
        encoded = encode_bytes(raw, args.url_safe)
        text = encoded.decode("ascii")
        text = wrap_text(text, args.wrap)
        write_output(text.encode("ascii"), args.output, text_ok=True)
        if args.output and args.output != "-":
            print(f"encoded {len(raw)} byte(s)", file=sys.stderr)
        return 0

    data = read_input(args.input)
    decoded = decode_bytes(data, args.url_safe, args.ignore_garbage)
    # write_output validates UTF-8 when stdout is requested and no -o is given.
    write_output(decoded, args.output, text_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
