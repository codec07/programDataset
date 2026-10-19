"""Beautiful Soup — practical single-file examples.

Install:  pip install beautifulsoup4 lxml
Run:      python bs4_examples.py

All HTML is embedded, so this file needs no network access. It covers parsing
with different tree builders, searching, CSS selectors, navigation, attribute
access, table extraction, cleanup, and rebuilding HTML.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Library Examples</title>
  <meta name="description" content="A demonstration page">
</head>
<body>
  <header id="top">
    <h1 class="title">Python Libraries</h1>
    <nav>
      <a href="/docs" class="nav-link">Docs</a>
      <a href="/tutorials" class="nav-link active">Tutorials</a>
      <a href="https://example.com/external" class="nav-link external">External</a>
    </nav>
  </header>

  <main>
    <section id="intro" data-level="1">
      <h2>Introduction</h2>
      <p class="lead">Beautiful Soup parses <em>broken</em> HTML and builds a tree.</p>
      <p>It is <strong>not</strong> a browser and does not run JavaScript.</p>
    </section>

    <section id="table">
      <h2>Inventory</h2>
      <table class="data">
        <thead>
          <tr><th>Item</th><th>Qty</th><th>Price</th></tr>
        </thead>
        <tbody>
          <tr class="row"><td>Widget</td><td>4</td><td>2.50</td></tr>
          <tr class="row"><td>Gadget</td><td>2</td><td>9.99</td></tr>
          <tr class="row"><td>Gizmo</td><td>7</td><td>1.25</td></tr>
        </tbody>
      </table>
    </section>

    <section id="links">
      <h2>Links</h2>
      <ul>
        <li><a href="https://python.org">Python</a></li>
        <li><a href="https://pypi.org">PyPI</a></li>
        <li><a href="/local">Local</a></li>
      </ul>
    </section>
  </main>

  <footer>
    <!-- This comment is part of the tree -->
    <p>&copy; 2026 Example</p>
  </footer>
</body>
</html>
"""


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Parsing and tree builders
# ---------------------------------------------------------------------------
def parsing() -> None:
    section("1. Parsing and tree builders")

    # html.parser is the standard-library fallback and always available
    soup = BeautifulSoup(HTML, "html.parser")
    print("title:", soup.title)
    print("title text:", soup.title.string)
    print("doctype:", soup.doctype)

    # lxml is faster but requires the lxml package
    try:
        soup_lxml = BeautifulSoup(HTML, "lxml")
        print("lxml parsed length:", len(str(soup_lxml)))
    except Exception as exc:  # FeatureNotFound included
        print("lxml not available:", type(exc).__name__)

    # Parse a fragment rather than a whole document
    fragment = BeautifulSoup("<p>Hello <b>world</b></p>", "html.parser")
    print("fragment paragraph:", fragment.p)

    # Parse from bytes (encoding is detected or can be declared)
    byte_soup = BeautifulSoup(HTML.encode("utf-8"), "html.parser", from_encoding="utf-8")
    print("byte parsing title:", byte_soup.title.string)

    # Prettify shows the normalized tree
    print("\nprettified header (first 12 lines):")
    for line in soup.header.prettify().splitlines()[:12]:
        print(line)


# ---------------------------------------------------------------------------
# 2. Searching
# ---------------------------------------------------------------------------
def searching() -> None:
    section("2. find, find_all, and filters")

    soup = BeautifulSoup(HTML, "html.parser")

    heading = soup.find("h1")
    print("first h1:", heading.get_text(strip=True))
    print("h1 attributes:", heading.attrs)

    all_links = soup.find_all("a")
    print("\nnumber of links:", len(all_links))
    for link in all_links:
        print(" -", link.get_text(strip=True), "->", link.get("href"))

    # By class, id, and attribute
    print("\nactive link:", soup.find("a", class_="active").get_text(strip=True))
    print("section by id:", soup.find("section", id="intro")["data-level"])
    print("elements with data-level:", len(soup.find_all(attrs={"data-level": True})))

    # String search
    print("\nparagraphs containing 'JavaScript':")
    for paragraph in soup.find_all("p", string=lambda text: text and "JavaScript" in text):
        print(" -", paragraph.get_text(strip=True))

    # Regex search on tag names or text
    import re

    print("\nheadings matching h1/h2:", [tag.name for tag in soup.find_all(re.compile(r"^h[12]$"))])

    # Limit results and search only inside a subtree
    main = soup.find("main")
    print("first two links in main:", [a.get_text(strip=True) for a in main.find_all("a", limit=2)])

    # find_parent / find_next_sibling
    em = soup.find("em")
    print("\nparent of <em>:", em.find_parent().name)
    print("next sibling:", em.next_sibling)


