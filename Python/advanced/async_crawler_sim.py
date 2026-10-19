"""Simulate an asynchronous web crawler with no network access.

A fake site provides HTML pages and deterministic latencies. The crawler uses
a fixed number of worker tasks, an ``asyncio.Queue`` frontier, URL deduplication,
depth and page limits, and per-page error capture. Everything runs offline.

Usage:
    python async_crawler_sim.py
    python async_crawler_sim.py --workers 2 --max-pages 8 --max-depth 1
    python async_crawler_sim.py --workers 6 --max-pages 30

The run terminates on its own and prints all fetched paths, errors, queue
high-water mark, and peak concurrency.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Sequence
from urllib.parse import urljoin, urlparse

LINK_RE = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)


class FetchError(RuntimeError):
    """Raised by the fake site for missing or temporarily failing pages."""


def normalize_url(url: str, base: str = "/") -> str:
    """Reduce a URL to a root-relative path and drop fragments/queries."""
    absolute = urljoin(base, url)
    path = urlparse(absolute).path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return path


def extract_links(html: str, base: str) -> list[str]:
    """Extract and normalize unique href targets from HTML."""
    seen: set[str] = set()
    links: list[str] = []
    for match in LINK_RE.findall(html):
        link = normalize_url(match, base)
        if link not in seen:
            seen.add(link)
            links.append(link)
    return links


def build_fake_site() -> dict[str, str]:
    """Return a small interconnected site with a duplicate and a dead link."""
    return {
        "/": """
            <h1>Async Crawler Test Site</h1>
            <a href="/docs">Docs</a>
            <a href="/about">About</a>
            <a href="/docs">Docs again (duplicate)</a>
            <a href="/missing">Broken link</a>
            <a href="/flaky">Flaky endpoint</a>
            <a href="/deep">Deep section</a>
        """,
        "/docs": """
            <h1>Documentation</h1>
            <a href="/docs/intro">Intro</a>
            <a href="/docs/api">API</a>
            <a href="/">Home</a>
            <a href="/docs/intro#install">Intro anchor</a>
        """,
        "/docs/intro": """
            <h1>Introduction</h1>
            <a href="../about">About</a>
            <a href="/docs/api">API</a>
        """,
        "/docs/api": """
            <h1>API Reference</h1>
            <a href="/docs/intro">Back to intro</a>
            <a href="/deep">Deep</a>
        """,
        "/about": """
            <h1>About</h1>
            <a href="/contact">Contact</a>
            <a href="/">Home</a>
        """,
        "/contact": """
            <h1>Contact</h1>
            <a href="/about">About</a>
        """,
        "/deep": """
            <h1>Deep</h1>
            <a href="/deep/one">One</a>
            <a href="/deep/two">Two</a>
        """,
        "/deep/one": '<h1>Deep one</h1><a href="/deep/two">Two</a>',
        "/deep/two": '<h1>Deep two</h1><a href="/">Home</a>',
        "/flaky": '<h1>Flaky</h1><a href="/missing">Another bad link</a>',
    }


class FakeWeb:
    """A delay-injecting fake HTTP client."""

    def __init__(
        self,
        pages: dict[str, str] | None = None,
        *,
        transient_failures: dict[str, int] | None = None,
    ) -> None:
        self.pages = pages if pages is not None else build_fake_site()
        self.transient_failures = dict(transient_failures or {})
        self.requests = 0
        self._lock = asyncio.Lock()

    async def fetch(self, url: str) -> str:
        path = normalize_url(url)
        async with self._lock:
            self.requests += 1
        # Deterministic latency: different path lengths finish out of order.
        await asyncio.sleep(0.004 + (len(path) % 5) * 0.003)
        remaining = self.transient_failures.get(path, 0)
        if remaining > 0:
            self.transient_failures[path] = remaining - 1
            raise FetchError("temporary upstream failure (503)")
        if path not in self.pages:
            raise FetchError("page not found (404)")
        return self.pages[path]


@dataclass(slots=True)
class CrawlStats:
    fetched: int = 0
    duplicates: int = 0
    limit_skips: int = 0
    errors: dict[str, str] = field(default_factory=dict)
    pages: list[str] = field(default_factory=list)
    max_concurrency: int = 0
    queue_peak: int = 0
    elapsed: float = 0.0


class Crawler:
    """Breadth-first crawler driven by a fixed pool of worker tasks."""

    def __init__(
        self,
        fetcher: Callable[[str], Awaitable[str]],
        *,
        workers: int = 4,
        max_pages: int = 20,
        max_depth: int = 2,
    ) -> None:
        if min(workers, max_pages) < 1:
            raise ValueError("workers and max_pages must be positive")
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        self.fetcher = fetcher
        self.workers = workers
        self.max_pages = max_pages
        self.max_depth = max_depth
        # Unbounded on purpose: every worker may be busy parsing links at the
        # same time, so a bounded queue could deadlock with all workers blocked
        # on put(). Concurrency is limited by the worker count, not queue size.
        self.queue: asyncio.Queue[tuple[str, int] | None] = asyncio.Queue()
        self.seen: set[str] = set()
        self.active = 0
        self.stats = CrawlStats()

    async def _enqueue(self, url: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False
        url = normalize_url(url)
        if url in self.seen:
            self.stats.duplicates += 1
            return False
        if len(self.seen) >= self.max_pages:
            self.stats.limit_skips += 1
            return False
        self.seen.add(url)
        await self.queue.put((url, depth))
        self.stats.queue_peak = max(self.stats.queue_peak, self.queue.qsize())
        return True

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            try:
                if item is None:
                    return
                url, depth = item
                self.active += 1
                self.stats.max_concurrency = max(self.stats.max_concurrency, self.active)
                try:
                    body = await self.fetcher(url)
                    self.stats.fetched += 1
                    self.stats.pages.append(url)
                    if depth < self.max_depth:
                        for link in extract_links(body, url):
                            await self._enqueue(link, depth + 1)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.stats.errors[url] = f"{type(exc).__name__}: {exc}"
                finally:
                    self.active -= 1
            finally:
                self.queue.task_done()

    async def crawl(self, seeds: Sequence[str]) -> CrawlStats:
        """Crawl from seed paths until the queue drains or limits are hit."""
        started = time.perf_counter()
        for seed in seeds:
            await self._enqueue(seed, 0)
        if not self.seen:
            self.stats.elapsed = time.perf_counter() - started
            return self.stats
        workers = [asyncio.create_task(self._worker()) for _ in range(self.workers)]
        try:
            await self.queue.join()
            for _ in workers:
                await self.queue.put(None)
            await asyncio.gather(*workers)
        except BaseException:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            raise
        self.stats.elapsed = time.perf_counter() - started
        return self.stats


async def _demo(workers: int, max_pages: int, max_depth: int) -> None:
    site = FakeWeb(transient_failures={"/flaky": 1})
    crawler = Crawler(
        site.fetch, workers=workers, max_pages=max_pages, max_depth=max_depth
    )
    stats = await crawler.crawl(["/"])
    print(
        f"fetched={stats.fetched}, duplicates={stats.duplicates}, "
        f"limit_skips={stats.limit_skips}, errors={len(stats.errors)}, "
        f"queue_peak={stats.queue_peak}, max_concurrency={stats.max_concurrency}, "
        f"elapsed={stats.elapsed:.3f}s"
    )
    print("pages:", ", ".join(stats.pages))
    if stats.errors:
        print("errors:")
        for url, message in stats.errors.items():
            print(f"  {url}: {message}")
    assert stats.max_concurrency <= workers, "concurrency limit was violated"
    assert len(set(stats.pages)) == len(stats.pages), "a page was fetched twice"
    print(f"fake HTTP requests: {site.requests}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline async crawler simulation.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.workers < 1 or args.max_pages < 1 or args.max_depth < 0:
        parser.error("workers/max-pages must be positive and max-depth non-negative")

    async def run() -> None:
        await asyncio.wait_for(
            _demo(args.workers, args.max_pages, args.max_depth), timeout=args.timeout
        )

    try:
        asyncio.run(run())
    except TimeoutError:
        parser.error(f"crawler did not finish within {args.timeout:g}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
