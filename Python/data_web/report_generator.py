"""Generate a self-contained HTML or Markdown report from CSV or JSON data.

Produces a summary of every numeric column (count, sum, mean, min, max,
median, population standard deviation) plus a preview table of the first
rows, all in one file with inline CSS.

Usage:
    python report_generator.py data.csv --title "Q3 Sales" --out report.html
    python report_generator.py data.json --format md --out report.md
    python report_generator.py data.csv --preview 12 --force
    python report_generator.py --demo
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

CSS = """
:root { color-scheme: light; }
body { font-family: Segoe UI, Helvetica, Arial, sans-serif; margin: 0 auto;
       max-width: 960px; padding: 32px; color: #111827; background: #f8fafc; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 18px; margin-top: 32px; border-bottom: 1px solid #e5e7eb;
     padding-bottom: 6px; }
.meta { color: #6b7280; font-size: 13px; margin-bottom: 24px; }
table { border-collapse: collapse; width: 100%; background: #fff;
        font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
th, td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; }
th { background: #f1f5f9; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
footer { margin-top: 32px; color: #9ca3af; font-size: 12px; }
"""


def load_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data = data.get("rows") or data.get("records") or data.get("data")
        if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
            raise ValueError("JSON must be a list of objects")
        return [dict(row) for row in data]
    if suffix in (".csv", ".txt", ".tsv"):
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row")
            return [{k.strip(): (v or "") for k, v in row.items() if k} for row in reader]
    raise ValueError(f"unsupported input type: {suffix or '(none)'}")


def to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def numeric_columns(records: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for key in records[0].keys():
        sample = [to_number(row.get(key)) for row in records]
        filled = [v for v in sample if v is not None]
        if filled and len(filled) >= max(1, len(records) // 2):
            columns.append(key)
    return columns


def summarize(records: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    summary = []
    for column in columns:
        values = [v for v in (to_number(row.get(column)) for row in records)
                  if v is not None]
        if not values:
            continue
        summary.append({
            "column": column,
            "count": len(values),
            "sum": sum(values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        })
    return summary


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9 and abs(value) < 1e15:
        return f"{int(round(value)):,}"
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def render_html(title: str, source: str, records: list[dict[str, Any]],
                summary: list[dict[str, Any]], preview: int) -> str:
    headers = list(records[0].keys()) if records else []
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        f"<style>{CSS}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
        f'<p class="meta">Source: {html.escape(source)} &middot; '
        f"{len(records)} row(s) &middot; {len(headers)} column(s) &middot; "
        f"generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
    ]
    if summary:
        parts.append("<h2>Numeric summary</h2><table><tr><th>column</th>"
                     "<th class='num'>count</th><th class='num'>sum</th>"
                     "<th class='num'>mean</th><th class='num'>median</th>"
                     "<th class='num'>min</th><th class='num'>max</th>"
                     "<th class='num'>stdev</th></tr>")
        for row in summary:
            parts.append(
                f"<tr><td>{html.escape(str(row['column']))}</td>"
                f"<td class='num'>{row['count']}</td>"
                f"<td class='num'>{fmt(row['sum'])}</td>"
                f"<td class='num'>{fmt(row['mean'])}</td>"
                f"<td class='num'>{fmt(row['median'])}</td>"
                f"<td class='num'>{fmt(row['min'])}</td>"
                f"<td class='num'>{fmt(row['max'])}</td>"
                f"<td class='num'>{fmt(row['stdev'])}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<h2>Numeric summary</h2><p>No numeric columns detected.</p>")

    if headers and records:
        parts.append(f"<h2>Preview (first {min(preview, len(records))} rows)</h2><table><tr>")
        numeric = {row["column"] for row in summary}
        for header in headers:
            cls = " class='num'" if header in numeric else ""
            parts.append(f"<th{cls}>{html.escape(str(header))}</th>")
        parts.append("</tr>")
        for record in records[:preview]:
            parts.append("<tr>")
            for header in headers:
                value = record.get(header, "")
                cls = " class='num'" if header in numeric else ""
                number = to_number(value) if header in numeric else None
                cell = fmt(number) if number is not None else html.escape(str(value))
                parts.append(f"<td{cls}>{cell}</td>")
            parts.append("</tr>")
        parts.append("</table>")
    parts.append("<footer>Generated by report_generator.py (standard library only)."
                 "</footer></body></html>")
    return "\n".join(parts) + "\n"


def render_markdown(title: str, source: str, records: list[dict[str, Any]],
                    summary: list[dict[str, Any]], preview: int) -> str:
    lines = [f"# {title}", "",
             f"*Source: `{source}` | {len(records)} rows | "
             f"generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]
    if summary:
        lines += ["## Numeric summary", "",
                  "| column | count | sum | mean | median | min | max | stdev |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for row in summary:
            lines.append(
                f"| {row['column']} | {row['count']} | {fmt(row['sum'])} | "
                f"{fmt(row['mean'])} | {fmt(row['median'])} | {fmt(row['min'])} | "
                f"{fmt(row['max'])} | {fmt(row['stdev'])} |")
        lines.append("")
    headers = list(records[0].keys()) if records else []
    if headers:
        lines += [f"## Preview (first {min(preview, len(records))} rows)", "",
                  "| " + " | ".join(str(h) for h in headers) + " |",
                  "|" + "---|" * len(headers)]
        for record in records[:preview]:
            cells = [str(record.get(h, "")).replace("|", "\\|") for h in headers]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        csv_path = root / "data.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["region", "orders", "revenue"])
            writer.writerows([
                ("north", 120, 5400.50), ("south", 98, 4210.00),
                ("east", 143, 6890.25), ("west", 87, 3120.75),
                ("central", 110, 5005.00),
            ])
        records = load_records(csv_path)
        summary = summarize(records, numeric_columns(records))
        html_text = render_html("Demo Report", str(csv_path), records, summary, 3)
        md_text = render_markdown("Demo Report", str(csv_path), records, summary, 3)
        (root / "report.html").write_text(html_text, encoding="utf-8", newline="\n")
        (root / "report.md").write_text(md_text, encoding="utf-8", newline="\n")
        print(f"rows: {len(records)}, numeric columns: "
              f"{', '.join(row['column'] for row in summary)}")
        print(f"html: {len(html_text)} chars, markdown: {len(md_text)} chars")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="HTML/Markdown report generator.")
    p.add_argument("input", nargs="?", type=Path, help="CSV/TSV or JSON file")
    p.add_argument("--title")
    p.add_argument("--format", choices=("html", "md"), default=None)
    p.add_argument("--out", type=Path)
    p.add_argument("--preview", type=int, default=8)
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    if not args.input or not args.input.is_file():
        print("error: input file not found (or use --demo)", file=sys.stderr)
        return 2
    if args.format:
        fmt_name = args.format
    elif args.out and args.out.suffix.lower() in (".md", ".markdown"):
        fmt_name = "md"
    else:
        fmt_name = "html"
    out = args.out or args.input.with_name(f"{args.input.stem}_report."
                                           f"{'md' if fmt_name == 'md' else 'html'}")
    if out.exists() and not args.force:
        print(f"error: {out} exists (use --force)", file=sys.stderr)
        return 2

    try:
        records = load_records(args.input)
        if not records:
            print("error: no records found", file=sys.stderr)
            return 1
        summary = summarize(records, numeric_columns(records))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    title = args.title or f"Report - {args.input.name}"
    preview = max(1, args.preview)
    text = (render_markdown(title, str(args.input), records, summary, preview)
            if fmt_name == "md"
            else render_html(title, str(args.input), records, summary, preview))
    try:
        out.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"error: cannot write {out}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {out} ({len(records)} rows, {len(summary)} numeric column(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
