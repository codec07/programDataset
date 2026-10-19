"""Threaded JSON CRUD API for a task list, using only the standard library.

Endpoints:
    GET    /health                 service + database status
    GET    /api/tasks              list tasks (optional ?done=true|false)
    POST   /api/tasks              create  {"title": "...", "done": false}
    GET    /api/tasks/<id>         fetch one
    PUT    /api/tasks/<id>         replace title/done
    PATCH  /api/tasks/<id>         partially update
    DELETE /api/tasks/<id>         remove (204)

Usage:
    python rest_api_server.py --port 8000 --db tasks.db
    python rest_api_server.py --once        # start, self-test, shut down

The server is threaded; each request uses its own short-lived SQLite
connection with parameterised statements.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

MAX_BODY = 64 * 1024


@contextmanager
def db_connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    with db_connect(db_path):
        pass


def validate_payload(payload: Any, *, partial: bool) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    allowed = {"title", "done"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
    out: dict[str, Any] = {}
    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if len(title.strip()) > 200:
            raise ValueError("title must be at most 200 characters")
        out["title"] = title.strip()
    elif not partial:
        raise ValueError("title is required")
    if "done" in payload:
        if not isinstance(payload["done"], bool):
            raise ValueError("done must be a boolean")
        out["done"] = int(payload["done"])
    if partial and not out:
        raise ValueError("no updatable fields supplied")
    return out


class TaskHandler(BaseHTTPRequestHandler):
    server_version = "TaskAPI/1.0"
    db_path: Path = Path("tasks.db")  # replaced on the server instance

    # ---------- helpers ----------
    def _send(self, status: int, payload: Any = None,
              headers: dict[str, str] | None = None) -> None:
        body = b"" if payload is None else json.dumps(
            payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _error(self, status: int, message: str,
               headers: dict[str, str] | None = None) -> None:
        self._send(status, {"error": message}, headers)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("request body is empty")
        if length > MAX_BODY:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if ctype and ctype != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid JSON: {exc}") from exc

    def _task_id(self) -> int | None:
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "tasks":
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)

    # ---------- verbs ----------
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/health":
            try:
                with db_connect(self.db_path) as conn:
                    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                self._send(200, {"status": "ok", "tasks": count})
            except sqlite3.Error as exc:
                self._send(500, {"status": "error", "error": str(exc)})
            return

        if path == "/api/tasks":
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            sql = "SELECT id, title, done, created_at FROM tasks"
            params: list[Any] = []
            for part in query.split("&") if query else []:
                key, _, value = part.partition("=")
                if key == "done":
                    if value.lower() not in ("true", "false", "1", "0"):
                        self._error(400, "done filter must be true or false")
                        return
                    sql += " WHERE done = ?"
                    params.append(1 if value.lower() in ("true", "1") else 0)
            sql += " ORDER BY id"
            with db_connect(self.db_path) as conn:
                rows = conn.execute(sql, params).fetchall()
            self._send(200, {"tasks": [dict(r) for r in rows]})
            return

        task_id = self._task_id()
        if task_id is not None:
            with db_connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
                    (task_id,)).fetchone()
            if row is None:
                self._error(404, f"task {task_id} not found")
            else:
                self._send(200, dict(row))
            return

        self._error(404, "unknown endpoint")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/api/tasks":
            self._error(404, "unknown endpoint")
            return
        try:
            fields = validate_payload(self._read_json(), partial=False)
        except ValueError as exc:
            self._error(400, str(exc))
            return
        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                (fields["title"], fields.get("done", 0)))
            task_id = int(cur.lastrowid or 0)
            row = conn.execute(
                "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
                (task_id,)).fetchone()
        self._send(201, dict(row), {"Location": f"/api/tasks/{task_id}"})

    def _update(self, partial: bool) -> None:
        task_id = self._task_id()
        if task_id is None:
            self._error(404, "unknown endpoint")
            return
        try:
            fields = validate_payload(self._read_json(), partial=partial)
        except ValueError as exc:
            self._error(400, str(exc))
            return
        assignments = ", ".join(f"{col} = ?" for col in fields)
        params = [*fields.values(), task_id]
        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                f"UPDATE tasks SET {assignments} WHERE id = ?", params)
            if cur.rowcount == 0:
                self._error(404, f"task {task_id} not found")
                return
            row = conn.execute(
                "SELECT id, title, done, created_at FROM tasks WHERE id = ?",
                (task_id,)).fetchone()
        self._send(200, dict(row))

    def do_PUT(self) -> None:  # noqa: N802
        self._update(partial=False)

    def do_PATCH(self) -> None:  # noqa: N802
        self._update(partial=True)

    def do_DELETE(self) -> None:  # noqa: N802
        task_id = self._task_id()
        if task_id is None:
            self._error(404, "unknown endpoint")
            return
        with db_connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            self._error(404, f"task {task_id} not found")
        else:
            self._send(204)

    def _method_not_allowed(self) -> None:
        self._error(405, "method not allowed",
                    {"Allow": "GET, POST, PUT, PATCH, DELETE"})

    do_HEAD = _method_not_allowed


def make_server(host: str, port: int, db_path: Path) -> ThreadingHTTPServer:
    handler = type("BoundTaskHandler", (TaskHandler,), {"db_path": db_path})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def self_test(db_path: Path) -> int:
    """Start the server on an ephemeral port, exercise CRUD, then stop."""
    server = make_server("127.0.0.1", 0, db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    failures = 0

    def call(method: str, path: str, payload: Any = None) -> tuple[int, Any]:
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return exc.code, json.loads(raw) if raw else None

    try:
        checks = [
            ("health", call("GET", "/health"), 200),
            ("create", call("POST", "/api/tasks", {"title": "write tests"}), 201),
            ("create 2", call("POST", "/api/tasks", {"title": "ship", "done": True}), 201),
            ("list", call("GET", "/api/tasks"), 200),
            ("patch", call("PATCH", "/api/tasks/1", {"done": True}), 200),
            ("get", call("GET", "/api/tasks/1"), 200),
            ("delete", call("DELETE", "/api/tasks/2"), 204),
            ("missing", call("GET", "/api/tasks/999"), 404),
            ("invalid", call("POST", "/api/tasks", {"title": ""}), 400),
            ("unknown field", call("POST", "/api/tasks", {"nope": 1}), 400),
        ]
        for label, (status, payload), expected in checks:
            ok = status == expected
            failures += 0 if ok else 1
            extra = "" if payload is None else f" {payload}"
            print(f"[{'PASS' if ok else 'FAIL'}] {label}: {status} (want {expected}){extra}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("self-test", "FAILED" if failures else "passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Threaded JSON CRUD task API.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--db", type=Path, default=Path("tasks.db"))
    p.add_argument("--once", action="store_true",
                   help="start on an ephemeral port, run self-tests, exit")
    args = p.parse_args(argv)

    try:
        if args.once:
            with tempfile.TemporaryDirectory() as tmp:
                return self_test(Path(tmp) / "selftest.db")
        init_db(args.db)
        server = make_server(args.host, args.port, args.db)
    except OSError as exc:
        print(f"error: cannot start server: {exc}", file=sys.stderr)
        return 1

    print(f"serving on http://{args.host}:{server.server_port} (db={args.db})")
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
