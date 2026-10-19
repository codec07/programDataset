"""Concurrent HTTP download manager with resume, retries and checksums.

Features:
  * multiple URLs, optionally listed in a file ("url [sha256]" per line)
  * HTTP Range resume from a ``.part`` file when the server supports it
  * up to N parallel downloads, 3 retries with backoff, 10 s timeout
  * optional SHA-256 verification, ``--dry-run`` and ``--force``
  * ``--demo`` runs a local Range-capable server, so no internet is needed

Usage:
    python download_manager.py https://example.com/file.zip --dest downloads
    python download_manager.py --file urls.txt --dest downloads --jobs 4
    python download_manager.py URL --sha256 <hex> --force
    python download_manager.py --demo
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

USER_AGENT = "download-manager/1.0 (educational sample)"
TIMEOUT = 10.0
CHUNK = 64 * 1024
RETRIES = 3


class DownloadError(RuntimeError):
    pass


def safe_filename(url: str) -> str:
    name = Path(urllib.parse.urlsplit(url).path).name
    name = urllib.parse.unquote(name)
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(". ")
    return name or "download.bin"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, dest_dir: Path, *, force: bool, expect_sha: str | None,
             dry_run: bool, retries: int = RETRIES) -> tuple[str, str]:
    """Download one URL; return (status, message)."""
    if not url.startswith(("http://", "https://")):
        return "error", f"unsupported URL: {url}"
    final = dest_dir / safe_filename(url)
    part = final.with_name(final.name + ".part")

    if final.exists() and not force:
        if expect_sha and sha256_file(final) == expect_sha.lower():
            return "skipped", f"{final.name} already present and verified"
        return "skipped", f"{final.name} exists (use --force)"
    if dry_run:
        return "planned", f"would download {url} -> {final}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(retries):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
                status = resp.status
                if offset and status == 200:
                    offset = 0  # server ignored Range: restart the file
                total = resp.headers.get("Content-Length")
                total_bytes = (int(total) + offset) if total and total.isdigit() else None
                mode = "ab" if offset else "wb"
                written = offset
                with part.open(mode) as fh:
                    while True:
                        block = resp.read(CHUNK)
                        if not block:
                            break
                        fh.write(block)
                        written += len(block)
                if total_bytes is not None and written != total_bytes:
                    raise DownloadError(
                        f"incomplete: {written}/{total_bytes} bytes")
            if expect_sha:
                actual = sha256_file(part)
                if actual != expect_sha.lower():
                    part.unlink(missing_ok=True)
                    raise DownloadError(
                        f"sha256 mismatch: got {actual[:12]}..., "
                        f"expected {expect_sha[:12]}...")
            if final.exists() and force:
                final.unlink()
            part.replace(final)
            return "done", f"{final.name} ({final.stat().st_size:,} bytes)"
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and part.exists():  # nothing left to fetch
                part.replace(final)
                return "done", f"{final.name} (already complete)"
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError, DownloadError) as exc:
            last_error = exc
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    return "error", f"{url}: {last_error}"


class RangeHandler(http.server.BaseHTTPRequestHandler):
    server_version = "DemoFiles/1.0"

    def do_GET(self) -> None:  # noqa: N802
        name = self.path.strip("/") or "demo.bin"
        if name not in self.server.files:  # type: ignore[attr-defined]
            self.send_error(404, "not found")
            return
        data: bytes = self.server.files[name]  # type: ignore[attr-defined]
        start = 0
        range_header = self.headers.get("Range", "")
        match = re.match(r"bytes=(\d+)-$", range_header)
        if match:
            start = int(match.group(1))
            if start >= len(data):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(data)}")
                self.end_headers()
                return
        body = data[start:]
        self.send_response(206 if match else 200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        if match:
            self.send_header("Content-Range",
                             f"bytes {start}-{len(data) - 1}/{len(data)}")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        return


def demo() -> int:
    payloads = {"alpha.txt": b"alpha " * 2000, "beta.bin": bytes(range(256)) * 100}
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
    server.files = payloads  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    failures = 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out"
            urls = [f"{base}/{name}" for name in payloads]
            results = [download(url, dest, force=False, expect_sha=None,
                                dry_run=False) for url in urls]
            for status, message in results:
                print(f"[{status}] {message}")
                if status != "done":
                    failures += 1
            # Resume test: truncate a .part and fetch only the tail.
            target = dest / "alpha.txt"
            expected = payloads["alpha.txt"]
            target.unlink()
            part = target.with_name("alpha.txt.part")
            part.write_bytes(expected[:1000])
            status, message = download(f"{base}/alpha.txt", dest, force=True,
                                       expect_sha=None, dry_run=False)
            print(f"[{status}] resume -> {message}")
            if not target.exists() or target.read_bytes() != expected:
                print("[FAIL] resumed file differs from source")
                failures += 1
            else:
                print("[PASS] resume produced identical bytes")
            digest = hashlib.sha256(payloads["beta.bin"]).hexdigest()
            status, message = download(f"{base}/beta.bin", dest, force=True,
                                       expect_sha=digest, dry_run=False)
            print(f"[{status}] checksum -> {message}")
            if status != "done":
                failures += 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("demo", "FAILED" if failures else "passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Concurrent resumable download manager.")
    p.add_argument("urls", nargs="*", help="one or more URLs")
    p.add_argument("--file", type=Path, help="file with 'url [sha256]' lines")
    p.add_argument("--dest", type=Path, default=Path("downloads"))
    p.add_argument("--jobs", type=int, default=3)
    p.add_argument("--sha256", help="expected digest for a single URL")
    p.add_argument("--force", action="store_true", help="re-download existing files")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--demo", action="store_true", help="local offline demo")
    args = p.parse_args(argv)

    if args.demo:
        return demo()

    jobs: list[tuple[str, str | None]] = []
    if args.file:
        if not args.file.is_file():
            print(f"error: file not found: {args.file}", file=sys.stderr)
            return 2
        for line in args.file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            jobs.append((parts[0], parts[1] if len(parts) > 1 else None))
    jobs.extend((url, None) for url in args.urls)
    if not jobs:
        print("error: no URLs supplied (or use --demo)", file=sys.stderr)
        return 2
    if args.sha256 and len(jobs) != 1:
        print("error: --sha256 only works with a single URL", file=sys.stderr)
        return 2
    if args.sha256:
        jobs[0] = (jobs[0][0], args.sha256)

    failures = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(download, url, args.dest, force=args.force,
                        expect_sha=digest, dry_run=args.dry_run): url
            for url, digest in jobs
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                status, message = future.result()
            except Exception as exc:  # defensive: never lose a worker error
                status, message = "error", f"{url}: {exc}"
            print(f"[{status}] {message}")
            if status == "error":
                failures += 1
    print(f"{len(jobs)} download(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
