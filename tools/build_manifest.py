#!/usr/bin/env python3
"""Build a machine-readable manifest for the program dataset.

Scans every known language folder, hashes each source file, counts lines and
writes ``manifest.json`` at the repository root. The manifest is the canonical
inventory used by downstream training pipelines.

Usage:
    python tools/build_manifest.py
    python tools/build_manifest.py --output manifest.json --pretty
    python tools/build_manifest.py --language Python
    python tools/build_manifest.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Language folder -> (source suffix, human-readable name)
LANGUAGES: dict[str, tuple[str, str]] = {
    "Python": (".py", "Python"),
    "JavaScript": (".js", "JavaScript"),
    "TypeScript": (".ts", "TypeScript"),
    "Rust": (".rs", "Rust"),
    "Go": (".go", "Go"),
    "C": (".c", "C"),
    "Cpp": (".cpp", "C++"),
    "Java": (".java", "Java"),
}

# Files that live inside a language folder but are not programs.
IGNORED_NAMES = {"README.md", "readme.md", ".gitkeep", "__init__.py"}


@dataclass(frozen=True)
class Record:
    id: str
    language: str
    domain: str
    path: str
    filename: str
    lines: int
    bytes: int
    sha256: str


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_lines(path: Path) -> int:
    """Count logical lines without loading the whole file into memory twice."""
    lines = 0
    last_byte = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            lines += chunk.count(b"\n")
            last_byte = chunk[-1:]
    if last_byte and last_byte != b"\n":
        lines += 1
    return lines


def scan_language(language: str, suffix: str) -> list[Record]:
    folder = ROOT / language
    if not folder.is_dir():
        return []

    records: list[Record] = []
    for path in sorted(folder.rglob(f"*{suffix}")):
        if not path.is_file() or path.name in IGNORED_NAMES:
            continue
        relative = path.relative_to(ROOT)
        domain = relative.parts[1] if len(relative.parts) > 2 else "root"
        records.append(
            Record(
                id=relative.as_posix(),
                language=language,
                domain=domain,
                path=relative.as_posix(),
                filename=path.name,
                lines=count_lines(path),
                bytes=path.stat().st_size,
                sha256=sha256_of(path),
            )
        )
    return records


def build_manifest(selected: list[str] | None = None, timestamp: str | None = None) -> dict:
    records: list[Record] = []
    per_language: dict[str, dict[str, object]] = {}

    for language, (suffix, display) in LANGUAGES.items():
        if selected and language not in selected:
            continue
        found = scan_language(language, suffix)
        if not found:
            continue
        records.extend(found)
        domains: dict[str, int] = {}
        for record in found:
            domains[record.domain] = domains.get(record.domain, 0) + 1
        per_language[language] = {
            "name": display,
            "suffix": suffix,
            "programs": len(found),
            "lines": sum(r.lines for r in found),
            "domains": dict(sorted(domains.items())),
        }

    total_lines = sum(r.lines for r in records)
    return {
        "schema_version": 1,
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repository": "https://github.com/codec07/programDataset",
        "license": "MIT",
        "languages": per_language,
        "totals": {
            "programs": len(records),
            "lines": total_lines,
            "bytes": sum(r.bytes for r in records),
            "languages": len(per_language),
        },
        "files": [asdict(r) for r in records],
    }


def compare_with_existing(manifest: dict, path: Path) -> bool:
    """Return True when the on-disk manifest matches the freshly built one."""
    if not path.is_file():
        print(f"manifest missing: {path}", file=sys.stderr)
        return False
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read existing manifest: {exc}", file=sys.stderr)
        return False

    # Timestamps are expected to differ; everything else must match.
    for candidate in (existing, manifest):
        candidate.pop("generated_at", None)
    if existing != manifest:
        print("manifest is out of date; run: python tools/build_manifest.py", file=sys.stderr)
        return False
    print("manifest is up to date.")
    return True


def print_summary(manifest: dict) -> None:
    print(f"{'Language':<12} {'Programs':>9} {'Lines':>9}  Domains")
    print("-" * 62)
    for language, info in manifest["languages"].items():
        domains = ", ".join(f"{name} ({count})" for name, count in info["domains"].items())
        print(f"{language:<12} {info['programs']:>9} {info['lines']:>9}  {domains}")
    totals = manifest["totals"]
    print("-" * 62)
    print(f"{'TOTAL':<12} {totals['programs']:>9} {totals['lines']:>9}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build manifest.json describing every program in the dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "manifest.json",
        help="output path (default: manifest.json at repository root)",
    )
    parser.add_argument(
        "--language",
        action="append",
        choices=sorted(LANGUAGES),
        help="limit scanning to a language folder (repeatable)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="indent JSON for human-readable diffs (larger file)",
    )
    parser.add_argument(
        "--timestamp",
        help="override generated_at (useful for reproducible builds)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the existing manifest is current; write nothing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args.language, args.timestamp)

    if manifest["totals"]["programs"] == 0:
        print("no program files found; nothing to write.", file=sys.stderr)
        return 1

    if args.check:
        return 0 if compare_with_existing(manifest, args.output) else 1

    print_summary(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2 if args.pretty else None, ensure_ascii=False)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {args.output} ({args.output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
