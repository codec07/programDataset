"""A polite, dependency-free web scraper built on urllib and html.parser.

Extracts the title, meta description, headings, visible text and links from a
page, optionally following same-host links up to a depth limit.  It checks
robots.txt, waits between requests, caps page count, and sets a timeout.

Offline use (no network required):
    python web_scraper.py --offline page.html
    python web_scraper.py --demo
Online use:
    python web_scraper.py --url https://example.com --depth 1 --max-pages 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "polite-scraper/1.0 (+educational; contact: example@example.com)"
TIMEOUT = 8.0
SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".zip",
            ".mp4", ".mp3", ".ico", ".woff", ".woff2")

DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Demo Page - Local HTML</title>
  <meta name="description" content="A tiny page used to test the scraper offline.">
</head>
<body>
  <h1>Offline scraping demo</h1>
  <p>This page never touches the network.</p>
  <p>It has <b>bold</b> text and a <a href="/about.html">relative link</a>,
     plus an <a href="https://example.org/outer">external link</a>.</p>
  <h2>Second heading</h2>
  <ul><li>alpha</li><li>beta</li></ul>
</body>
</html>
"""


class PageParser(HTMLParser):
    """Collect title, metadata, headings, paragraphs and links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.headings: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.paragraphs: list[str] = []
        self._stack: list[str] = []
        self._buffer: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1
            return
        if tag == "meta":
            name = attributes.get("name", "").lower()
            if name == "description" and not self.description:
                self.description = attributes.get("content", "").strip()
        elif tag == "a":
            href = attributes.get("href", "").strip()
            if href and not href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
                self.links.append(href)
        elif tag in ("title", "h1", "h2", "h3", "p", "li"):
            self._stack.append(tag)
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if not self._stack or self._stack[-1] != tag:
            return
        text = " ".join("".join(self._buffer).split())
        if text:
            if tag == "title":
                self.title = text
            elif tag in ("h1", "h2", "h3"):
                self.headings.append((tag, text))
            elif tag == "p":
                self.paragraphs.append(text)
        self._stack.pop()
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._stack:
            self._buffer.append(data)


def parse_html(markup: str, base_url: str = "") -> dict[str, Any]:
    parser = PageParser()
    parser.feed(markup)
    parser.close()
    links = []
    for href in parser.links:
        absolute = urllib.parse.urljoin(base_url, href) if base_url else href
        links.append(absolute)
    return {
        "url": base_url,
        "title": parser.title,
        "description": parser.description,
        "headings": [{"tag": tag, "text": text} for tag, text in parser.headings],
        "paragraphs": parser.paragraphs,
        "links": links,
    }


def fetch(url: str, timeout: float = TIMEOUT, retries: int = 2) -> str:
    """Fetch a URL as text with a small retry loop."""
    last: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if "html" not in ctype and ctype:
                    raise ValueError(f"not an HTML response: {ctype}")
                raw = resp.read(2_000_000)
                charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise ConnectionError(f"could not fetch {url}: {last}")


def robots_allows(base: str, path: str) -> bool:
    """Very small robots.txt check for the wildcard user-agent group."""
    parsed = urllib.parse.urlsplit(base)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        text = fetch(robots_url, timeout=5, retries=1)
    except (ConnectionError, ValueError):
        return True  # no robots.txt -> allow
    applies = False
    disallowed: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            applies = value == "*"
        elif key == "disallow" and applies and value:
            disallowed.append(value)
    return not any(path.startswith(rule) for rule in disallowed)


def crawl(start: str, max_depth: int, max_pages: int, delay: float,
          respect_robots: bool) -> list[dict[str, Any]]:
    host = urllib.parse.urlsplit(start).netloc
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []

    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        clean = urllib.parse.urldefrag(url)[0]
        if clean in seen:
            continue
        seen.add(clean)
        path = urllib.parse.urlsplit(clean).path or "/"
        if respect_robots and not robots_allows(clean, path):
            print(f"skipped by robots.txt: {clean}", file=sys.stderr)
            continue
        try:
            markup = fetch(clean)
        except (ConnectionError, ValueError) as exc:
            print(f"skip {clean}: {exc}", file=sys.stderr)
            continue
        page = parse_html(markup, clean)
        page["depth"] = depth
        pages.append(page)
        if depth < max_depth:
            for link in page["links"]:
                parts = urllib.parse.urlsplit(link)
                if parts.scheme not in ("http", "https") or parts.netloc != host:
                    continue
                if parts.path.lower().endswith(SKIP_EXT):
                    continue
                if link not in seen:
                    queue.append((link, depth + 1))
        if delay and queue:
            time.sleep(delay)
    return pages


def summarize(pages: list[dict[str, Any]]) -> None:
    for page in pages:
        print(f"\nURL   : {page['url']}")
        print(f"Title : {page['title'] or '(none)'}")
        if page["description"]:
            print(f"Desc  : {page['description']}")
        if page["headings"]:
            print("Heads : " + " | ".join(h["text"][:50] for h in page["headings"][:5]))
        text = " ".join(page["paragraphs"])
        print(f"Text  : {text[:240]}{'...' if len(text) > 240 else ''}")
        print(f"Links : {len(page['links'])}")
    print(f"\n{len(pages)} page(s) scraped")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Polite stdlib web scraper.")
    p.add_argument("--url", help="start URL")
    p.add_argument("--offline", type=Path, help="parse a local HTML file instead")
    p.add_argument("--depth", type=int, default=0, help="follow links this deep")
    p.add_argument("--max-pages", type=int, default=5)
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--no-robots", action="store_true", help="skip robots.txt checks")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--output", type=Path, help="write JSON to a file")
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true", help="parse bundled HTML offline")
    args = p.parse_args(argv)

    if args.output and args.output.exists() and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    try:
        if args.demo:
            pages = [parse_html(DEMO_HTML, "https://demo.local/index.html")]
            pages[0]["depth"] = 0
        elif args.offline:
            if not args.offline.is_file():
                print(f"error: file not found: {args.offline}", file=sys.stderr)
                return 2
            markup = args.offline.read_text(encoding="utf-8", errors="replace")
            pages = [parse_html(markup, args.offline.resolve().as_uri())]
            pages[0]["depth"] = 0
        elif args.url:
            if not args.url.startswith(("http://", "https://")):
                print("error: URL must start with http:// or https://", file=sys.stderr)
                return 2
            pages = crawl(args.url, max(0, args.depth), max(1, args.max_pages),
                          max(0.0, args.delay), not args.no_robots)
        else:
            print("error: provide --url, --offline FILE or --demo", file=sys.stderr)
            return 2
    except (ConnectionError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json or args.output:
        payload = json.dumps({"pages": pages}, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {len(pages)} page(s) -> {args.output}")
        else:
            print(payload)
    else:
        summarize(pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
