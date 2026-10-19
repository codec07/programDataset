"""pandas — practical single-file examples.

Install:  pip install pandas
Run:      python pandas_examples.py

Covers Series/DataFrame construction, indexing, cleaning, transformation,
grouping, merging, reshaping, time series, and file I/O. All sample data is
embedded, so no downloads are required.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Series and DataFrame basics
# ---------------------------------------------------------------------------
def construction() -> None:
    section("1. Series and DataFrame construction")

    s = pd.Series([10, 20, 30, 40], index=["a", "b", "c", "d"], name="score")
    print("Series:\n", s)
    print("values:", s.values, "index:", list(s.index), "dtype:", s.dtype)

    # From a dictionary: keys become columns
    df = pd.DataFrame(
        {
            "name": ["Ada", "Linus", "Grace", "Alan"],
            "team": ["math", "kernel", "compiler", "math"],
            "age": [36, 54, 45, 41],
            "salary": [120_000, 150_000, 135_000, 125_000],
        }
    )
    print("\nDataFrame:\n", df)
    print("\nshape:", df.shape)
    print("columns:", list(df.columns))
    print("dtypes:\n", df.dtypes)

    # From records (list of dicts)
    records = pd.DataFrame.from_records(
        [{"x": 1, "y": 2}, {"x": 3, "y": 4}], index=["r1", "r2"]
    )
    print("\nfrom_records:\n", records)

    # Explicit index and columns
    custom = pd.DataFrame(
        [[1, 2], [3, 4]],
        index=pd.Index(["row1", "row2"], name="row"),
        columns=["left", "right"],
    )
    print("\ncustom frame:\n", custom)

    print("\nsummary statistics:\n", df.describe(include="all").T)


# ---------------------------------------------------------------------------
# 2. Selecting data
# ---------------------------------------------------------------------------
def selection() -> None:
    section("2. Selecting rows and columns")

    df = pd.DataFrame(
        {
            "name": ["Ada", "Linus", "Grace", "Alan", "Margaret"],
            "team": ["math", "kernel", "compiler", "math", "compiler"],
            "age": [36, 54, 45, 41, 32],
            "salary": [120_000, 150_000, 135_000, 125_000, 140_000],
        },
        index=[101, 102, 103, 104, 105],
    )

    print("single column (Series):\n", df["name"])
    print("\nmultiple columns (DataFrame):\n", df[["name", "salary"]])
    print("\n.iloc row 0:\n", df.iloc[0])
    print("\n.iloc rows 0:2, cols 0:2:\n", df.iloc[0:2, 0:2])
    print("\n.loc label 103:\n", df.loc[103])
    print("\n.loc label slice:\n", df.loc[102:104, ["name", "team"]])

    mask = (df["team"] == "math") & (df["age"] > 35)
    print("\nboolean mask result:\n", df[mask])

    print("\nquery() equivalent:\n", df.query("team == 'compiler' and salary >= 135000"))
    print("\nisin teams:\n", df[df["team"].isin(["kernel", "compiler"])])

    # at/iat are scalar fast paths
    print("\nat[101, 'name']:", df.at[101, "name"])
    print("iat[0, 0]:", df.iat[0, 0])

    # Setting values
    edited = df.copy()
    edited.loc[edited["team"] == "kernel", "salary"] *= 1.10
    print("\nafter 10% kernel raise:\n", edited[["name", "salary"]])


# ---------------------------------------------------------------------------
# 3. Missing data and cleaning
# ---------------------------------------------------------------------------
def cleaning() -> None:
    section("3. Missing data and cleaning")

    raw = pd.DataFrame(
        {
            "city": ["Paris", "London", None, "Berlin", "Paris", "London"],
            "temperature": [18.0, np.nan, 21.0, 19.0, np.nan, 17.0],
            "humidity": [60, 65, np.nan, 70, 62, 68],
        }
    )
    print("raw:\n", raw)
    print("\nisna():\n", raw.isna())
    print("\nmissing per column:\n", raw.isna().sum())

    print("\ndrop rows with any missing:\n", raw.dropna())
    print("\ndrop rows where temperature missing:\n", raw.dropna(subset=["temperature"]))

    filled = raw.copy()
    filled["city"] = filled["city"].fillna("Unknown")
    filled["temperature"] = filled["temperature"].fillna(filled["temperature"].mean())
    filled["humidity"] = filled["humidity"].ffill()
    print("\nfilled:\n", filled)

    # Duplicates
    dupes = pd.concat([filled, filled.iloc[[0]]], ignore_index=True)
    print("\nduplicate rows:", dupes.duplicated().sum())
    print("after drop_duplicates:", len(dupes.drop_duplicates()))

    # String cleanup
    names = pd.Series(["  Ada Lovelace ", "LINUS TORVALDS", "grace hopper"])
    print("\nstripped/title:", names.str.strip().str.title().tolist())

    # Replace sentinel values
    print("\nreplace -999 with NaN:\n", pd.Series([1, -999, 3]).replace(-999, np.nan))


# ---------------------------------------------------------------------------
# 4. Transformation
# ---------------------------------------------------------------------------
def transformation() -> None:
    section("4. Creating and transforming columns")

    df = pd.DataFrame(
        {
            "employee": ["Ada", "Linus", "Grace", "Alan"],
            "department": ["R&D", "Kernel", "R&D", "Math"],
            "salary": [120_000, 150_000, 135_000, 125_000],
            "start_date": ["2019-03-01", "2012-07-15", "2017-11-20", "2021-01-05"],
        }
    )

    df["start_date"] = pd.to_datetime(df["start_date"])
    df["years"] = (pd.Timestamp("2026-10-19") - df["start_date"]).dt.days / 365.25
    df["salary_k"] = df["salary"] / 1000
    df["senior"] = np.where(df["years"] >= 8, "yes", "no")

    print(df)

    # map for lookup tables
    bonus_rates = {"R&D": 0.15, "Kernel": 0.10, "Math": 0.08}
    df["bonus"] = df["department"].map(bonus_rates).fillna(0.05) * df["salary"]
    print("\nwith bonus:\n", df[["employee", "department", "bonus"]])

    # apply for row-wise logic (use vectorized ops when possible)
    df["level"] = df.apply(
        lambda row: "staff" if row["salary"] < 130_000 else "senior", axis=1
    )
    print("\nlevels:", df["level"].tolist())

    # assign returns a new frame; useful for chaining
    result = (
        df.assign(monthly=lambda d: d["salary"] / 12)
        .sort_values("salary", ascending=False)
        .head(3)
    )
    print("\nchained assign/sort/head:\n", result[["employee", "monthly"]])

    # cut and qcut for bucketing
    df["salary_band"] = pd.cut(
        df["salary"], bins=[0, 125_000, 140_000, 200_000], labels=["low", "mid", "high"]
    )
    print("\nsalary bands:\n", df[["employee", "salary_band"]])


# ---------------------------------------------------------------------------
# 5. Grouping and aggregation
# ---------------------------------------------------------------------------
def grouping() -> None:
    section("5. GroupBy, aggregation, and transform")

    sales = pd.DataFrame(
        {
            "region": ["North", "North", "South", "South", "East", "East", "East"],
            "product": ["A", "B", "A", "B", "A", "B", "C"],
            "units": [10, 5, 8, 12, 15, 7, 3],
            "price": [100.0, 250.0, 100.0, 250.0, 100.0, 250.0, 400.0],
        }
    )
    sales["revenue"] = sales["units"] * sales["price"]
    print(sales)

    print("\nrevenue by region:\n", sales.groupby("region")["revenue"].sum())

    print("\nmultiple aggregations:\n", sales.groupby("region")["revenue"].agg(["sum", "mean", "count"]))

    # Named aggregation produces tidy column names
    summary = sales.groupby(["region", "product"], as_index=False).agg(
        total_units=("units", "sum"),
        total_revenue=("revenue", "sum"),
        avg_price=("price", "mean"),
    )
    print("\nnamed aggregation:\n", summary)

    # transform keeps the original row count
    sales["region_share"] = sales["revenue"] / sales.groupby("region")["revenue"].transform("sum")
    print("\nregion share:\n", sales[["region", "product", "region_share"]])

    # filter groups by a condition
    big_regions = sales.groupby("region").filter(lambda g: g["revenue"].sum() > 2000)
    print("\nregions over 2000:\n", big_regions)

    print("\nsize per region:\n", sales.groupby("region").size())
    print("\nnunique products per region:\n", sales.groupby("region")["product"].nunique())


# ---------------------------------------------------------------------------
# 6. Merging, joining, concatenating
# ---------------------------------------------------------------------------
def combining() -> None:
    section("6. Merge, join, and concat")

    customers = pd.DataFrame(
        {"customer_id": [1, 2, 3, 4], "name": ["Ada", "Linus", "Grace", "Alan"]}
    )
    orders = pd.DataFrame(
        {
            "order_id": [10, 11, 12, 13, 14],
            "customer_id": [1, 1, 3, 5, 2],
            "amount": [250.0, 75.0, 400.0, 50.0, 125.0],
        }
    )

    print("inner merge:\n", customers.merge(orders, on="customer_id", how="inner"))
    print("\nleft merge:\n", customers.merge(orders, on="customer_id", how="left"))
    print("\nouter merge (missing marked):\n", customers.merge(orders, on="customer_id", how="outer"))

    # Indicator tells you where each row came from
    merged = customers.merge(orders, on="customer_id", how="left", indicator=True)
    print("\nmerge indicator counts:\n", merged["_merge"].value_counts())

    left = pd.DataFrame({"id": [1, 2, 3], "a": ["x", "y", "z"]}).set_index("id")
    right = pd.DataFrame({"id": [2, 3, 4], "b": [20, 30, 40]}).set_index("id")
    print("\nDataFrame.join (index-based):\n", left.join(right, how="left"))

    q1 = pd.DataFrame({"product": ["A", "B"], "q1": [100, 200]})
    q2 = pd.DataFrame({"product": ["A", "B"], "q2": [110, 190]})
    print("\nconcat columns:\n", pd.concat([q1, q2], axis=1))
    print("\nconcat rows:\n", pd.concat([q1, q2], ignore_index=True))

    # Validate merge cardinality to catch duplicate keys early
    try:
        customers.merge(orders, on="customer_id", validate="one_to_one")
    except pd.errors.MergeError as exc:
        print("\nmerge validation caught:", exc)


# ---------------------------------------------------------------------------
# 7. Reshaping
# ---------------------------------------------------------------------------
def reshaping() -> None:
    section("7. Pivot, melt, and crosstab")

    long = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
            "city": ["Paris", "Berlin", "Paris", "Berlin"],
            "metric": ["temp", "temp", "temp", "temp"],
            "value": [8.0, 4.0, 9.5, 3.5],
        }
    )

    wide = long.pivot_table(index="date", columns="city", values="value", aggfunc="mean")
    print("pivot_table:\n", wide)

    melted = wide.reset_index().melt(id_vars="date", var_name="city", value_name="temp")
    print("\nmelt back to long:\n", melted.sort_values(["date", "city"]))

    # stack/unstack work on the index
    print("\nstack:\n", wide.stack())
    print("\nunstack back:\n", wide.stack().unstack())

    survey = pd.DataFrame(
        {
            "team": ["math", "math", "compiler", "compiler", "kernel"],
            "answer": ["yes", "no", "yes", "yes", "no"],
        }
    )
    print("\ncrosstab counts:\n", pd.crosstab(survey["team"], survey["answer"]))
    print("\ncrosstab proportions (normalize='index'):\n", pd.crosstab(survey["team"], survey["answer"], normalize="index"))

    # explode list-valued cells
    tags = pd.DataFrame({"id": [1, 2], "tags": [["a", "b"], ["b"]]})
    print("\nexplode:\n", tags.explode("tags"))


# ---------------------------------------------------------------------------
# 8. Time series
# ---------------------------------------------------------------------------
def time_series() -> None:
    section("8. Datetime and time series")

    rng = np.random.default_rng(11)
    index = pd.date_range("2026-01-01", periods=90, freq="D")
    ts = pd.Series(rng.normal(loc=20.0, scale=3.0, size=len(index)), index=index, name="value")
    print("head:\n", ts.head())

    print("\nmonthly mean:\n", ts.resample("ME").mean())
    print("\nweekly sum (first 4):\n", ts.resample("W").sum().head(4))
    print("\n7-day rolling mean (last 3):\n", ts.rolling(window=7).mean().tail(3))
    print("\nexponential weighted mean (last 3):\n", ts.ewm(span=7).mean().tail(3))

    print("\nfirst/last date:", ts.index.min().date(), ts.index.max().date())
    print("day of week counts:\n", ts.index.day_name().value_counts())

    # Date ranges and offsets
    print("\nbusiness days:\n", pd.bdate_range("2026-10-01", periods=5))
    shifted = ts.copy()
    shifted.index = shifted.index + pd.DateOffset(months=1)
    print("\nshifted one month (first 2):\n", shifted.head(2))

    # Lag and difference
    frame = pd.DataFrame({"value": ts})
    frame["lag1"] = frame["value"].shift(1)
    frame["diff"] = frame["value"].diff()
    print("\nlag/diff tail:\n", frame.tail(3))


# ---------------------------------------------------------------------------
# 9. Input and output
# ---------------------------------------------------------------------------
def io_examples() -> None:
    section("9. CSV, JSON, and Excel-style round-trips")

    csv_text = """name,department,salary,start
