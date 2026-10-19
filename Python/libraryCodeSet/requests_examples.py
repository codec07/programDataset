"""requests — practical single-file examples.

Install:  pip install requests
Run:      python requests_examples.py

Demonstrates sessions, query parameters, headers, JSON/form bodies, timeouts,
retries, streaming downloads, authentication, and error handling.

Most examples call https://httpbin.org, so they need internet access. The
functions are written to fail gracefully and print a clear message when the
network is unavailable.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://httpbin.org"
TIMEOUT = (3.05, 10)  # (connect, read) seconds


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def show_response(response: requests.Response) -> None:
    print("status:", response.status_code, response.reason)
    print("elapsed:", response.elapsed.total_seconds(), "s")
    print("content-type:", response.headers.get("Content-Type"))
    print("encoding:", response.encoding)


# ---------------------------------------------------------------------------
# 1. Basic GET
# ---------------------------------------------------------------------------
def basic_get() -> None:
    section("1. GET with query parameters")

    params = {"q": "python requests", "limit": 3}
    response = requests.get(f"{BASE_URL}/get", params=params, timeout=TIMEOUT)
    show_response(response)
    response.raise_for_status()

    payload = response.json()
    print("final URL:", response.url)
    print("server saw args:", payload.get("args"))
    print("origin:", payload.get("origin"))
    print("user-agent:", payload.get("headers", {}).get("User-Agent"))


# ---------------------------------------------------------------------------
# 2. Headers, sessions, and cookies
# ---------------------------------------------------------------------------
def sessions_and_headers() -> None:
    section("2. Session, custom headers, and cookies")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "programDataset-examples/1.0",
            "Accept": "application/json",
        }
    )

    response = session.get(f"{BASE_URL}/headers", timeout=TIMEOUT)
    response.raise_for_status()
    headers = response.json()["headers"]
    print("User-Agent seen by server:", headers.get("User-Agent"))
    print("Accept seen by server:", headers.get("Accept"))

    # Cookie round-trip
    session.cookies.set("example", "dataset", domain="httpbin.org")
    cookie_response = session.get(f"{BASE_URL}/cookies", timeout=TIMEOUT)
    if cookie_response.ok:
        print("cookies:", cookie_response.json().get("cookies"))

    # Per-request headers override session headers
    override = session.get(
        f"{BASE_URL}/headers", headers={"Accept": "text/plain"}, timeout=TIMEOUT
    )
    print("override Accept:", override.json()["headers"].get("Accept"))

    session.close()


# ---------------------------------------------------------------------------
# 3. POST, PUT, PATCH, DELETE
# ---------------------------------------------------------------------------
def write_methods() -> None:
    section("3. POST / PUT / PATCH / DELETE")

    payload = {"name": "Ada", "role": "engineer", "tags": ["math", "code"]}
    response = requests.post(f"{BASE_URL}/post", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    echoed = response.json()
    print("POST json field:", echoed.get("json"))
    print("POST content-type:", echoed.get("headers", {}).get("Content-Type"))

    # Form-encoded body
    form = requests.post(
        f"{BASE_URL}/post", data={"username": "ada", "password": "secret"}, timeout=TIMEOUT
    )
    print("\nform field:", form.json().get("form"))

    put = requests.put(f"{BASE_URL}/put", json={"id": 1, "active": True}, timeout=TIMEOUT)
    print("\nPUT status:", put.status_code, "json:", put.json().get("json"))

    patch = requests.patch(f"{BASE_URL}/patch", data={"note": "updated"}, timeout=TIMEOUT)
    print("PATCH status:", patch.status_code)

    delete = requests.delete(f"{BASE_URL}/delete", timeout=TIMEOUT)
    print("DELETE status:", delete.status_code)


# ---------------------------------------------------------------------------
# 4. Status codes and errors
# ---------------------------------------------------------------------------
def errors() -> None:
    section("4. HTTP errors, timeouts, and connection errors")

    response = requests.get(f"{BASE_URL}/status/404", timeout=TIMEOUT)
    print("404 status:", response.status_code)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        print("raise_for_status ->", type(exc).__name__, exc)

    # A 500 also raises, but is not retried by default
    server_error = requests.get(f"{BASE_URL}/status/500", timeout=TIMEOUT)
    print("\n500 status:", server_error.status_code, "ok:", server_error.ok)

    # Timeout
    try:
        requests.get(f"{BASE_URL}/delay/5", timeout=1.0)
    except requests.Timeout as exc:
        print("\ntimeout caught:", type(exc).__name__)

    # Connection failure (invalid host)
    try:
        requests.get("https://no-such-host.invalid", timeout=TIMEOUT)
    except requests.ConnectionError as exc:
        print("connection error caught:", type(exc).__name__)

    # Never index JSON blindly; inspect the content type and status first
    print("\ncontent-type check:", response.headers.get("Content-Type"))


# ---------------------------------------------------------------------------
# 5. Retries with backoff
# ---------------------------------------------------------------------------
def retries() -> None:
    section("5. Retries with exponential backoff")

    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_policy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # /status/200 is stable; /status/503 would be retried.
    response = session.get(f"{BASE_URL}/status/200", timeout=TIMEOUT)
    print("status with retry adapter:", response.status_code)
    print("retry policy total:", retry_policy.total)

    session.close()


# ---------------------------------------------------------------------------
# 6. Streaming downloads
# ---------------------------------------------------------------------------
def streaming() -> None:
    section("6. Streaming responses and file downloads")

    output = Path(__file__).resolve().parent / "output"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "httpbin_bytes.bin"

    with requests.get(f"{BASE_URL}/bytes/4096", stream=True, timeout=TIMEOUT) as response:
        response.raise_for_status()
        expected = int(response.headers.get("Content-Length", 0))
        written = 0
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)

    print("content-length:", expected)
    print("bytes written:", written)
    print("file size:", destination.stat().st_size)
    print("saved:", destination)

    # Streaming JSON lines (httpbin returns a single JSON object)
    with requests.get(f"{BASE_URL}/stream/3", stream=True, timeout=TIMEOUT) as response:
        for index, line in enumerate(response.iter_lines(decode_unicode=True)):
            if line:
                print(f"line {index}: {line[:80]}")
            if index >= 4:
                break


# ---------------------------------------------------------------------------
# 7. Authentication and redirects
# ---------------------------------------------------------------------------
def auth_and_redirects() -> None:
    section("7. Basic auth, redirects, and proxies")

    response = requests.get(
        f"{BASE_URL}/basic-auth/ada/secret", auth=("ada", "secret"), timeout=TIMEOUT
    )
    print("basic auth status:", response.status_code)
    if response.ok:
        print("authenticated:", response.json().get("authenticated"))

    # Redirect control
    followed = requests.get(f"{BASE_URL}/redirect/2", timeout=TIMEOUT)
    print("\nfollowed redirects:", len(followed.history), "final status:", followed.status_code)

    not_followed = requests.get(
        f"{BASE_URL}/redirect/2", allow_redirects=False, timeout=TIMEOUT
    )
    print("not followed status:", not_followed.status_code)
    print("location:", not_followed.headers.get("Location"))

    # Proxies are configured per request or per session:
    # proxies = {"https": "http://user:pass@proxy.example:8080"}
    # requests.get(url, proxies=proxies, timeout=TIMEOUT)
    print("proxy configuration shown in comments")


# ---------------------------------------------------------------------------
# 8. Offline fallback
# ---------------------------------------------------------------------------
def offline_check() -> bool:
    try:
        response = requests.get(f"{BASE_URL}/get", timeout=(2, 4))
        return response.ok
    except requests.RequestException as exc:
        print("network unavailable:", type(exc).__name__)
        return False


def main() -> None:
    print("requests version:", requests.__version__)
    print("timeout policy:", TIMEOUT)

    if not offline_check():
        print("\nSkipping live examples: no connection to httpbin.org.")
        print("The code above still shows the intended request patterns.")
        return

    basic_get()
    sessions_and_headers()
    write_methods()
    errors()
    retries()
    streaming()
    auth_and_redirects()

    print("\nAll requests example sections completed.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"\nNetwork error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
