"""A small, robust HTTP client built on urllib with retries and backoff.

Supports arbitrary methods, request headers, JSON or form bodies, response
headers, output to a file, and retries with exponential backoff for transient
failures (connection errors, timeouts and 5xx responses).

Usage:
    python http_client.py https://example.com
    python http_client.py https://httpbin.org/post -X POST -d '{"a": 1}' --json
    python http_client.py URL --header "Authorization: Bearer TOKEN" --timeout 10
    python http_client.py URL --retries 4 --output body.txt --include-headers
    python http_client.py --demo        # spins up a local server, no internet
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

USER_AGENT = "http-client/1.0 (educational sample)"
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class Response:
    def __init__(self, status: int, reason: str, headers: dict[str, str], body: bytes,
                 url: str, elapsed: float) -> None:
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body
        self.url = url
        self.elapsed = elapsed

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())


def parse_headers(pairs: list[str]) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    for pair in pairs:
        if ":" not in pair:
            raise ValueError(f"bad header {pair!r}; expected 'Name: value'")
        name, value = pair.split(":", 1)
        if not name.strip():
            raise ValueError(f"bad header {pair!r}; empty name")
        headers[name.strip()] = value.strip()
    return headers


def request(url: str, method: str = "GET", headers: dict[str, str] | None = None,
            body: bytes | None = None, timeout: float = 10.0,
            retries: int = 3, backoff: float = 1.0) -> Response:
    """Perform an HTTP request, retrying transient failures."""
    headers = dict(headers or {"User-Agent": USER_AGENT})
    attempts = max(1, retries)
    last_error: Exception | None = None

    for attempt in range(attempts):
        started = time.monotonic()
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read()
                elapsed = time.monotonic() - started
                return Response(resp.status, resp.reason or "",
                                dict(resp.headers.items()), payload, resp.geturl(),
                                elapsed)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            elapsed = time.monotonic() - started
            response = Response(exc.code, exc.reason or "",
                                dict(exc.headers.items()) if exc.headers else {},
                                payload, url, elapsed)
            if exc.code not in RETRY_STATUS or attempt == attempts - 1:
                return response
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
        delay = backoff * (2 ** attempt)
        print(f"transient failure ({last_error}); retrying in {delay:.1f}s",
              file=sys.stderr)
        time.sleep(delay)

    raise ConnectionError(f"{method} {url} failed after {attempts} attempts: {last_error}")


def demo() -> int:
    """Run a local HTTP server and exercise the client entirely offline."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/flaky":
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b"try again")
                return
            payload = json.dumps({"path": self.path, "method": "GET"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            data = self.rfile.read(length)
            payload = json.dumps({"received": data.decode("utf-8", "replace")}).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: Any) -> None:  # silence stderr noise
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        first = request(base + "/hello", timeout=5, retries=2)
        print(f"GET {first.status} {first.json()} in {first.elapsed * 1000:.0f} ms")
        second = request(base + "/echo", method="POST", body=b"ping",
                         headers={"Content-Type": "text/plain"}, timeout=5)
        print(f"POST {second.status} {second.json()}")
        third = request(base + "/flaky", timeout=5, retries=2, backoff=0.05)
        print(f"GET flaky -> {third.status} ({third.text()})")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Robust urllib-based HTTP client.")
    p.add_argument("url", nargs="?", help="request URL")
    p.add_argument("-X", "--method", default="GET", help="HTTP method (default GET)")
    p.add_argument("-H", "--header", action="append", default=[], metavar="NAME: VALUE")
    p.add_argument("-d", "--data", help="request body")
    p.add_argument("--json", action="store_true", help="send/parse JSON")
    p.add_argument("--form", action="store_true", help="URL-encode data as a form")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("-o", "--output", type=Path, help="write body to this file")
    p.add_argument("--force", action="store_true", help="overwrite output file")
    p.add_argument("--include-headers", action="store_true")
    p.add_argument("--demo", action="store_true", help="run a local offline demo")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    if not args.url:
        print("error: URL is required (or use --demo)", file=sys.stderr)
        return 2
    if args.output and args.output.exists() and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    try:
        headers = parse_headers(args.header)
        body: bytes | None = None
        if args.data is not None:
            if args.json:
                headers.setdefault("Content-Type", "application/json")
                # Validate before sending so local mistakes fail fast.
                json.loads(args.data)
                body = args.data.encode("utf-8")
            elif args.form:
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                body = urllib.parse.urlencode(
                    {"q": args.data} if "=" not in args.data else
                    dict(pair.split("=", 1) for pair in args.data.split("&"))
                ).encode("utf-8")
            else:
                body = args.data.encode("utf-8")
        if args.method.upper() in {"POST", "PUT", "PATCH"} and body is None:
            body = b""

        response = request(args.url, args.method.upper(), headers, body,
                           timeout=max(1.0, args.timeout),
                           retries=max(1, args.retries))
    except (ValueError, ConnectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.include_headers:
        print(f"HTTP {response.status} {response.reason}")
        for name, value in response.headers.items():
            print(f"{name}: {value}")
        print()

    if args.output:
        args.output.write_bytes(response.body)
        print(f"saved {len(response.body)} bytes -> {args.output}")
    else:
        text = response.text()
        if args.json:
            try:
                print(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(text)
        else:
            print(text, end="" if text.endswith("\n") else "\n")
        print(f"[{response.status} {response.reason}] {response.elapsed * 1000:.0f} ms"
              f" {len(response.body)} bytes", file=sys.stderr)

    return 0 if 200 <= response.status < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
