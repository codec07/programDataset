#!/usr/bin/env python3
"""Read and edit values in an INI configuration file.

Subcommands: list, get, set, delete and delete-section. Writes are atomic
and a timestamped .bak copy is made first unless --no-backup is used.
--dry-run shows the exact diff without touching the file.

Note: the file is rewritten by configparser, so comments and custom
formatting are not preserved on a successful write. The tool warns about
this before changing anything.

Usage:
    python ini_config_editor.py --file app.ini list
    python ini_config_editor.py --file app.ini get database host
    python ini_config_editor.py --file app.ini set database port 5433 --create
    python ini_config_editor.py --file app.ini set app debug true --dry-run
    python ini_config_editor.py --file app.ini delete app debug
    python ini_config_editor.py --file app.ini delete-section old --yes
"""

from __future__ import annotations

import argparse
import configparser
import difflib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence

KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def read_config(path: Path) -> tuple[configparser.ConfigParser, str]:
    """Load an INI file and return the parser plus the original text."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid UTF-8 ({exc.reason})")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # preserve key case
    try:
        parser.read_string(text, source=str(path))
    except configparser.Error as exc:
        raise SystemExit(f"error: invalid INI file: {exc}")
    return parser, text


def serialise(parser: configparser.ConfigParser) -> str:
    """Render the parser back to INI text."""
    from io import StringIO

    buffer = StringIO()
    parser.write(buffer)
    return buffer.getvalue()


def backup_file(path: Path) -> Path:
    """Copy the current file to a timestamped .bak sibling."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.{stamp}-{counter}.bak")
        counter += 1
    try:
        shutil.copy2(path, backup)
    except OSError as exc:
        raise SystemExit(f"error: cannot create backup {backup}: {exc}")
    return backup


def atomic_write(path: Path, text: str) -> None:
    """Write text through a temporary file and replace the original."""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(text)
            temp_name = handle.name
        os.replace(temp_name, path)
    except OSError as exc:
        raise SystemExit(f"error: cannot write {path}: {exc}")


def save_config(path: Path, parser: configparser.ConfigParser,
                original: str, args: argparse.Namespace,
                action: str) -> None:
    """Diff, back up if requested, and write the updated configuration."""
    updated = serialise(parser)

    if args.dry_run:
        diff = difflib.unified_diff(
            original.splitlines(), updated.splitlines(),
            fromfile=f"{path} (current)", tofile=f"{path} ({action})", lineterm="",
        )
        print("\n".join(diff) or "No change.")
        print("[dry-run] file not written", file=sys.stderr)
        return

    backup = None if args.no_backup else backup_file(path)
    atomic_write(path, updated)
    if backup:
        print(f"backup: {backup}", file=sys.stderr)
    print(f"{action}: {path}")


def require_section(parser: configparser.ConfigParser, section: str) -> None:
    """Exit with a helpful message when a section is absent."""
    if not parser.has_section(section):
        available = ", ".join(parser.sections()) or "(none)"
        raise SystemExit(f"error: no section '{section}' (available: {available})")


def get_value(parser: configparser.ConfigParser, section: str, key: str) -> str:
    """Return a value or exit with a helpful message."""
    require_section(parser, section)
    if not parser.has_option(section, key):
        keys = ", ".join(parser.options(section)) or "(none)"
        raise SystemExit(f"error: no key '{key}' in [{section}] (available: {keys})")
    return parser.get(section, key)


def cmd_list(parser: configparser.ConfigParser, args: argparse.Namespace) -> int:
    if args.json:
        payload = {section: dict(parser.items(section)) for section in parser.sections()}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not parser.sections():
        print("(no sections)")
        return 0
    for section in parser.sections():
        print(f"[{section}]")
        for key, value in parser.items(section):
            print(f"  {key} = {value}")
    return 0


def cmd_get(parser: configparser.ConfigParser, args: argparse.Namespace) -> int:
    print(get_value(parser, args.section, args.key))
    return 0


