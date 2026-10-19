#!/usr/bin/env python3
"""Compute file hashes and verify checksum files.

Supported algorithms are those guaranteed by hashlib (md5, sha1, sha256,
sha512, blake2b, ...). Checksum files use the common `sha256sum` format:
one "<hex digest>  <path>" per line, with optional '*' before the path.
Relative paths in a checksum file are resolved against that file's folder.

Exit status: 0 all verified, 1 mismatches or unreadable files, 2 usage error.

Usage:
    python hash_checker.py report.pdf
    python hash_checker.py *.zip --algorithm sha512
    python hash_checker.py backup.tar.gz --expected 9f86d081...
    python hash_checker.py --check SHA256SUMS
    python hash_checker.py --check checksums.sha256 --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

CHUNK_SIZE = 1024 * 1024
CHECKSUM_RE = re.compile(r"^(?P<digest>[0-9a-fA-F]{8,128})\s+\*?(?P<name>.+?)\s*$")


@dataclass
class CheckResult:
    """Outcome of verifying one file."""

    path: str
    expected: str
    actual: str | None
    status: str  # "ok", "failed" or "missing"


def read_bytes(path: Path) -> bytes:
    """Read a checksum file as UTF-8."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")


def hash_file(path: Path, algorithm: str) -> str:
    """Hash a file in chunks, raising a friendly error on failure."""
    digest = hashlib.new(algorithm)
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_SIZE):
                digest.update(chunk)
    except FileNotFoundError:
        raise SystemExit(f"error: file not found: {path}")
    except IsADirectoryError:
        raise SystemExit(f"error: is a directory: {path}")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")
    return digest.hexdigest()


def expected_length(algorithm: str) -> int:
    """Hex length of a digest for *algorithm*."""
    return hashlib.new(algorithm).digest_size * 2


def parse_checksum_file(path: Path, algorithm: str) -> list[tuple[str, Path]]:
    """Parse a checksum file into (digest, resolved path) pairs."""
    text = read_bytes(path).decode("utf-8", errors="replace")
    entries: list[tuple[str, Path]] = []
    wanted = expected_length(algorithm)
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = CHECKSUM_RE.match(stripped)
        if not match:
            print(f"warning: {path}:{number}: ignoring malformed line", file=sys.stderr)
            continue
        digest = match.group("digest").lower()
        if len(digest) != wanted:
            print(
                f"warning: {path}:{number}: digest length {len(digest)} does not "
                f"match {algorithm} ({wanted}); skipping",
                file=sys.stderr,
            )
            continue
        target = Path(match.group("name"))
        if not target.is_absolute():
            target = path.parent / target
        entries.append((digest, target))
    if not entries:
        raise SystemExit(f"error: no valid checksum entries in {path}")
    return entries


def verify_checksums(entries: Sequence[tuple[str, Path]], algorithm: str) -> list[CheckResult]:
    """Verify every (digest, path) pair."""
    results: list[CheckResult] = []
    for expected, target in entries:
        if not target.is_file():
            results.append(CheckResult(str(target), expected, None, "missing"))
            continue
        actual = hash_file(target, algorithm)
        status = "ok" if actual == expected else "failed"
        results.append(CheckResult(str(target), expected, actual, status))
    return results


def print_check_results(results: Sequence[CheckResult]) -> None:
    """Print per-file verification lines."""
    for result in results:
        if result.status == "ok":
            print(f"OK      {result.path}")
        elif result.status == "missing":
            print(f"MISSING {result.path}")
        else:
            print(f"FAILED  {result.path}")
            print(f"        expected {result.expected}")
            print(f"        actual   {result.actual}")
    ok = sum(1 for item in results if item.status == "ok")
    failed = len(results) - ok
    print(f"\n{ok} verified, {failed} failed or missing.")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute hashes and verify checksum files.",
        epilog="Checksum lines look like: <hex>  <filename>",
    )
    parser.add_argument("files", nargs="*", help="files to hash")
    parser.add_argument("--algorithm", default="sha256",
                        choices=sorted(hashlib.algorithms_guaranteed),
                        help="hash algorithm (default: sha256)")
    parser.add_argument("--expected", metavar="HEX",
                        help="compare a single file against this digest")
    parser.add_argument("--check", metavar="FILE",
                        help="verify every entry in a checksum file")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON")
    args = parser.parse_args(argv)

    if args.expected and args.check:
        parser.error("--expected and --check are mutually exclusive")
    if args.expected and len(args.files) != 1:
        parser.error("--expected requires exactly one file")
    if args.check and args.files:
        parser.error("--check cannot be combined with individual files")
    if not args.check and not args.files:
        parser.error("provide at least one file, or use --check")
    if args.expected:
        digest = args.expected.strip().lower()
        if not re.fullmatch(r"[0-9a-f]+", digest):
            parser.error("--expected must be a hexadecimal digest")
        if len(digest) != expected_length(args.algorithm):
            parser.error(
                f"--expected has {len(digest)} hex characters; "
                f"{args.algorithm} needs {expected_length(args.algorithm)}"
            )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.check:
        checksum_path = Path(args.check)
        entries = parse_checksum_file(checksum_path, args.algorithm)
        results = verify_checksums(entries, args.algorithm)
        if args.as_json:
            print(json.dumps([asdict(item) for item in results], indent=2))
        else:
            print_check_results(results)
        return 0 if all(item.status == "ok" for item in results) else 1

    if args.expected:
        target = Path(args.files[0])
        actual = hash_file(target, args.algorithm)
        match = actual == args.expected.strip().lower()
        if args.as_json:
            print(json.dumps({
                "path": str(target), "algorithm": args.algorithm,
                "expected": args.expected.strip().lower(), "actual": actual,
                "match": match,
            }, indent=2))
        else:
            print(f"{'OK' if match else 'MISMATCH'}  {target}")
            if not match:
                print(f"expected {args.expected.strip().lower()}")
                print(f"actual   {actual}")
        return 0 if match else 1

    rows = []
    for name in args.files:
        path = Path(name)
        rows.append({"path": str(path), "algorithm": args.algorithm,
                     "digest": hash_file(path, args.algorithm)})
    if args.as_json:
        print(json.dumps(rows, indent=2))
    else:
        width = max(len(row["digest"]) for row in rows)
        for row in rows:
            print(f"{row['digest']:<{width}}  {row['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
