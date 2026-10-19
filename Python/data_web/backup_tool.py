"""Back up a directory into a timestamped snapshot with a SHA-256 manifest.

Commands:
    backup   copy a tree into <dest>/<name>_<timestamp>/ (+ manifest.json)
    verify   re-hash a snapshot and report changed/missing files
    restore  copy files from a snapshot back into a target directory
    list     show snapshots under a destination directory

Supports --dry-run on mutating commands and refuses to overwrite existing
files without --force.

Usage:
    python backup_tool.py backup ./project --dest ./backups
    python backup_tool.py backup ./project --dest ./backups --zip --dry-run
    python backup_tool.py list ./backups
    python backup_tool.py verify ./backups/project_20261019_120000
    python backup_tool.py restore SNAPSHOT ./restored --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

MANIFEST = "manifest.json"
CHUNK = 1024 * 1024
DEFAULT_EXCLUDES = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Snapshot backups with hash manifests.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("backup", help="create a snapshot")
    b.add_argument("source", type=Path)
    b.add_argument("--dest", type=Path, required=True)
    b.add_argument("--zip", action="store_true", help="archive the snapshot as .zip")
    b.add_argument("--exclude", action="append", default=[], metavar="NAME")

    v = sub.add_parser("verify", help="verify a snapshot manifest")
    v.add_argument("snapshot", type=Path)

    r = sub.add_parser("restore", help="restore a snapshot")
    r.add_argument("snapshot", type=Path)
    r.add_argument("target", type=Path)

    ls = sub.add_parser("list", help="list snapshots")
    ls.add_argument("dest", type=Path)
    return p.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_files(root: Path, excludes: set[str]) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in excludes for part in path.relative_to(root).parts):
            continue
        if path.is_file() and not path.is_symlink():
            yield path


def create_backup(source: Path, dest: Path, as_zip: bool, excludes: set[str],
                  dry_run: bool, force: bool) -> int:
    if not source.is_dir():
        print(f"error: source is not a directory: {source}", file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{source.resolve().name}_{stamp}"
    target = dest / name
    if target.exists() and not force:
        print(f"error: {target} exists (use --force)", file=sys.stderr)
        return 2

    files = list(iter_files(source, excludes))
    total = sum(f.stat().st_size for f in files)
    print(f"source: {source.resolve()}")
    print(f"files : {len(files)}  bytes: {total}")
    print(f"target: {target}{'.zip' if as_zip else ''}")
    if dry_run:
        for path in files[:10]:
            print(f"  would copy {path.relative_to(source)}")
        if len(files) > 10:
            print(f"  ... {len(files) - 10} more")
        print("[dry-run] nothing written")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    stage = target
    stage.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    try:
        for path in files:
            relative = path.relative_to(source)
            copy_to = stage / relative
            copy_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copy_to)
            entries.append({
                "path": relative.as_posix(),
                "size": copy_to.stat().st_size,
                "sha256": sha256_file(copy_to),
                "mtime": path.stat().st_mtime,
            })
        manifest = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "source": str(source.resolve()),
            "files": entries,
            "total_bytes": sum(e["size"] for e in entries),
        }
        with (stage / MANIFEST).open("w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, indent=2)

        if as_zip:
            archive = target.with_suffix(".zip")
            if archive.exists() and not force:
                raise FileExistsError(f"{archive} exists (use --force)")
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        zf.write(path, path.relative_to(stage).as_posix())
            shutil.rmtree(stage)
            print(f"archive: {archive} ({archive.stat().st_size} bytes)")
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    print(f"backed up {len(entries)} file(s)")
    return 0


def load_manifest(where: Path) -> dict[str, Any]:
    if where.suffix.lower() == ".zip":
        with zipfile.ZipFile(where) as zf:
            return json.loads(zf.read(MANIFEST).decode("utf-8"))
    with (where / MANIFEST).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def verify(snapshot: Path) -> int:
    if not snapshot.exists():
        print(f"error: snapshot not found: {snapshot}", file=sys.stderr)
        return 2
    try:
        manifest = load_manifest(snapshot)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: cannot read manifest: {exc}", file=sys.stderr)
        return 1

    bad = 0
    if snapshot.suffix.lower() == ".zip":
        with zipfile.ZipFile(snapshot) as zf:
            names = set(zf.namelist())
            for entry in manifest["files"]:
                if entry["path"] not in names:
                    print(f"MISSING {entry['path']}")
                    bad += 1
                    continue
                digest = hashlib.sha256()
                with zf.open(entry["path"]) as member:
                    for block in iter(lambda: member.read(CHUNK), b""):
                        digest.update(block)
                if digest.hexdigest() != entry["sha256"]:
                    print(f"CHANGED {entry['path']}")
                    bad += 1
    else:
        for entry in manifest["files"]:
            path = snapshot / entry["path"]
            if not path.is_file():
                print(f"MISSING {entry['path']}")
                bad += 1
            elif sha256_file(path) != entry["sha256"]:
                print(f"CHANGED {entry['path']}")
                bad += 1
    print(f"verified {len(manifest['files'])} file(s), {bad} problem(s)")
    return 1 if bad else 0


def safe_destination(root: Path, relative: str) -> Path:
    """Resolve a manifest path, refusing anything outside the restore root."""
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"unsafe path in manifest: {relative!r}")
    return candidate


def restore(snapshot: Path, target: Path, dry_run: bool, force: bool) -> int:
    if not snapshot.exists():
        print(f"error: snapshot not found: {snapshot}", file=sys.stderr)
        return 2
    manifest = load_manifest(snapshot)
    destinations = {entry["path"]: safe_destination(target, entry["path"])
                    for entry in manifest["files"]}
    conflicts = [path for path in destinations.values() if path.exists()]
    if conflicts and not force and not dry_run:
        print(f"error: {len(conflicts)} file(s) already exist in {target} "
              "(use --force)", file=sys.stderr)
        return 2

    restored = 0
    if snapshot.suffix.lower() == ".zip":
        with zipfile.ZipFile(snapshot) as zf:
            for entry in manifest["files"]:
                out = destinations[entry["path"]]
                if dry_run:
                    print(f"would restore {entry['path']}")
                    restored += 1
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(zf.read(entry["path"]))
                restored += 1
    else:
        for entry in manifest["files"]:
            out = destinations[entry["path"]]
            if dry_run:
                print(f"would restore {entry['path']}")
                restored += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snapshot / entry["path"], out)
            restored += 1
    print(f"{'planned' if dry_run else 'restored'} {restored} file(s) -> {target}")
    return 0


def list_snapshots(dest: Path) -> int:
    if not dest.is_dir():
        print(f"error: not a directory: {dest}", file=sys.stderr)
        return 2
    items = sorted(p for p in dest.iterdir()
                   if p.is_dir() or p.suffix.lower() == ".zip")
    if not items:
        print("no snapshots found")
        return 0
    for item in items:
        size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file()) \
            if item.is_dir() else item.stat().st_size
        print(f"{item.name:<40} {size:>12,} bytes")
    return 0


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "project"
        (source / "src").mkdir(parents=True)
        (source / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
        (source / "README.md").write_text("# Demo\n", encoding="utf-8")
        (source / "__pycache__").mkdir()
        (source / "__pycache__" / "junk.pyc").write_bytes(b"\x00" * 10)

        backups = root / "backups"
        create_backup(source, backups, False, DEFAULT_EXCLUDES, False, False)
        snapshot = next(p for p in backups.iterdir() if p.is_dir())
        print()
        verify(snapshot)
        print()
        create_backup(source, backups / "zips", True, DEFAULT_EXCLUDES, False, False)
        print()
        list_snapshots(backups)
        print()
        restore(snapshot, root / "restored", False, False)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        print(__doc__)
        return 0
    args = parse_args(argv)
    try:
        if args.command == "backup":
            excludes = set(DEFAULT_EXCLUDES) | set(args.exclude)
            return create_backup(args.source, args.dest, args.zip, excludes,
                                 args.dry_run, args.force)
        if args.command == "verify":
            return verify(args.snapshot)
        if args.command == "restore":
            return restore(args.snapshot, args.target, args.dry_run, args.force)
        if args.command == "list":
            return list_snapshots(args.dest)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        raise SystemExit(demo())
    raise SystemExit(main())
