"""Track a stock/crypto portfolio: holdings, cost basis, P&L and allocation.

Prices are read from a small JSON file ({"AAPL": 190.2, ...}) so the tool
works fully offline; nothing is fetched from the network.  Holdings live in
SQLite with parameterised statements.

Usage:
    python portfolio_tracker.py --db portfolio.db buy AAPL 10 150.00
    python portfolio_tracker.py --db portfolio.db buy BTC 0.5 30000 --kind crypto
    python portfolio_tracker.py --db portfolio.db list
    python portfolio_tracker.py --db portfolio.db report --prices prices.json
    python portfolio_tracker.py --db portfolio.db sell AAPL 4 --price 190
    python portfolio_tracker.py --demo
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS lots (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol    TEXT NOT NULL,
    kind      TEXT NOT NULL DEFAULT 'stock',
    quantity  REAL NOT NULL CHECK (quantity > 0),
    cost      REAL NOT NULL CHECK (cost >= 0),
    bought_on TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lots_symbol ON lots(symbol);
"""


@contextmanager
def connect(db: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db, timeout=10.0)
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


def buy(db: Path, symbol: str, qty: float, cost: float, kind: str, day: str) -> None:
    with connect(db) as conn:
        conn.execute(
            "INSERT INTO lots (symbol, kind, quantity, cost, bought_on) "
            "VALUES (?, ?, ?, ?, ?)",
            (symbol.upper(), kind, qty, cost, day),
        )
    print(f"bought {qty:g} {symbol.upper()} at {cost:.2f}")


def sell(db: Path, symbol: str, qty: float, price: float | None,
         day: str) -> None:
    """Reduce holdings FIFO; realised P&L uses the supplied sale price."""
    symbol = symbol.upper()
    with connect(db) as conn:
        lots = conn.execute(
            "SELECT id, quantity, cost FROM lots WHERE symbol = ? ORDER BY bought_on, id",
            (symbol,),
        ).fetchall()
        available = sum(row["quantity"] for row in lots)
        if qty > available + 1e-9:
            raise ValueError(f"cannot sell {qty:g} {symbol}; only {available:g} held")
        remaining = qty
        realised = 0.0
        for lot in lots:
            if remaining <= 1e-9:
                break
            take = min(remaining, lot["quantity"])
            if price is not None:
                realised += take * (price - lot["cost"])
            if take >= lot["quantity"] - 1e-9:
                conn.execute("DELETE FROM lots WHERE id = ?", (lot["id"],))
            else:
                conn.execute("UPDATE lots SET quantity = quantity - ? WHERE id = ?",
                             (take, lot["id"]))
            remaining -= take
    print(f"sold {qty:g} {symbol}" +
          (f", realised P&L {realised:+.2f}" if price is not None else ""))


def load_prices(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read prices file {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("prices file must contain a JSON object")
    prices: dict[str, float] = {}
    for key, value in raw.items():
        try:
            price = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"price for {key!r} is not a number") from exc
        if price < 0:
            raise ValueError(f"price for {key!r} is negative")
        prices[str(key).upper()] = price
    return prices


def aggregate(rows: list[sqlite3.Row]) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}
    for row in rows:
        entry = table.setdefault(row["symbol"], {"qty": 0.0, "cost": 0.0})
        entry["qty"] += row["quantity"]
        entry["cost"] += row["quantity"] * row["cost"]
    return table


