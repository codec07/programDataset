#!/usr/bin/env python3
"""Print a terminal calendar with ISO week numbers and today highlighted.

Without arguments the current month is shown. `--month` selects a month
in the current (or given) year, and `--year` alone prints a full-year
calendar in three columns. Today is highlighted only when stdout is a
terminal, so piped output stays clean.

Usage:
    python cli_calendar.py
    python cli_calendar.py --month 12
    python cli_calendar.py --month 2 --year 2028
    python cli_calendar.py --year 2026
    python cli_calendar.py --month 10 --weeks --sunday --no-highlight
"""

from __future__ import annotations

import argparse
import calendar
import sys
from datetime import date
from typing import Sequence

WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
HIGHLIGHT = "\033[1;7m"
RESET = "\033[0m"


def month_name(year: int, month: int) -> str:
    """Return 'October 2026'."""
    return f"{calendar.month_name[month]} {year}"


def render_month(
    year: int,
    month: int,
    *,
    first_weekday: int,
    show_weeks: bool,
    highlight: bool,
) -> list[str]:
    """Render one month as a list of fixed-width lines."""
    cal = calendar.Calendar(firstweekday=first_weekday)
    weeks = cal.monthdayscalendar(year, month)
    names = WEEKDAYS[first_weekday:] + WEEKDAYS[:first_weekday]
    prefix_width = 3 if show_weeks else 0
    title = month_name(year, month).center(20 + prefix_width)

    header = ("Wk " if show_weeks else "") + " ".join(f"{name:>2}" for name in names)
    lines = [title, header]
    today = date.today()

    for week in weeks:
        cells: list[str] = []
        for day in week:
            if day == 0:
                cells.append("  ")
            elif highlight and (year, month, day) == (today.year, today.month, today.day):
                cells.append(f"{HIGHLIGHT}{day:2d}{RESET}")
            else:
                cells.append(f"{day:2d}")
        row = " ".join(cells)
        if show_weeks:
            first_day = next((day for day in week if day), 1)
            week_number = date(year, month, first_day).isocalendar().week
            row = f"{week_number:2d} " + row
        lines.append(row)
    return lines


def render_year(year: int, *, first_weekday: int, highlight: bool) -> list[str]:
    """Render a full year as three months per row."""
    lines = [str(year).center(66), ""]
    for quarter_start in (1, 4, 7, 10):
        blocks = [
            render_month(
                year, month,
                first_weekday=first_weekday,
                show_weeks=False,
                highlight=highlight,
            )
            for month in range(quarter_start, quarter_start + 3)
        ]
        height = max(len(block) for block in blocks)
        for index in range(height):
            cells = [
                block[index] if index < len(block) else " " * 20
                for block in blocks
            ]
            lines.append("   ".join(cells).rstrip())
        lines.append("")
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Print a calendar for a month or a whole year.",
        epilog="Today is highlighted only when output goes to a terminal.",
    )
    parser.add_argument("--month", type=int, metavar="1-12",
                        help="month to display (default: current month)")
    parser.add_argument("--year", type=int, metavar="YYYY",
                        help="year to display (default: current year)")
    parser.add_argument("--weeks", action="store_true",
                        help="show ISO week numbers in month view")
    parser.add_argument("--sunday", action="store_true",
                        help="start weeks on Sunday instead of Monday")
    parser.add_argument("--no-highlight", action="store_true",
                        help="do not mark today")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI highlighting even on a terminal")
    args = parser.parse_args(argv)

    args.year_given = args.year is not None
    args.year = args.year if args.year is not None else today.year
    if not 1 <= args.year <= 9999:
        parser.error("--year must be between 1 and 9999")
    if args.month is not None and not 1 <= args.month <= 12:
        parser.error("--month must be between 1 and 12")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    first_weekday = calendar.SUNDAY if args.sunday else calendar.MONDAY
    use_color = (
        not args.no_highlight
        and not args.no_color
        and sys.stdout.isatty()
    )
    today = date.today()

    if args.month is None and args.year_given:
        lines = render_year(args.year, first_weekday=first_weekday, highlight=use_color)
    elif args.month is None:
        lines = render_month(
            today.year, today.month,
            first_weekday=first_weekday,
            show_weeks=args.weeks,
            highlight=use_color,
        )
    else:
        lines = render_month(
            args.year, args.month,
            first_weekday=first_weekday,
            show_weeks=args.weeks,
            highlight=use_color,
        )

    print("\n".join(lines).rstrip())
    if not args.no_highlight:
        print(f"\nToday: {today.isoformat()} (ISO week {today.isocalendar().week})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
