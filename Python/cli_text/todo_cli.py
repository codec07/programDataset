#!/usr/bin/env python3
"""A small, file-backed todo list for the terminal.

Tasks live in a JSON file (todo.json in the current directory by default)
and keep stable numeric IDs. Writes are atomic: a temporary file is
replaced in one step, so an interrupted save cannot truncate the list.
Corrupt files are reported instead of being overwritten.

Usage:
    python todo_cli.py add "Write the report" --priority high
    python todo_cli.py add "Buy milk" "Call Sam"
    python todo_cli.py list
    python todo_cli.py list --pending --json
    python todo_cli.py done 1
    python todo_cli.py edit 2 "Write the final report"
    python todo_cli.py remove 3
    python todo_cli.py --file work.json clear --done --yes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

PRIORITIES = ("low", "normal", "high")
PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}
DEFAULT_FILE = "todo.json"


@dataclass
class Item:
    """One todo entry."""

    id: int
    text: str
    done: bool = False
    priority: str = "normal"
    created: str = ""
    completed: str | None = None


class TodoStore:
    """Load, mutate and save a JSON todo list."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: list[Item] = []
        self.next_id = 1

    def load(self) -> None:
        """Read the JSON file; a missing file starts an empty list."""
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"error: {self.path} is not valid JSON at line {exc.lineno}: {exc.msg}"
            )
        except OSError as exc:
            raise SystemExit(f"error: cannot read {self.path}: {exc}")

        if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
            raise SystemExit(f"error: {self.path} has an unexpected structure")
        try:
            self.items = [
                Item(
                    id=int(entry["id"]),
                    text=str(entry["text"]),
                    done=bool(entry.get("done", False)),
                    priority=str(entry.get("priority", "normal")),
                    created=str(entry.get("created", "")),
                    completed=entry.get("completed"),
                )
                for entry in raw["items"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"error: invalid todo entry in {self.path}: {exc}")
        self.next_id = int(raw.get("next_id", max((i.id for i in self.items), default=0) + 1))

    def save(self) -> None:
        """Atomically write the list to disk."""
        payload = {
            "next_id": self.next_id,
            "items": [asdict(item) for item in self.items],
        }
        parent = self.path.parent if str(self.path.parent) else Path(".")
        try:
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temp_name = handle.name
            os.replace(temp_name, self.path)
        except OSError as exc:
            raise SystemExit(f"error: cannot save {self.path}: {exc}")

    def find(self, item_id: int) -> Item | None:
        """Return the item with *item_id* or None."""
        return next((item for item in self.items if item.id == item_id), None)

    def add(self, text: str, priority: str) -> Item:
        """Create and return a new item."""
        item = Item(
            id=self.next_id,
            text=text,
            priority=priority,
            created=datetime.now().isoformat(timespec="seconds"),
        )
        self.next_id += 1
        self.items.append(item)
        return item

    def missing_ids(self, ids: Sequence[int]) -> list[int]:
        """Return ids that do not exist in the store."""
        existing = {item.id for item in self.items}
        return [item_id for item_id in ids if item_id not in existing]


def format_table(items: Sequence[Item]) -> None:
    """Print items as an aligned table."""
    if not items:
        print("No matching tasks.")
        return
    id_width = max(2, len(str(max(item.id for item in items))))
    print(f"{'ID':>{id_width}}  {'DONE':<4}  {'PRIORITY':<8}  TASK")
    print("-" * (id_width + 20 + 20))
    for item in items:
        status = "[x]" if item.done else "[ ]"
        priority = item.priority.upper()
        print(f"{item.id:>{id_width}}  {status:<4}  {priority:<8}  {item.text}")
    pending = sum(1 for item in items if not item.done)
    print(f"\n{len(items)} task(s), {pending} pending, {len(items) - pending} done")


def select_items(store: TodoStore, args: argparse.Namespace) -> list[Item]:
    """Apply list filters and sorting."""
    items = list(store.items)
    if args.pending:
        items = [item for item in items if not item.done]
    elif args.done:
        items = [item for item in items if item.done]
    if args.sort == "priority":
        items.sort(key=lambda item: (PRIORITY_ORDER.get(item.priority, 9), item.id))
    else:
        items.sort(key=lambda item: item.id)
    return items


def cmd_add(store: TodoStore, args: argparse.Namespace) -> int:
    text = " ".join(args.text).strip()
    if not text:
        print("error: task text cannot be empty", file=sys.stderr)
        return 1
    item = store.add(text, args.priority)
    store.save()
    print(f"Added task {item.id}: {item.text}")
    return 0


def cmd_list(store: TodoStore, args: argparse.Namespace) -> int:
    items = select_items(store, args)
    if args.as_json:
        print(json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2))
    else:
        format_table(items)
    return 0


def cmd_done(store: TodoStore, args: argparse.Namespace, done: bool) -> int:
    missing = store.missing_ids(args.ids)
    if missing:
        print(f"error: unknown task id(s): {', '.join(map(str, missing))}", file=sys.stderr)
        return 1
    changed = 0
    for item_id in args.ids:
        item = store.find(item_id)
        if item is None:  # already guarded by missing_ids
            continue
        if item.done == done:
            print(f"Task {item_id} is already {'done' if done else 'pending'}; unchanged.")
            continue
        item.done = done
        item.completed = datetime.now().isoformat(timespec="seconds") if done else None
        changed += 1
        print(f"Task {item_id} marked {'done' if done else 'pending'}.")
    if changed:
        store.save()
    return 0