# ---------------------------------------------------------------------------
# 3. CSS selectors
# ---------------------------------------------------------------------------
def selectors() -> None:
    section("3. CSS selectors with select and select_one")

    soup = BeautifulSoup(HTML, "html.parser")

    print("nav links:", [a.get_text(strip=True) for a in soup.select("nav a.nav-link")])
    print("external link:", soup.select_one("a.external")["href"])
    print("direct child:", [li.get_text(strip=True) for li in soup.select("ul > li")])
    print("attribute selector:", [a["href"] for a in soup.select('a[href^="https://"]')])
    print("nth-of-type:", soup.select_one("table tbody tr:nth-of-type(2)").get_text(" ", strip=True))
    print("comma groups:", len(soup.select("h1, h2")))
    print("id selector:", soup.select_one("#intro h2").get_text(strip=True))


# ---------------------------------------------------------------------------
# 4. Navigation
# ---------------------------------------------------------------------------
def navigation() -> None:
    section("4. Tree navigation")

    soup = BeautifulSoup(HTML, "html.parser")
    body = soup.body

    print("body children (tags only):", [child.name for child in body.children if isinstance(child, Tag)])
    print("body descendants count:", len(list(body.descendants)))
    print("header next sibling:", body.header.find_next_sibling().name)

    first_paragraph = soup.find("p")
    print("\nfirst paragraph text:", first_paragraph.get_text(" ", strip=True))
    print("contents:", first_paragraph.contents)
    print("strings:", list(first_paragraph.strings))
    print("stripped strings:", list(first_paragraph.stripped_strings))

    intro = soup.find(id="intro")
    print("\nintro children:", [child.name for child in intro.children if isinstance(child, Tag)])
    print("parent:", intro.parent.name)
    print("previous sibling:", intro.previous_sibling)
    print("next section:", intro.find_next("section")["id"])

    # Walk up the tree
    print("ancestors of h2:", [tag.name for tag in soup.find("h2").parents if isinstance(tag, Tag)])


# ---------------------------------------------------------------------------
# 5. Attributes, text, and comments
# ---------------------------------------------------------------------------
def attributes_and_text() -> None:
    section("5. Attributes, text, and comments")

    soup = BeautifulSoup(HTML, "html.parser")

    link = soup.find("a", class_="external")
    print("href:", link["href"])
    print("get with default:", link.get("target", "_self"))
    print("classes:", link.get("class"))  # multi-valued attributes are lists
    print("all attrs:", link.attrs)

    # Multi-valued class handling
    classes = soup.find("a", class_="active").get("class")
    print("active classes:", classes, "joined:", " ".join(classes))

    # Text extraction: separator controls concatenation
    table = soup.find("table")
    print("\nget_text with spaces:", table.get_text(" ", strip=True)[:100])
    print("get_text with newlines:\n", table.get_text("\n", strip=True)[:160])

    # Comments are Comment nodes, not tags
    comment = soup.find(string=lambda value: isinstance(value, Comment))
    print("\ncomment:", comment)
    print("comment type:", type(comment).__name__)

    # NavigableString behaves like a string but keeps tree context
    title_text = soup.title.string
    print("is NavigableString:", isinstance(title_text, NavigableString))
    print("parent tag:", title_text.parent.name)

    # Safe attribute handling for optional values
    meta = soup.find("meta", attrs={"name": "description"})
    print("description:", meta.get("content") if meta else None)