Ada,R&D,120000,2019-03-01
Linus,Kernel,150000,2012-07-15
Grace,R&D,135000,2017-11-20
"""
    df = pd.read_csv(io.StringIO(csv_text), parse_dates=["start"])
    print("read_csv:\n", df)
    print("dtypes:\n", df.dtypes)

    workdir = Path(tempfile.mkdtemp(prefix="pandas_examples_"))

    df.to_csv(workdir / "employees.csv", index=False)
    print("\nwrote CSV:", workdir / "employees.csv")

    df.to_json(workdir / "employees.json", orient="records", indent=2)
    restored = pd.read_json(workdir / "employees.json")
    print("JSON round-trip rows:", len(restored))

    # NDJSON / JSON lines
    df.to_json(workdir / "employees.ndjson", orient="records", lines=True)
    ndjson = pd.read_json(workdir / "employees.ndjson", lines=True)
    print("NDJSON rows:", len(ndjson))

    # Markdown output needs the optional `tabulate` package
    try:
        print("\nmarkdown table:\n", df.to_markdown(index=False))
    except ImportError:
        print("\ntabulate not installed; skipped to_markdown()")

    # Excel requires openpyxl; this example only writes if it is installed
    try:
        df.to_excel(workdir / "employees.xlsx", index=False)
        print("wrote Excel:", workdir / "employees.xlsx")
    except ImportError:
        print("openpyxl not installed; skipped Excel output")

    print("temporary files in:", workdir)


def main() -> None:
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 110)
    pd.set_option("display.precision", 2)

    construction()
    selection()
    cleaning()
    transformation()
    grouping()
    combining()
    reshaping()
    time_series()
    io_examples()

    print("\nAll pandas example sections completed.")


if __name__ == "__main__":
    main()