def cmd_edit(store: TodoStore, args: argparse.Namespace) -> int:
    item = store.find(args.id)
    if item is None:
        print(f"error: unknown task id: {args.id}", file=sys.stderr)
        return 1
    text = " ".join(args.text).strip()
    if not text:
        print("error: task text cannot be empty", file=sys.stderr)
        return 1
    item.text = text
    if args.priority:
        item.priority = args.priority
    store.save()
    print(f"Updated task {item.id}: {item.text}")
    return 0


def cmd_remove(store: TodoStore, args: argparse.Namespace) -> int:
    missing = store.missing_ids(args.ids)
    if missing:
        print(f"error: unknown task id(s): {', '.join(map(str, missing))}", file=sys.stderr)
        return 1
    targets = [item for item in store.items if item.id in set(args.ids)]
    if args.dry_run:
        for item in targets:
            print(f"[dry-run] would remove task {item.id}: {item.text}")
        return 0
    store.items = [item for item in store.items if item.id not in set(args.ids)]
    store.save()
    for item in targets:
        print(f"Removed task {item.id}: {item.text}")
    return 0


def cmd_clear(store: TodoStore, args: argparse.Namespace) -> int:
    if args.done:
        targets = [item for item in store.items if item.done]
        label = "completed task(s)"
    else:
        targets = list(store.items)
        label = "task(s)"
    if not targets:
        print(f"No {label} to clear.")
        return 0
    if args.dry_run:
        for item in targets:
            print(f"[dry-run] would remove task {item.id}: {item.text}")
        print(f"[dry-run] {len(targets)} {label} would be removed.")
        return 0
    if not args.yes:
        print(
            f"error: refusing to remove {len(targets)} {label} without --yes "
            "(use --dry-run to preview)",
            file=sys.stderr,
        )
        return 1
    ids = {item.id for item in targets}
    store.items = [item for item in store.items if item.id not in ids]
    store.save()
    print(f"Cleared {len(targets)} {label}.")
    return 0


def cmd_priority(store: TodoStore, args: argparse.Namespace) -> int:
    item = store.find(args.id)
    if item is None:
        print(f"error: unknown task id: {args.id}", file=sys.stderr)
        return 1
    item.priority = args.priority
    store.save()
    print(f"Task {item.id} priority set to {args.priority}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A small file-backed todo list.",
        epilog=f"Data is stored in ./{DEFAULT_FILE} unless --file is given.",
    )
    parser.add_argument("--file", default=DEFAULT_FILE, metavar="PATH",
                        help=f"todo JSON file (default: {DEFAULT_FILE})")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    add = sub.add_parser("add", help="add one or more tasks")
    add.add_argument("text", nargs="+", help="task text")
    add.add_argument("--priority", choices=PRIORITIES, default="normal")
    add.set_defaults(func=cmd_add)

    listing = sub.add_parser("list", help="show tasks")
    group = listing.add_mutually_exclusive_group()
    group.add_argument("--pending", action="store_true", help="only pending tasks")
    group.add_argument("--done", action="store_true", help="only completed tasks")
    listing.add_argument("--sort", choices=("id", "priority"), default="id")
    listing.add_argument("--json", action="store_true", dest="as_json")
    listing.set_defaults(func=cmd_list)

    done = sub.add_parser("done", help="mark tasks as done")
    done.add_argument("ids", nargs="+", type=int, metavar="ID")
    done.set_defaults(func=lambda store, args: cmd_done(store, args, True))

    undone = sub.add_parser("undone", help="mark tasks as pending again")
    undone.add_argument("ids", nargs="+", type=int, metavar="ID")
    undone.set_defaults(func=lambda store, args: cmd_done(store, args, False))

    edit = sub.add_parser("edit", help="change a task's text or priority")
    edit.add_argument("id", type=int, metavar="ID")
    edit.add_argument("text", nargs="+", help="new task text")
    edit.add_argument("--priority", choices=PRIORITIES)
    edit.set_defaults(func=cmd_edit)

    priority = sub.add_parser("priority", help="set only the priority")
    priority.add_argument("id", type=int, metavar="ID")
    priority.add_argument("priority", choices=PRIORITIES)
    priority.set_defaults(func=cmd_priority)

    remove = sub.add_parser("remove", help="delete specific tasks")
    remove.add_argument("ids", nargs="+", type=int, metavar="ID")
    remove.add_argument("--dry-run", action="store_true")
    remove.set_defaults(func=cmd_remove)

    clear = sub.add_parser("clear", help="delete all tasks or all completed tasks")
    target = clear.add_mutually_exclusive_group(required=True)
    target.add_argument("--done", action="store_true", help="only completed tasks")
    target.add_argument("--all", action="store_true", help="every task")
    clear.add_argument("--yes", action="store_true", help="confirm deletion")
    clear.add_argument("--dry-run", action="store_true", help="preview only")
    clear.set_defaults(func=cmd_clear)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file).expanduser()
    store = TodoStore(path)
    store.load()
    return int(args.func(store, args))


if __name__ == "__main__":
    sys.exit(main())
