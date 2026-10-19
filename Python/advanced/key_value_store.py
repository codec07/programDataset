"""A durable string-keyed store backed by an append-only JSONL log.

Every mutation is appended as a small JSON record; deletions write tombstones.
``compact()`` rewrites live data to a sibling temporary file and atomically
replaces the old log with ``os.replace``. The in-memory index is rebuilt by
replaying the log at startup.

Usage:
    python key_value_store.py --demo
    python key_value_store.py --db data.jsonl set user '{"name": "Ada"}'
    python key_value_store.py --db data.jsonl get user
    python key_value_store.py --db data.jsonl delete user
    python key_value_store.py --db data.jsonl list
    python key_value_store.py --db data.jsonl compact
    python key_value_store.py --db data.jsonl info

Values may be any JSON-serializable object. The demo uses a temporary
directory and verifies persistence and compaction before exiting.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Iterator, Sequence


class StoreError(RuntimeError):
    """Raised for corrupt logs or I/O failures."""


class KeyValueStore:
    """Append-only JSONL key/value store with tombstones and compaction."""

    def __init__(self, path: str | Path, *, durable: bool = True) -> None:
        self.path = Path(path)
        self.durable = durable
        self._data: dict[str, Any] = {}
        self._records = 0
        self._tombstones = 0
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._replay()

    def _replay(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise StoreError(
                            f"corrupt JSON at line {line_number} of {self.path}"
                        ) from exc
                    if not isinstance(record, dict) or "op" not in record:
                        raise StoreError(f"invalid record at line {line_number}")
                    self._apply(record, replay=True)
        except OSError as exc:
            raise StoreError(f"could not read {self.path}: {exc}") from exc

    def _apply(self, record: dict[str, Any], *, replay: bool = False) -> None:
        operation = record.get("op")
        key = record.get("key")
        if not isinstance(key, str):
            raise StoreError("record key must be a string")
        if operation == "set":
            if "value" not in record:
                raise StoreError("set record is missing a value")
            self._data[key] = record["value"]
            if not replay:
                self._records += 1
        elif operation == "del":
            self._data.pop(key, None)
            if not replay:
                self._records += 1
                self._tombstones += 1
        else:
            raise StoreError(f"unknown operation {operation!r}")
        if replay:
            self._records += 1
            if operation == "del":
                self._tombstones += 1

    def _append(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()
                if self.durable:
                    os.fsync(handle.fileno())
        except OSError as exc:
            raise StoreError(f"could not append to {self.path}: {exc}") from exc

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` and append a durable record."""
        if not isinstance(key, str):
            raise TypeError("keys must be strings")
        if not key:
            raise ValueError("keys must not be empty")
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("value must be JSON-serializable") from exc
        with self._lock:
            self._append({"op": "set", "key": key, "value": value})
            self._data[key] = value
            self._records += 1

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        """Delete a key by appending a tombstone; return whether it existed."""
        with self._lock:
            existed = key in self._data
            self._append({"op": "del", "key": key})
            self._records += 1
            self._tombstones += 1
            self._data.pop(key, None)
            return existed

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def keys(self) -> list[str]:
        with self._lock:
            return sorted(self._data)

    def items(self) -> Iterator[tuple[str, Any]]:
        with self._lock:
            snapshot = sorted(self._data.items())
        return iter(snapshot)

    def stats(self) -> dict[str, int | str]:
        with self._lock:
            size = self.path.stat().st_size if self.path.exists() else 0
            return {
                "path": str(self.path),
                "keys": len(self._data),
                "log_records": self._records,
                "tombstones": self._tombstones,
                "bytes": size,
            }

    def compact(self) -> tuple[int, int]:
        """Rewrite live records atomically; return (before_bytes, after_bytes)."""
        with self._lock:
            before = self.path.stat().st_size if self.path.exists() else 0
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    for key in sorted(self._data):
                        line = json.dumps(
                            {"op": "set", "key": key, "value": self._data[key]},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        handle.write(line + "\n")
                    handle.flush()
                    if self.durable:
                        os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
            after = self.path.stat().st_size
            self._records = len(self._data)
            self._tombstones = 0
            return before, after


def _demo() -> None:
    with tempfile.TemporaryDirectory(prefix="kvstore-demo-") as directory:
        path = Path(directory) / "store.jsonl"
        store = KeyValueStore(path)
        store.set("language", "Python")
        store.set("version", 3.13)
        store.set("features", ["async", "typing", "wave"])
        store.set("obsolete", {"nested": True})
        store.delete("obsolete")
        print("initial:", store.stats())
        print("language =", store.get("language"))
        print("missing =", store.get("missing", "<default>"))

        # A second instance proves that state is recovered from the log.
        reopened = KeyValueStore(path)
        print("reopened keys:", reopened.keys())
        before, after = reopened.compact()
        print(f"compaction: {before} -> {after} bytes")
        print("after compact:", reopened.stats())

        reopened.set("extra", [1, 2, 3])
        final = KeyValueStore(path)
        print("final keys:", final.keys())
        print("log line count:", sum(1 for _ in path.open(encoding="utf-8")))
        assert final.get("language") == "Python"
        assert "obsolete" not in final
        print("persistence and tombstones verified")


def _parse_cli_value(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append-only JSONL key/value store.")
    parser.add_argument("--db", default="kvstore_demo.jsonl", help="database path")
    parser.add_argument("--demo", action="store_true", help="run a self-contained demonstration")
    parser.add_argument("--no-fsync", action="store_true", help="skip fsync for speed")
    subparsers = parser.add_subparsers(dest="command")

    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("key")
    set_parser.add_argument("value")

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("key")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("key")

    subparsers.add_parser("list")
    subparsers.add_parser("compact")
    subparsers.add_parser("info")
    args = parser.parse_args(argv)

    if args.demo:
        _demo()
        return 0
    if not args.command:
        parser.error("provide a command or use --demo")

    try:
        store = KeyValueStore(args.db, durable=not args.no_fsync)
        if args.command == "set":
            store.set(args.key, _parse_cli_value(args.value))
            print(f"set {args.key!r}; {len(store)} key(s) stored")
        elif args.command == "get":
            marker = object()
            value = store.get(args.key, marker)
            if value is marker:
                print(f"{args.key!r} not found")
                return 1
            print(json.dumps(value, ensure_ascii=False, indent=2))
        elif args.command == "delete":
            print(f"deleted {args.key!r}" if store.delete(args.key) else "key was not present; tombstone written")
        elif args.command == "list":
            for key, value in store.items():
                print(f"{key} = {json.dumps(value, ensure_ascii=False)}")
        elif args.command == "compact":
            before, after = store.compact()
            print(f"compacted {before} -> {after} bytes")
        elif args.command == "info":
            print(json.dumps(store.stats(), indent=2))
    except StoreError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
