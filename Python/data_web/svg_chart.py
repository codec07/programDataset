"""Generate a standalone SVG bar or line chart from CSV data (no matplotlib).

Reads two columns (category/label and numeric value), scales them into a
viewport with axes, gridlines, value labels and a title, then writes a
complete SVG file that opens in any browser.

Usage:
    python svg_chart.py sales.csv --x month --y revenue --out revenue.svg
    python svg_chart.py sales.csv --x month --y revenue --type line --title "Revenue"
    python svg_chart.py data.csv --x name --y score --width 900 --height 420
    python svg_chart.py --demo
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import tempfile
from pathlib import Path

PALETTE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed"]
FONT = "Segoe UI, Helvetica, Arial, sans-serif"


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def load_series(path: Path, x_col: str | None, y_col: str | None
                ) -> tuple[list[str], list[float], str, str]:
    # utf-8-sig transparently strips the BOM that Excel prepends to CSV exports.
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        fields = [f.strip() for f in reader.fieldnames]
        x_name = x_col or fields[0]
        numeric = [f for f in fields if f != x_name]
        if y_col:
            y_name = y_col
        elif numeric:
            y_name = numeric[-1]
        else:
            raise ValueError("CSV needs at least two columns")
        if x_name not in fields or y_name not in fields:
            raise ValueError(f"columns not found; available: {', '.join(fields)}")

        labels: list[str] = []
        values: list[float] = []
        for line_no, row in enumerate(reader, start=2):
            raw = (row.get(y_name) or "").strip().replace(",", "")
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"line {line_no}: {y_name}={raw!r} is not numeric") from exc
            if math.isnan(value) or math.isinf(value):
                raise ValueError(f"line {line_no}: non-finite value")
            labels.append((row.get(x_name) or "").strip() or f"row {line_no}")
            values.append(value)
    if not labels:
        raise ValueError("no data rows found")
    return labels, values, x_name, y_name


def nice_ticks(max_value: float, count: int = 5) -> tuple[float, list[float]]:
    """Return (axis_max, tick values) with rounded steps."""
    if max_value <= 0:
        return 1.0, [0.0, 1.0]
    raw_step = max_value / count
    magnitude = 10 ** math.floor(math.log10(raw_step))
    for multiplier in (1, 2, 2.5, 5, 10):
        step = magnitude * multiplier
        if step >= raw_step:
            break
    axis_max = math.ceil(max_value / step) * step
    ticks = [i * step for i in range(int(round(axis_max / step)) + 1)]
    return axis_max, ticks


def fmt_number(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def build_svg(labels: list[str], values: list[float], *, chart_type: str,
              title: str, x_name: str, y_name: str,
              width: int, height: int) -> str:
    left, right, top, bottom = 70, 30, 60, 80
    plot_w = max(50, width - left - right)
    plot_h = max(50, height - top - bottom)

    vmin = min(0.0, min(values))
    vmax = max(0.0, max(values))
    axis_max, ticks = nice_ticks(vmax)
    if vmin < 0:
        axis_min, neg_ticks = nice_ticks(-vmin)
        axis_min = -axis_min
    else:
        axis_min, neg_ticks = 0.0, []
    span = axis_max - axis_min or 1.0

    def y_pos(value: float) -> float:
        return top + plot_h - (value - axis_min) / span * plot_h

    def x_pos(index: int) -> float:
        if len(values) == 1:
            return left + plot_w / 2
        return left + (index + 0.5) * plot_w / len(values)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{left}" y="30" font-family="{FONT}" font-size="20" '
        f'font-weight="600" fill="#111827">{esc(title)}</text>',
    ]

    # Gridlines and y-axis labels.
    all_ticks = sorted(set(ticks + neg_ticks))
    for tick in all_ticks:
        y = y_pos(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" '
                     f'y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                     f'font-family="{FONT}" font-size="11" fill="#6b7280">'
                     f'{fmt_number(tick)}</text>')
    parts.append(f'<line x1="{left}" y1="{y_pos(0):.1f}" x2="{left + plot_w}" '
                 f'y2="{y_pos(0):.1f}" stroke="#9ca3af" stroke-width="1.5"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" '
                 f'stroke="#9ca3af" stroke-width="1.5"/>')

    if chart_type == "bar":
        slot = plot_w / len(values)
        bar_w = max(2.0, min(64.0, slot * 0.62))
        for index, value in enumerate(values):
            x = x_pos(index) - bar_w / 2
            y = y_pos(max(value, 0))
            bar_h = abs(y_pos(value) - y_pos(0))
            color = PALETTE[index % len(PALETTE)] if len(values) <= 12 else PALETTE[0]
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                         f'height="{max(bar_h, 0.5):.1f}" fill="{color}" rx="2"/>')
            parts.append(f'<text x="{x_pos(index):.1f}" y="{y - 5:.1f}" '
                         f'text-anchor="middle" font-family="{FONT}" font-size="10" '
                         f'fill="#374151">{fmt_number(value)}</text>')
    else:
        points = " ".join(f"{x_pos(i):.1f},{y_pos(v):.1f}"
                          for i, v in enumerate(values))
        area = (f"{left},{y_pos(0):.1f} {points} "
                f"{left + plot_w},{y_pos(0):.1f}")
        parts.append(f'<polygon points="{area}" fill="{PALETTE[0]}" opacity="0.10"/>')
        parts.append(f'<polyline points="{points}" fill="none" stroke="{PALETTE[0]}" '
                     f'stroke-width="2.5" stroke-linejoin="round"/>')
        for index, value in enumerate(values):
            parts.append(f'<circle cx="{x_pos(index):.1f}" cy="{y_pos(value):.1f}" '
                         f'r="3.5" fill="#ffffff" stroke="{PALETTE[0]}" '
                         f'stroke-width="2"/>')
            if len(values) <= 16:
                parts.append(f'<text x="{x_pos(index):.1f}" y="{y_pos(value) - 9:.1f}" '
                             f'text-anchor="middle" font-family="{FONT}" font-size="9" '
                             f'fill="#374151">{fmt_number(value)}</text>')

    # X labels, skipped when they would collide.
    stride = max(1, math.ceil(len(values) / max(1, plot_w // 55)))
    for index, label in enumerate(labels):
        if index % stride and index != len(labels) - 1:
            continue
        display = label if len(label) <= 12 else label[:11] + "."
        parts.append(f'<text x="{x_pos(index):.1f}" y="{top + plot_h + 20}" '
                     f'text-anchor="middle" font-family="{FONT}" font-size="11" '
                     f'fill="#4b5563">{esc(display)}</text>')

    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 16}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="12" fill="#374151">{esc(x_name)}</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="12" fill="#374151" '
                 f'transform="rotate(-90 18 {top + plot_h / 2})">{esc(y_name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def demo() -> int:
    rows = [("Jan", 120), ("Feb", 185), ("Mar", 143), ("Apr", 210),
            ("May", 265), ("Jun", 240)]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "sales.csv"
        with data.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["month", "revenue"])
            writer.writerows(rows)
        labels, values, x_name, y_name = load_series(data, None, None)
        for chart in ("bar", "line"):
            svg = build_svg(labels, values, chart_type=chart,
                            title=f"Demo {chart} chart", x_name=x_name,
                            y_name=y_name, width=720, height=380)
            out = root / f"{chart}.svg"
            out.write_text(svg, encoding="utf-8", newline="\n")
            print(f"{chart}: {out.stat().st_size} bytes, "
                  f"{svg.count('<')} elements")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render a CSV column as an SVG chart.")
    p.add_argument("csv_file", nargs="?", type=Path)
    p.add_argument("--x", help="label column (default: first column)")
    p.add_argument("--y", help="numeric column (default: last column)")
    p.add_argument("--type", choices=("bar", "line"), default="bar")
    p.add_argument("--title", default="")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=450)
    p.add_argument("--out", type=Path, help="output SVG path")
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    if not args.csv_file or not args.csv_file.is_file():
        print("error: CSV file not found (or use --demo)", file=sys.stderr)
        return 2
    out = args.out or args.csv_file.with_suffix(".svg")
    if out.exists() and not args.force:
        print(f"error: {out} exists (use --force)", file=sys.stderr)
        return 2

    try:
        labels, values, x_name, y_name = load_series(args.csv_file, args.x, args.y)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    svg = build_svg(labels, values, chart_type=args.type,
                    title=args.title or f"{y_name} by {x_name}",
                    x_name=x_name, y_name=y_name,
                    width=max(320, args.width), height=max(240, args.height))
    try:
        out.write_text(svg, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"error: cannot write {out}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {out} ({len(values)} points, {out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