# ---------------------------------------------------------------------------
# 6. Tables
# ---------------------------------------------------------------------------
def tables() -> None:
    section("6. Extracting tabular data")

    soup = BeautifulSoup(HTML, "html.parser")
    table = soup.find("table", class_="data")

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        rows.append(dict(zip(headers, cells)))

    print("headers:", headers)
    for row in rows:
        print(row)

    total = sum(float(row["Price"]) * int(row["Qty"]) for row in rows)
    print("inventory value:", round(total, 2))

    # rowspan/colspan require manual handling; this table has none
    print("rows with class 'row':", len(table.select("tr.row")))


# ---------------------------------------------------------------------------
# 7. Modifying the tree
# ---------------------------------------------------------------------------
def modification() -> None:
    section("7. Modifying and building HTML")

    soup = BeautifulSoup(HTML, "html.parser")

    # Change text and attributes
    soup.title.string = "Updated Title"
    soup.find("h1")["data-updated"] = "true"
    soup.find("a", class_="external")["href"] = "https://example.org/changed"

    # Add new tags
    footer = soup.find("footer")
    new_paragraph = soup.new_tag("p", attrs={"class": "notice"})
    new_paragraph.string = "Generated by Beautiful Soup examples."
    footer.append(new_paragraph)

    # Insert before/after
    intro = soup.find(id="intro")
    intro.insert_before(soup.new_tag("hr"))
    intro.h2.insert_after(soup.new_tag("span", attrs={"class": "badge"}))
    soup.find("span", class_="badge").string = "new"

    # Remove and decompose
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    soup.find("nav").decompose()

    print("title after edit:", soup.title.string)
    print("h1 attributes:", soup.h1.attrs)
    print("footer paragraphs:", len(footer.find_all("p")))
    print("nav present:", soup.find("nav") is not None)

    print("\nmodified fragment:")
    print(soup.find("header").prettify()[:400])

    # Build a small document from scratch
    fresh = BeautifulSoup("", "html.parser")
    html = fresh.new_tag("html")
    body = fresh.new_tag("body")
    heading = fresh.new_tag("h1")
    heading.string = "Built from scratch"
    body.append(heading)
    html.append(body)
    fresh.append(html)
    print("\nfresh document:\n", fresh.prettify())


# ---------------------------------------------------------------------------
# 8. Robust parsing helpers
# ---------------------------------------------------------------------------
def helpers() -> None:
    section("8. Cleanup and defensive extraction")

    messy = """
    <div class='card'>
      <h3>  Spaced   Title </h3>
      <p>First&nbsp;paragraph<br>with a line break.</p>
      <a href='#'>Read more</a>
      <script>console.log('ignore me')</script>
    </div>
    """
    soup = BeautifulSoup(messy, "html.parser")

    # Remove non-content elements before extracting text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    card = soup.find("div", class_="card")
    print("title:", " ".join(card.h3.get_text(" ", strip=True).split()))
    print("paragraph:", " ".join(card.p.get_text(" ", strip=True).split()))
    print("link text:", card.a.get_text(strip=True))
    print("link href:", card.a.get("href"))

    # Normalize whitespace without breaking words
    def clean_text(node: Tag) -> str:
        return " ".join(node.get_text(" ", strip=True).split())

    print("clean card text:", clean_text(card))

    # Convert relative links with a base
    from urllib.parse import urljoin

    base = "https://example.com/docs/page.html"
    for anchor in soup.find_all("a", href=True):
        print("absolute:", urljoin(base, anchor["href"]))

    # Extract metadata safely
    meta = soup.find("meta", attrs={"name": "description"})
    print("missing meta fallback:", meta["content"] if meta else "n/a")

    # Limit tree size when debugging very large documents
    print("short representation:", str(soup)[:80].replace("\n", " "))


def main() -> None:
    print("Beautiful Soup version:", __import__("bs4").__version__)
    parsing()
    searching()
    selectors()
    navigation()
    attributes_and_text()
    tables()
    modification()
    helpers()

    print("\nAll Beautiful Soup example sections completed.")


if __name__ == "__main__":
    main()