def cmd_set(path: Path, parser: configparser.ConfigParser,
            original: str, args: argparse.Namespace) -> int:
    if not KEY_RE.match(args.key):
        print(f"error: invalid key name: {args.key}", file=sys.stderr)
        return 1
    if "\n" in args.value or "\r" in args.value:
        print("error: values must be a single line", file=sys.stderr)
        return 1
    if not parser.has_section(args.section):
        if not args.create:
            require_section(parser, args.section)
        parser.add_section(args.section)
        print(f"created section [{args.section}]")
    old = parser.get(args.section, args.key, fallback=None)
    parser.set(args.section, args.key, args.value)
    if old == args.value:
        print(f"no change: [{args.section}] {args.key} is already {args.value!r}")
        return 0
    save_config(path, parser, original, args, f"set [{args.section}] {args.key}")
    return 0


def cmd_delete(path: Path, parser: configparser.ConfigParser,
               original: str, args: argparse.Namespace) -> int:
    get_value(parser, args.section, args.key)
    parser.remove_option(args.section, args.key)
    save_config(path, parser, original, args,
                f"delete [{args.section}] {args.key}")
    return 0


def cmd_delete_section(path: Path, parser: configparser.ConfigParser,
                       original: str, args: argparse.Namespace) -> int:
    require_section(parser, args.section)
    keys = parser.options(args.section)
    if keys and not args.yes and not args.dry_run:
        print(
            f"error: section [{args.section}] still has {len(keys)} key(s); "
            "use --yes to delete it",
            file=sys.stderr,
        )
        return 1
    parser.remove_section(args.section)
    save_config(path, parser, original, args, f"delete section [{args.section}]")
    return 0


def add_shared_options(subparser: argparse.ArgumentParser) -> None:
    """Allow the global options after the subcommand as well as before it."""
    subparser.add_argument("--file", default=argparse.SUPPRESS, metavar="PATH",
                           help="INI file to edit (default: config.ini)")
    subparser.add_argument("--dry-run", action="store_true",
                           default=argparse.SUPPRESS,
                           help="show a diff without writing")
    subparser.add_argument("--no-backup", action="store_true",
                           default=argparse.SUPPRESS,
                           help="do not create a .bak copy before writing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read and edit INI configuration files.",
        epilog="Comments are not preserved when a file is rewritten.",
    )
    parser.add_argument("--file", default="config.ini", metavar="PATH",
                        help="INI file to edit (default: config.ini)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show a diff without writing")
    parser.add_argument("--no-backup", action="store_true",
                        help="do not create a .bak copy before writing")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    listing = sub.add_parser("list", help="show all sections and keys")
    listing.add_argument("--json", action="store_true")
    add_shared_options(listing)
    listing.set_defaults(func=cmd_list)

    get = sub.add_parser("get", help="print one value")
    get.add_argument("section")
    get.add_argument("key")
    add_shared_options(get)
    get.set_defaults(func=cmd_get)

    set_cmd = sub.add_parser("set", help="set one value")
    set_cmd.add_argument("section")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value")
    set_cmd.add_argument("--create", action="store_true",
                         help="create the section if it does not exist")
    add_shared_options(set_cmd)
    set_cmd.set_defaults(func=cmd_set, mutating=True)

    delete = sub.add_parser("delete", help="remove one key")
    delete.add_argument("section")
    delete.add_argument("key")
    add_shared_options(delete)
    delete.set_defaults(func=cmd_delete, mutating=True)

    delete_section = sub.add_parser("delete-section", help="remove a whole section")
    delete_section.add_argument("section")
    delete_section.add_argument("--yes", action="store_true",
                                help="confirm deleting a non-empty section")
    add_shared_options(delete_section)
    delete_section.set_defaults(func=cmd_delete_section, mutating=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file)
    parser, original = read_config(path)
    if getattr(args, "mutating", False):
        return int(args.func(path, parser, original, args))
    return int(args.func(parser, args))


if __name__ == "__main__":
    sys.exit(main())
