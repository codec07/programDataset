"""Serve a directory over HTTP with safe path handling and directory listings.

Guards against path traversal by resolving every request inside the served
root.  Uses ``http.server`` only, supports HEAD, conditional-free caching
headers, and a ``--once`` self-test that starts a server on an ephemeral port,
requests a file, and shuts down.

Usage:
    python static_file_server.py ./public --port 8080
    python static_file_server.py ./public --bind 0.0.0.0 --port 9000
    python static_file_server.py --once        # offline self-test
"""

from __future__ import annotations

import argparse
import html
import mimetypes
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

INDEX_FILES = ("index.html", "index.htm")
MAX_DIR_ENTRIES = 500


class StaticHandler(BaseHTTPRequestHandler):
    server_version = "StaticServer/1.0"
    root: Path = Path(".")

    def _resolve(self, raw_path: str) -> Path | None:
        """Map a URL path to a file inside root, or None if unsafe."""
        path = unquote(urlsplit(raw_path).path)
        if "\x00" in path:
            return None
        relative = path.lstrip("/")
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return None
        return candidate

    def _send_body(self, status: int, body: bytes, content_type: str,
                   extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _listing(self, directory: Path, url_path: str) -> bytes:
        entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        rows = []
        if url_path != "/":
            rows.append('<li><a href="../">../</a></li>')
        for entry in entries[:MAX_DIR_ENTRIES]:
            name = entry.name + ("/" if entry.is_dir() else "")
            link = html.escape(name, quote=True)
            size = "" if entry.is_dir() else f"{entry.stat().st_size:,} B"
            rows.append(f'<li><a href="{link}">{html.escape(name)}</a> '
                        f'<span>{size}</span></li>')
        if len(entries) > MAX_DIR_ENTRIES:
            rows.append(f"<li>... {len(entries) - MAX_DIR_ENTRIES} more</li>")
        title = html.escape(f"Index of {url_path}")
        page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}
li{{margin:.25rem 0}} span{{color:#666;font-size:.85em}}</style></head>
<body><h1>{title}</h1><ul>{''.join(rows)}</ul></body></html>"""
        return page.encode("utf-8")

    def do_GET(self) -> None:  # noqa: N802
        target = self._resolve(self.path)
        if target is None:
            self._send_body(400, b"bad path\n", "text/plain; charset=utf-8")
            return
        if not target.exists():
            self._send_body(404, b"not found\n", "text/plain; charset=utf-8")
            return
        if target.is_dir():
            for index in INDEX_FILES:
                candidate = target / index
                if candidate.is_file():
                    self._serve_file(candidate)
                    return
            if not urlsplit(self.path).path.endswith("/"):
                self.send_response(301)
                self.send_header("Location", urlsplit(self.path).path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = self._listing(target, urlsplit(self.path).path)
            self._send_body(200, body, "text/html; charset=utf-8")
            return
        self._serve_file(target)

    def _serve_file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError as exc:
            self._send_body(403, f"cannot read file: {exc}\n".encode(),
                            "text/plain; charset=utf-8")
            return
        ctype, _ = mimetypes.guess_type(path.name)
        if path.suffix.lower() in {".html", ".htm", ".css", ".js", ".json", ".svg"}:
            ctype = (ctype or "text/plain").split(";")[0] + "; charset=utf-8"
        self._send_body(200, data, ctype or "application/octet-stream",
                        {"Cache-Control": "no-cache"})

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)


def make_server(root: Path, host: str, port: int) -> ThreadingHTTPServer:
    root = root.resolve()
    handler = type("BoundStaticHandler", (StaticHandler,), {"root": root})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "hello.txt").write_text("hello static world\n", encoding="utf-8")
        (root / "index.html").write_text("<h1>home</h1>", encoding="utf-8")
        (root / "sub").mkdir()
        (root / "sub" / "page.html").write_text("<p>sub</p>", encoding="utf-8")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args: Any, **kwargs: Any) -> None:
                return None

        opener = urllib.request.build_opener(NoRedirect)
        server = make_server(root, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        failures = 0
        try:
            cases = [
                ("/hello.txt", 200, "hello static world"),
                ("/", 200, "<h1>home</h1>"),
                ("/sub/", 200, "page.html"),
                ("/sub", 301, None),
                ("/missing.txt", 404, "not found"),
                ("/../secret.txt", 400, None),
                ("/%2e%2e/secret.txt", 400, None),
            ]
            for path, expected, needle in cases:
                req = urllib.request.Request(base + path)
                try:
                    with opener.open(req, timeout=5) as resp:
                        status, body = resp.status, resp.read().decode("utf-8", "replace")
                except urllib.error.HTTPError as exc:
                    status, body = exc.code, exc.read().decode("utf-8", "replace")
                ok = status == expected and (needle is None or needle in body)
                failures += 0 if ok else 1
                print(f"[{'PASS' if ok else 'FAIL'}] {path}: {status} (want {expected})")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        print("self-test", "FAILED" if failures else "passed")
        return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Safe static file HTTP server.")
    p.add_argument("root", nargs="?", type=Path, default=Path("."))
    p.add_argument("--bind", default="127.0.0.1", help="interface to bind")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--once", action="store_true", help="run offline self-test and exit")
    args = p.parse_args(argv)

    if args.once:
        return self_test()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2
    try:
        server = make_server(root, args.bind, args.port)
    except OSError as exc:
        print(f"error: cannot bind {args.bind}:{args.port}: {exc}", file=sys.stderr)
        return 1

    host = args.bind if args.bind not in ("0.0.0.0", "::") else socket.gethostname()
    print(f"serving {root} at http://{host}:{server.server_port}/")
    print("press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
