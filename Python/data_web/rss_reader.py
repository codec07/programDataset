"""Read RSS 2.0 and Atom feeds with xml.etree, offline or over HTTP.

Features:
  * parses both RSS (``<item>``) and Atom (``<entry>``) documents
  * resolves relative links, strips a small set of HTML tags from summaries
  * HTTP fetch with timeout and retries; ``--file``/``--demo`` need no network
  * table or JSON output, keyword filtering and a result limit

Usage:
    python rss_reader.py --file feed.xml
    python rss_reader.py --url https://example.com/feed.xml --limit 5
    python rss_reader.py --demo --json
    python rss_reader.py --file feed.xml --grep python --limit 3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

USER_AGENT = "rss-reader/1.0 (educational sample)"
TIMEOUT = 8.0
TAG_RE = re.compile(r"<[^>]+>")

DEMO_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Demo Feed</title>
    <link>https://demo.local/</link>
    <description>Sample feed shipped with the program</description>
    <item>
      <title>Python 3.13 released</title>
      <link>https://demo.local/python-313</link>
      <pubDate>Mon, 19 Oct 2026 09:00:00 GMT</pubDate>
      <description>A &lt;p&gt;new&lt;/p&gt; interpreter release.</description>
    </item>
    <item>
      <title>SQLite tips</title>
      <link>https://demo.local/sqlite-tips</link>
      <pubDate>Sun, 18 Oct 2026 12:30:00 GMT</pubDate>
      <description>Use parameterised queries.</description>
    </item>
  </channel>
</rss>
"""

DEMO_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Demo Atom</title>
  <link href="https://demo.local/atom"/>
  <entry>
    <title>Atom entry</title>
    <link href="/atom/1"/>
    <updated>2026-10-19T10:00:00Z</updated>
    <summary>Namespaced parsing works too.</summary>
  </entry>
</feed>
"""


@dataclass
class Entry:
    title: str
    link: str
    published: str
    summary: str


def clean_text(value: str | None, limit: int = 300) -> str:
    if not value:
        return ""
    text = " ".join(TAG_RE.sub(" ", value).split())
    return text[:limit] + ("..." if len(text) > limit else "")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, *names: str) -> str:
    for child in element:
        if local_name(child.tag) in names:
            return (child.text or "").strip()
    return ""


def child_link(element: ET.Element) -> str:
    """Find a link, preferring Atom's rel=alternate / href form."""
    fallback = ""
    for child in element:
        if local_name(child.tag) != "link":
            continue
        href = child.get("href")
        if href:
            rel = (child.get("rel") or "alternate").lower()
            if rel == "alternate":
                return href
            fallback = fallback or href
        elif (child.text or "").strip():
            fallback = fallback or child.text.strip()
    return fallback


def parse_feed(xml_text: str) -> tuple[str, list[Entry]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"invalid XML: {exc}") from exc

    channel_title = ""
    if local_name(root.tag) == "rss":
        for child in root:
            if local_name(child.tag) == "channel":
                channel_title = child_text(child, "title")
                break
    else:
        channel_title = child_text(root, "title")
    entries: list[Entry] = []
    for element in root.iter():
        name = local_name(element.tag)
        if name not in ("item", "entry"):
            continue
        title = child_text(element, "title") or "(untitled)"
        published = child_text(element, "pubdate", "published", "updated", "date")
        summary = child_text(element, "description", "summary", "content")
        entries.append(Entry(title=title, link=child_link(element),
                             published=published, summary=clean_text(summary)))
    return channel_title, entries


def fetch(url: str, retries: int = 2) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
                return resp.read(5_000_000).decode(
                    resp.headers.get_content_charset() or "utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    raise ConnectionError(f"could not fetch {url}: {last}")


def render_table(channel: str, entries: list[Entry]) -> str:
    lines = [f"Feed: {channel or '(untitled)'}  ({len(entries)} entries)", ""]
    for idx, entry in enumerate(entries, 1):
        lines.append(f"{idx:>2}. {entry.title}")
        if entry.published:
            lines.append(f"    {entry.published}")
        if entry.link:
            lines.append(f"    {entry.link}")
        if entry.summary:
            lines.append(f"    {entry.summary[:160]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RSS/Atom feed reader.")
    p.add_argument("--url", help="feed URL (http/https)")
    p.add_argument("--file", type=Path, help="local XML file")
    p.add_argument("--demo", action="store_true", help="use bundled sample feeds")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--grep", help="only keep entries containing this text")
    p.add_argument("--json", action="store_true")
    p.add_argument("--output", type=Path, help="write JSON to a file")
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    if args.output and args.output.exists() and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    try:
        if args.demo:
            channel, entries = parse_feed(DEMO_RSS)
            atom_channel, atom_entries = parse_feed(DEMO_ATOM)
            channel = f"{channel} + {atom_channel}"
            entries.extend(atom_entries)
        elif args.file:
            if not args.file.is_file():
                print(f"error: file not found: {args.file}", file=sys.stderr)
                return 2
            channel, entries = parse_feed(args.file.read_text(encoding="utf-8"))
        elif args.url:
            if not args.url.startswith(("http://", "https://")):
                print("error: URL must start with http:// or https://", file=sys.stderr)
                return 2
            channel, entries = parse_feed(fetch(args.url))
        else:
            print("error: provide --url, --file or --demo", file=sys.stderr)
            return 2
    except (ValueError, ConnectionError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.grep:
        needle = args.grep.lower()
        entries = [e for e in entries
                   if needle in e.title.lower() or needle in e.summary.lower()]
    entries = entries[:max(1, args.limit)]

    if args.json or args.output:
        payload = json.dumps({"feed": channel,
                              "entries": [asdict(e) for e in entries]},
                             indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8", newline="\n")
            print(f"wrote {len(entries)} entries -> {args.output}")
        else:
            print(payload)
    else:
        print(render_table(channel, entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
