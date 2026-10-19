"""Report disk usage for a directory tree: biggest folders, files and types.

Walks the tree once with ``os.scandir`` (no psutil), tolerating permission
errors and very deep paths.  Prints a bar chart, a largest-files table and a
breakdown by file extension.  ``--demo`` builds a temporary tree offline.

Usage:
    python disk_usage_report.py .
    python disk_usage_report.py ./projects --depth 2 --top 15
    python disk_usage_report.py . --min-size 1MB --json --output usage.json
    python disk_usage_report.py --demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Usage:
    root: Path
    files: int = 0
    directories: int = 0
    total_bytes: int = 0
    largest: list[tuple[int, str]] = field(default_factory=list)
    by_ext: dict[str, int] = field(default_factory=dict)
    by_dir: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def note_file(self, path: Path, size: int) -> None:
        self.files += 1
        self.total_bytes += size
        ext = path.suffix.lower() or "(no extension)"
        self.by_ext[ext] = self.by_ext.get(ext, 0) + size
        self.largest.append((size, str(path)))
        if len(self.largest) > 200:
            self.largest.sort(reverse=True)
            del self.largest[50:]


def human_bytes(value: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def parse_size(text: str) -> int:
    units = {"b": 1, "k": 1024, "kb": 1024, "m": 1024 ** 2, "mb": 1024 ** 2,
             "g": 1024 ** 3, "gb": 1024 ** 3}
    cleaned = text.strip().lower().rstrip("b")
    multiplier = 1
    for suffix, factor in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if cleaned.endswith(suffix) and cleaned[:-len(suffix)].replace(".", "", 1).isdigit():
            multiplier = factor
            cleaned = cleaned[:-len(suffix)]
            break
    try:
        return int(float(cleaned) * multiplier)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid size: {text!r}") from exc


def walk(root: Path, depth_limit: int | None, usage: Usage) -> None:
    """Iterative walk so pathological depth cannot overflow the stack."""
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            usage.directories += 1
                            if depth_limit is None or depth < depth_limit:
                                key = str(Path(entry.path).relative_to(root)) or "."
                                usage.by_dir.setdefault(key, 0)
                                stack.append((Path(entry.path), depth + 1))
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            usage.note_file(Path(entry.path), size)
                            # Attribute the file to its top-level folder.
                            rel = Path(entry.path).relative_to(root)
                            key = rel.parts[0] if len(rel.parts) > 1 else "."
                            usage.by_dir[key] = usage.by_dir.get(key, 0) + size
                    except OSError as exc:
                        usage.errors.append(f"{entry.path}: {exc}")
        except OSError as exc:
            usage.errors.append(f"{directory}: {exc}")


def bar(value: int, maximum: int, width: int = 28) -> str:
    if maximum <= 0:
        return ""
    return "#" * max(1, int(round(value / maximum * width))) if value else ""


def render(usage: Usage, top: int) -> str:
    lines = [
        f"Disk usage for {usage.root}",
        f"  files: {usage.files:,}   dirs: {usage.directories:,}   "
        f"total: {human_bytes(usage.total_bytes)}",
        "",
        "Largest top-level entries",
        "-" * 60,
    ]
    ordered = sorted(usage.by_dir.items(), key=lambda kv: kv[1], reverse=True)[:top]
    maximum = ordered[0][1] if ordered else 0
    for name, size in ordered:
        lines.append(f"  {name[:28]:<28} {human_bytes(size):>10}  {bar(size, maximum)}")

    lines += ["", f"Largest files (top {top})", "-" * 60]
    for size, path in sorted(usage.largest, reverse=True)[:top]:
        display = path if len(path) <= 58 else "..." + path[-55:]
        lines.append(f"  {human_bytes(size):>10}  {display}")

    lines += ["", "By extension", "-" * 60]
    ordered_ext = sorted(usage.by_ext.items(), key=lambda kv: kv[1], reverse=True)[:top]
    ext_max = ordered_ext[0][1] if ordered_ext else 0
    for ext, size in ordered_ext:
        share = size / usage.total_bytes * 100 if usage.total_bytes else 0
        lines.append(f"  {ext[:18]:<18} {human_bytes(size):>10} {share:>5.1f}%  "
                     f"{bar(size, ext_max)}")

    if usage.errors:
        lines += ["", f"Skipped {len(usage.errors)} path(s), first few:", "-" * 60]
        lines.extend(f"  {err}" for err in usage.errors[:5])
    return "\n".join(lines)


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        layout = {
            "docs/readme.txt": "x" * 1200,
            "docs/guide.md": "y" * 3400,
            "images/logo.png": "z" * 9000,
            "images/photo.jpg": "p" * 25000,
            "src/app.py": "print('hi')\n" * 120,
            "src/util.py": "pass\n" * 40,
            "empty/.keep": "",
        }
        for relative, content in layout.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        usage = Usage(root=root.resolve())
        walk(root, None, usage)
        print(render(usage, 5))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Directory disk usage report.")
    p.add_argument("path", nargs="?", type=Path, default=Path("."))
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--depth", type=int, default=None,
                   help="limit directory recursion depth")
    p.add_argument("--min-size", type=parse_size, default=0,
                   help="ignore files smaller than this (e.g. 1MB)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    if not args.path.is_dir():
        print(f"error: not a directory: {args.path}", file=sys.stderr)
        return 2
    if args.output and args.output.exists() and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    usage = Usage(root=args.path.resolve())
    walk(usage.root, args.depth, usage)

    if args.min_size:
        usage.largest = [item for item in usage.largest if item[0] >= args.min_size]

    if args.json or args.output:
        payload = {
            "root": str(usage.root),
            "files": usage.files,
            "directories": usage.directories,
            "total_bytes": usage.total_bytes,
            "by_extension": usage.by_ext,
            "by_directory": usage.by_dir,
            "largest_files": [{"bytes": size, "path": path}
                              for size, path in sorted(usage.largest, reverse=True)
                              [:max(1, args.top)]],
            "skipped": usage.errors,
        }
        text = json.dumps(payload, indent=2)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
            print(f"wrote report -> {args.output}")
        else:
            print(text)
    else:
        print(render(usage, max(1, args.top)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
