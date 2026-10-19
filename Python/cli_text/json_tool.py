#!/usr/bin/env python3
"""Validate, format, minify and query JSON documents.

Subcommands:
    validate   parse the document and report success or the exact error
    format     pretty-print (optionally sorting keys)
    minify     remove all insignificant whitespace
    get        fetch a value by dotted path, e.g. users.0.name
    paths      list nested paths and value types for exploration

Input defaults to stdin and can be written back to a file with -o.
Exit status is 0 on success and 1 for invalid JSON or a missing path.

Usage:
    python json_tool.py validate config.json
    python json_tool.py format config.json --indent 4 --sort-keys
    python json_tool.py minify data.json -o data.min.json
    python json_tool.py get package.json dependencies
    python json_tool.py get api.json items.0.id --default missing
    python json_tool.py paths data.json --max-depth 2
    type data.json | python json_tool.py validate -
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator, Sequence

_MISSING = object()


def read_input(path: str) -> str:
    """Read JSON text from a file or stdin."""
    if path == "-":
        try:
            return sys.stdin.read()
        except UnicodeDecodeError as exc:
            raise SystemExit(f"error: stdin is not valid UTF-8 ({exc.reason})")
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def load_json(path: str) -> Any:
    """Parse JSON with a helpful error including line and column."""
    text = read_input(path)
    if not text.strip():
        raise SystemExit("error: input is empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"error: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        )


def write_output(text: str, destination: str | None) -> None:
    """Write serialized JSON to a file or stdout."""
    if destination is None or destination == "-":
        print(text)
        return
    try:
        with open(destination, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
    except OSError as exc:
        raise SystemExit(f"error: cannot write {destination}: {exc}")


def walk_paths(value: Any, prefix: str = "", depth: int = 0, max_depth: int = 4) -> Iterator[tuple[str, str]]:
    """Yield (dotted path, type name) for *value* down to *max_depth*."""
    kind = "null" if value is None else type(value).__name__
    if prefix:
        yield prefix, kind
    if depth >= max_depth:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            yield from walk_paths(child, child_path, depth + 1, max_depth)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{prefix}.{index}" if prefix else str(index)
            yield from walk_paths(child, child_path, depth + 1, max_depth)


def resolve_path(document: Any, dotted: str) -> Any:
    """Resolve a dotted path (with integer list indexes) or return _MISSING."""
    current = document
    for part in dotted.split("."):
        if part == "":
            continue
        if isinstance(current, dict):
            if part not in current:
                return _MISSING
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                return _MISSING
        else:
            return _MISSING
    return current


def add_common_io(parser: argparse.ArgumentParser) -> None:
    """Add the shared input/output arguments used by several subcommands."""
    parser.add_argument("file", nargs="?", default="-", help="JSON file, or '-' for stdin")
    parser.add_argument("-o", "--output", help="write result here instead of stdout")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, format, minify and query JSON documents.",
        epilog="All read commands accept '-' (the default) for stdin.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    validate = sub.add_parser("validate", help="check whether a document is valid JSON")
    validate.add_argument("file", nargs="?", default="-", help="JSON file, or '-' for stdin")
    validate.add_argument("-q", "--quiet", action="store_true",
                          help="print nothing; rely on the exit status")

    fmt = sub.add_parser("format", help="pretty-print JSON")
    add_common_io(fmt)
    fmt.add_argument("--indent", type=int, default=2, metavar="N",
                     help="indentation width (default: 2)")
    fmt.add_argument("--sort-keys", action="store_true",
                     help="sort object keys alphabetically")

    minify = sub.add_parser("minify", help="remove insignificant whitespace")
    add_common_io(minify)
    minify.add_argument("--sort-keys", action="store_true",
                        help="sort object keys alphabetically")

    get = sub.add_parser("get", help="read a value by dotted path")
    get.add_argument("file", help="JSON file, or '-' for stdin")
    get.add_argument("path", help="dotted path such as users.0.name")
    get.add_argument("--default", metavar="VALUE",
                     help="print VALUE instead of failing when the path is absent")
    get.add_argument("--raw", action="store_true",
                     help="print strings without JSON quotes")

    paths = sub.add_parser("paths", help="list nested paths and their types")
    paths.add_argument("file", nargs="?", default="-", help="JSON file, or '-' for stdin")
    paths.add_argument("--max-depth", type=int, default=4, metavar="N",
                       help="maximum nesting depth to show (default: 4)")

    for command in (fmt, minify):
        command.set_defaults(indent=2)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate":
        document = load_json(args.file)
        if not args.quiet:
            kind = "null" if document is None else type(document).__name__
            print(f"valid JSON ({kind})", file=sys.stderr)
        return 0

    if args.command in {"format", "minify"}:
        if not 0 <= getattr(args, "indent", 2) <= 8:
            raise SystemExit("error: --indent must be between 0 and 8")
        document = load_json(args.file)
        if args.command == "minify":
            text = json.dumps(
                document, ensure_ascii=False, sort_keys=args.sort_keys,
                separators=(",", ":"),
            )
        else:
            text = json.dumps(
                document, ensure_ascii=False, sort_keys=args.sort_keys,
                indent=args.indent,
            )
        write_output(text, args.output)
        return 0

    if args.command == "get":
        document = load_json(args.file)
        result = resolve_path(document, args.path)
        if result is _MISSING:
            if args.default is not None:
                print(args.default)
                return 0
            print(f"error: path not found: {args.path}", file=sys.stderr)
            return 1
        if isinstance(result, str) and args.raw:
            print(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "paths":
        if args.max_depth < 0:
            raise SystemExit("error: --max-depth cannot be negative")
        document = load_json(args.file)
        count = 0
        for dotted, kind in walk_paths(document, max_depth=args.max_depth):
            print(f"{dotted}  ({kind})")
            count += 1
        if count == 0:
            print("(scalar document - no nested paths)", file=sys.stderr)
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