def show(db: Path, prices: dict[str, float]) -> None:
    with connect(db) as conn:
        rows = conn.execute("SELECT symbol, quantity, cost FROM lots").fetchall()
    table = aggregate(rows)
    if not table:
        print("portfolio is empty")
        return
    total_value = 0.0
    total_cost = 0.0
    print(f"{'symbol':<8} {'qty':>10} {'avg cost':>10} {'price':>10} "
          f"{'value':>12} {'P&L':>12}")
    print("-" * 68)
    valued = 0.0
    for symbol in sorted(table):
        entry = table[symbol]
        qty = entry["qty"]
        avg = entry["cost"] / qty if qty else 0.0
        price = prices.get(symbol)
        total_cost += entry["cost"]
        if price is None:
            print(f"{symbol:<8} {qty:>10.4g} {avg:>10.2f} {'?':>10} {'?':>12} {'?':>12}")
            continue
        value = qty * price
        pnl = value - entry["cost"]
        total_value += value
        valued += value
        print(f"{symbol:<8} {qty:>10.4g} {avg:>10.2f} {price:>10.2f} "
              f"{value:>12.2f} {pnl:>+12.2f}")
    print("-" * 68)
    if valued:
        print(f"total value {total_value:.2f}  cost {total_cost:.2f}  "
              f"P&L {total_value - total_cost:+.2f}")
        print("\nallocation:")
        for symbol in sorted(table):
            price = prices.get(symbol)
            if price is None:
                continue
            value = table[symbol]["qty"] * price
            share = value / total_value * 100 if total_value else 0
            bar = "#" * int(round(share / 2))
            print(f"  {symbol:<8} {share:>5.1f}%  {bar}")
    missing = [s for s in table if s not in prices]
    if missing:
        print(f"no price for: {', '.join(missing)}")


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "portfolio.db"
        buy(db, "AAPL", 10, 150.0, "stock", "2025-04-01")
        buy(db, "AAPL", 5, 180.0, "stock", "2026-01-15")
        buy(db, "MSFT", 3, 310.0, "stock", "2025-11-20")
        buy(db, "BTC", 0.25, 30000.0, "crypto", "2025-06-05")
        sell(db, "AAPL", 4, 195.0, "2026-09-01")
        prices_path = Path(tmp) / "prices.json"
        prices_path.write_text(
            json.dumps({"AAPL": 190.0, "MSFT": 420.0, "BTC": 61000.0}),
            encoding="utf-8",
        )
        print()
        show(db, load_prices(prices_path))
    return 0


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--prices", type=Path, default=argparse.SUPPRESS,
                        help="JSON file of current prices")

    p = argparse.ArgumentParser(description="Offline portfolio tracker.",
                                parents=[common])
    p.add_argument("--demo", action="store_true", help="run an offline demonstration")
    sub = p.add_subparsers(dest="command")

    b = sub.add_parser("buy", help="add a purchase lot", parents=[common])
    b.add_argument("symbol")
    b.add_argument("quantity", type=float)
    b.add_argument("cost", type=float, help="price per unit")
    b.add_argument("--kind", choices=("stock", "crypto", "etf", "fund"), default="stock")
    b.add_argument("--date", default=None)

    s = sub.add_parser("sell", help="sell units (FIFO)", parents=[common])
    s.add_argument("symbol")
    s.add_argument("quantity", type=float)
    s.add_argument("--price", type=float, help="sale price per unit")
    s.add_argument("--date", default=None)

    sub.add_parser("list", help="show holdings", parents=[common])
    sub.add_parser("report", help="show holdings with valuation", parents=[common])

    args = p.parse_args(argv, argparse.Namespace(db=Path("portfolio.db"), prices=None))
    if args.demo:
        return demo()
    if not args.command:
        p.print_help()
        return 0

    from datetime import date

    day = getattr(args, "date", None) or date.today().isoformat()
    try:
        if args.command == "buy":
            if args.quantity <= 0 or args.cost < 0:
                print("error: quantity must be positive, cost non-negative",
                      file=sys.stderr)
                return 2
            buy(args.db, args.symbol, args.quantity, args.cost, args.kind, day)
        elif args.command == "sell":
            if args.quantity <= 0:
                print("error: quantity must be positive", file=sys.stderr)
                return 2
            sell(args.db, args.symbol, args.quantity, args.price, day)
        elif args.command in ("list", "report"):
            prices = load_prices(args.prices) if args.prices else {}
            show(args.db, prices)
    except (sqlite3.Error, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
