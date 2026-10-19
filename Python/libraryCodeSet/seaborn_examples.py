"""Seaborn — practical single-file examples.

Install:  pip install seaborn pandas matplotlib
Run:      python seaborn_examples.py

Uses generated DataFrames (no downloads) and the Agg backend, saving figures
to ``output/``. Seaborn's built-in datasets (``sns.load_dataset("tips")``)
download from GitHub on first use; they are mentioned but not required here.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

OUTPUT = Path(__file__).resolve().parent / "output"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def save(fig: plt.Figure, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    fig.savefig(path, dpi=110, bbox_inches="tight")
    print("saved:", path)


def make_dataset(seed: int = 7) -> pd.DataFrame:
    """Create a tidy dataset with numeric and categorical columns."""
    rng = np.random.default_rng(seed)
    n = 300
    departments = np.array(["Engineering", "Sales", "Support", "Design"])
    regions = np.array(["North", "South", "East", "West"])

    department = rng.choice(departments, size=n, p=[0.4, 0.3, 0.2, 0.1])
    region = rng.choice(regions, size=n)
    experience = rng.gamma(shape=3.0, scale=2.5, size=n)
    base = np.select(
        [department == "Engineering", department == "Sales", department == "Design"],
        [95_000, 70_000, 80_000],
        default=60_000,
    )
    salary = base + experience * 4_000 + rng.normal(scale=6_000, size=n)
    satisfaction = np.clip(rng.normal(loc=7.0, scale=1.5, size=n), 1, 10)
    projects = rng.poisson(lam=3.0, size=n)

    return pd.DataFrame(
        {
            "department": department,
            "region": region,
            "experience_years": experience.round(1),
            "salary": salary.round(0),
            "satisfaction": satisfaction.round(1),
            "projects": projects,
        }
    )


# ---------------------------------------------------------------------------
# 1. Theme and dataset overview
# ---------------------------------------------------------------------------
def setup_and_overview(df: pd.DataFrame) -> None:
    section("1. Theme, context, and dataset overview")

    sns.set_theme(style="whitegrid", context="notebook", palette="deep")
    print("seaborn version:", sns.__version__)
    print(df.head())
    print("\ndescribe:\n", df.describe())
    print("\ncounts by department:\n", df["department"].value_counts())

    # seaborn themes: darkgrid, whitegrid, dark, white, ticks
    # contexts: paper, notebook, talk, poster
    sns.set_style("ticks")
    sns.despine()
    print("\ntheme set to 'ticks' with despine()")


# ---------------------------------------------------------------------------
# 2. Relational plots
# ---------------------------------------------------------------------------
def relational(df: pd.DataFrame) -> None:
    section("2. Scatter and line plots (relplot / scatterplot / lineplot)")

    fig = sns.relplot(
        data=df,
        x="experience_years",
        y="salary",
        hue="department",
        size="projects",
        style="region",
        alpha=0.7,
        height=5,
        aspect=1.4,
    )
    fig.set_axis_labels("Experience (years)", "Salary")
    fig.figure.suptitle("relplot: experience vs salary", y=1.02)
    save(fig.figure, "01_relplot_scatter.png")
    plt.close("all")

    # Axes-level version for embedding in an existing figure
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.scatterplot(
        data=df, x="experience_years", y="salary", hue="department", size="projects", ax=ax
    )
    ax.set_title("scatterplot on an existing Axes")
    save(fig, "02_scatterplot_axes.png")
    plt.close(fig)

    # Line plot with confidence band and multiple semantic groupings
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.lineplot(
        data=df, x="experience_years", y="satisfaction", hue="department", errorbar="sd", ax=ax
    )
    ax.set_title("Satisfaction vs experience (shaded = ±1 SD)")
    save(fig, "03_lineplot.png")
    plt.close(fig)

    # Regression line per group
    fig = sns.lmplot(
        data=df, x="experience_years", y="salary", hue="department", height=5, aspect=1.4, ci=95
    )
    fig.figure.suptitle("lmplot: per-department regression", y=1.02)
    save(fig.figure, "04_lmplot.png")
    plt.close("all")


# ---------------------------------------------------------------------------
# 3. Categorical plots
# ---------------------------------------------------------------------------
def categorical(df: pd.DataFrame) -> None:
    section("3. Categorical plots")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(data=df, x="department", y="salary", hue="region", errorbar="se", ax=ax)
    ax.set_title("Mean salary by department and region (SE bars)")
    ax.tick_params(axis="x", rotation=15)
    save(fig, "05_barplot.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.boxplot(data=df, x="department", y="salary", hue="region", ax=ax, fliersize=3)
    ax.set_title("Salary distribution by department")
    ax.tick_params(axis="x", rotation=15)
    save(fig, "06_boxplot.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.violinplot(data=df, x="department", y="satisfaction", inner="quartile", cut=0, ax=ax)
    ax.set_title("Satisfaction density by department")
    ax.tick_params(axis="x", rotation=15)
    save(fig, "07_violinplot.png")
    plt.close(fig)

    # Strip + swarm-style jitter
    sample = df.sample(80, random_state=1)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.stripplot(data=sample, x="department", y="projects", jitter=0.25, size=4, ax=ax)
    ax.set_title("Projects per employee (jittered)")
    save(fig, "08_stripplot.png")
    plt.close(fig)

    # Point plot: means with confidence intervals connected across categories
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.pointplot(data=df, x="region", y="salary", hue="department", dodge=0.3, ax=ax)
    ax.set_title("Regional salary means by department")
    save(fig, "09_pointplot.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Distribution plots
# ---------------------------------------------------------------------------
def distributions(df: pd.DataFrame) -> None:
    section("4. Histograms, KDE, and ECDF")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.histplot(data=df, x="salary", hue="department", bins=25, element="step", alpha=0.5, ax=ax)
    ax.set_title("Salary histogram by department")
    save(fig, "10_histplot.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.kdeplot(data=df, x="satisfaction", hue="region", fill=True, common_norm=False, alpha=0.35, ax=ax)
    ax.set_title("Satisfaction KDE by region")
    save(fig, "11_kdeplot.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.ecdfplot(data=df, x="salary", hue="department", ax=ax)
    ax.set_title("Salary empirical CDF")
    save(fig, "12_ecdfplot.png")
    plt.close(fig)

    # Joint distribution with marginal plots
    grid = sns.jointplot(
        data=df, x="experience_years", y="salary", hue="department", kind="scatter", height=6
    )
    grid.figure.suptitle("jointplot: scatter + marginals", y=1.02)
    save(grid.figure, "13_jointplot.png")
    plt.close("all")

    # Pairwise relationships
    pair = sns.pairplot(
        df[["experience_years", "salary", "satisfaction", "projects", "department"]],
        hue="department",
        corner=True,
        diag_kind="kde",
        height=1.9,
    )
    pair.figure.suptitle("pairplot of numeric columns", y=1.01)
    save(pair.figure, "14_pairplot.png")
    plt.close("all")


# ---------------------------------------------------------------------------
# 5. Matrix plots
# ---------------------------------------------------------------------------
def matrices(df: pd.DataFrame) -> None:
    section("5. Heatmaps and clustermaps")

    numeric = df[["experience_years", "salary", "satisfaction", "projects"]]
    correlation = numeric.corr(method="pearson")
    print("correlation matrix:\n", correlation.round(3))

    fig, ax = plt.subplots(figsize=(6, 4.5))
    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="vlag",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"label": "Pearson r"},
        ax=ax,
    )
    ax.set_title("Correlation heatmap")
    save(fig, "15_heatmap_corr.png")
    plt.close(fig)

    pivot = df.pivot_table(
        index="department", columns="region", values="salary", aggfunc="mean"
    )
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGnBu", linewidths=0.5, ax=ax)
    ax.set_title("Mean salary by department × region")
    save(fig, "16_heatmap_pivot.png")
    plt.close(fig)

    # Clustermap reorders rows/columns by similarity
    cluster = sns.clustermap(
        correlation, annot=True, fmt=".2f", cmap="vlag", center=0, figsize=(6, 5)
    )
    cluster.figure.suptitle("Clustered correlation matrix", y=1.02)
    save(cluster.figure, "17_clustermap.png")
    plt.close("all")


# ---------------------------------------------------------------------------
# 6. Multi-plot grids
# ---------------------------------------------------------------------------
def grids(df: pd.DataFrame) -> None:
    section("6. FacetGrid and catplot")

    grid = sns.FacetGrid(df, col="region", row="department", height=2.6, aspect=1.2, margin_titles=True)
    grid.map_dataframe(sns.scatterplot, x="experience_years", y="salary", alpha=0.6)
    grid.set_axis_labels("experience", "salary")
    grid.figure.suptitle("FacetGrid: salary vs experience", y=1.01)
    save(grid.figure, "18_facetgrid.png")
    plt.close("all")

    # catplot returns a FacetGrid and handles figure-level sizing
    cat = sns.catplot(
        data=df,
        kind="box",
        x="department",
        y="salary",
        col="region",
        col_wrap=2,
        height=3.2,
        aspect=1.25,
    )
    cat.figure.suptitle("catplot: salary by department, faceted by region", y=1.02)
    save(cat.figure, "19_catplot.png")
    plt.close("all")

    # Two-variable facet with custom mapping
    grid = sns.FacetGrid(df, col="department", col_wrap=2, height=3.2)
    grid.map_dataframe(sns.histplot, x="salary", bins=20, color="tab:blue")
    grid.set_titles("{col_name}")
    save(grid.figure, "20_facet_hist.png")
    plt.close("all")


# ---------------------------------------------------------------------------
# 7. Styling details
# ---------------------------------------------------------------------------
def styling(df: pd.DataFrame) -> None:
    section("7. Contexts, palettes, and publication styling")

    print("palette sample:", sns.color_palette("husl", 6).as_hex())

    sns.set_context("talk")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(
        data=df,
        x="department",
        y="salary",
        palette="mako",
        hue="department",
        legend=False,
        errorbar=None,
        ax=ax,
    )
    ax.set_title("Talk context with mako palette")
    ax.tick_params(axis="x", rotation=15)
    sns.despine()
    save(fig, "21_talk_context.png")
    plt.close(fig)

    # Reset to defaults for the rest of the session
    sns.set_theme(style="whitegrid", context="notebook")

    # Custom legend placement and title
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.scatterplot(data=df, x="projects", y="satisfaction", hue="region", ax=ax)
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_title("Legend outside the axes")
    save(fig, "22_legend_outside.png")
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    df = make_dataset()

    setup_and_overview(df)
    relational(df)
    categorical(df)
    distributions(df)
    matrices(df)
    grids(df)
    styling(df)

    print("\nAll Seaborn example sections completed.")


if __name__ == "__main__":
    main()
