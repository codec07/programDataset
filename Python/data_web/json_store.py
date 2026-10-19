"""A tiny persistent JSON key/value store with dotted keys and atomic writes.

Data is kept in a single JSON object.  Every mutation rewrites the file
atomically (temp file + os.replace) so a crash cannot leave a half-written
document behind.  Dotted keys address nested objects, e.g. ``server.port``.

Usage:
    python json_store.py --file store.json set name "Ada Lovelace"
    python json_store.py --file store.json set server.port 8080 --json
    python json_store.py --file store.json get server.port
    python json_store.py --file store.json keys
    python json_store.py --file store.json delete server.port
    python json_store.py --demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


class JsonStore:
    """Load, query and atomically persist a JSON object on disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {}
        if path.exists():
            self.data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{self.path} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{self.path} must contain a JSON object at the top level")
        return data

    def save(self) -> None:
        """Write atomically: serialise to a temp file in the same directory."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    @staticmethod
    def _parts(key: str) -> list[str]:
        parts = [p for p in key.split(".") if p]
        if not parts:
            raise ValueError("key must not be empty")
        return parts

    def get(self, key: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in self._parts(key):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        parts = self._parts(key)
        node = self.data
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = value

    def delete(self, key: str) -> bool:
        parts = self._parts(key)
        node = self.data
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                return False
            node = child
        return node.pop(parts[-1], None) is not None

    def flatten(self, prefix: str = "") -> list[str]:
        """Return every leaf key as a dotted path."""
        out: list[str] = []

        def walk(node: Any, path: str) -> None:
            if isinstance(node, dict) and node:
                for k, v in node.items():
                    walk(v, f"{path}.{k}" if path else k)
            else:
                out.append(path)

        walk(self.data, prefix)
        return sorted(out)


def parse_value(raw: str, as_json: bool) -> Any:
    if as_json:
        return json.loads(raw)
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "store.json"
        store = JsonStore(path)
        store.set("app.name", "demo")
        store.set("app.version", 3)
        store.set("app.features", ["a", "b"])
        store.save()

        reloaded = JsonStore(path)
        print("reloaded app.name   :", reloaded.get("app.name"))
        print("reloaded app.version:", reloaded.get("app.version"))
        print("missing key default :", reloaded.get("nope", "fallback"))
        print("leaf keys           :", ", ".join(reloaded.flatten()))
        reloaded.delete("app.version")
        reloaded.save()
        print("after delete        :", ", ".join(JsonStore(path).flatten()))
    return 0


def main(argv: list[str] | None = None) -> int:
    # Shared options use SUPPRESS defaults so a subparser cannot reset them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", type=Path, default=argparse.SUPPRESS,
                        help="store path")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="parse values with JSON (allows lists/objects)")

    p = argparse.ArgumentParser(description="Persistent JSON key/value store.",
                                parents=[common])
    p.add_argument("--demo", action="store_true", help="run an offline demonstration")
    sub = p.add_subparsers(dest="command")

    g = sub.add_parser("get", help="print a value", parents=[common])
    g.add_argument("key")

    s = sub.add_parser("set", help="create or replace a value", parents=[common])
    s.add_argument("key")
    s.add_argument("value")

    d = sub.add_parser("delete", help="remove a key", parents=[common])
    d.add_argument("key")

    sub.add_parser("keys", help="list every leaf key", parents=[common])
    sub.add_parser("dump", help="print the whole store", parents=[common])

    args = p.parse_args(argv, argparse.Namespace(file=Path("store.json"), json=False))
    if args.demo:
        return demo()
    if not args.command:
        p.print_help()
        return 0

    try:
        store = JsonStore(args.file)
        if args.command == "get":
            missing = object()
            value = store.get(args.key, missing)
            if value is missing:
                print(f"error: key not found: {args.key}", file=sys.stderr)
                return 1
            print(json.dumps(value, indent=2, ensure_ascii=False)
                  if isinstance(value, (dict, list)) else value)
        elif args.command == "set":
            store.set(args.key, parse_value(args.value, args.json))
            store.save()
            print(f"set {args.key}")
        elif args.command == "delete":
            if store.delete(args.key):
                store.save()
                print(f"deleted {args.key}")
            else:
                print(f"error: key not found: {args.key}", file=sys.stderr)
                return 1
        elif args.command == "keys":
            for key in store.flatten():
                print(key)
        elif args.command == "dump":
            print(json.dumps(store.data, indent=2, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
