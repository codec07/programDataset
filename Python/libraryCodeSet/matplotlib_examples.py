"""Matplotlib — practical single-file examples.

Install:  pip install matplotlib
Run:      python matplotlib_examples.py

Uses the non-interactive Agg backend so every figure is written to
``output/`` without needing a display. Replace ``matplotlib.use("Agg")`` with
``matplotlib.use("TkAgg")`` (or delete it) if you want interactive windows.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe; remove for plt.show()

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib import gridspec
from matplotlib.patches import Circle, Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator

OUTPUT = Path(__file__).resolve().parent / "output"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def save(fig: plt.Figure, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    fig.savefig(path, dpi=110, bbox_inches="tight")
    print("saved:", path)


# ---------------------------------------------------------------------------
# 1. Pyplot state-machine API vs object-oriented API
# ---------------------------------------------------------------------------
def basics() -> None:
    section("1. Line plots: pyplot vs object-oriented API")

    x = np.linspace(0, 2 * np.pi, 200)

    # State-machine style: fine for quick scripts
    plt.figure(figsize=(7, 4))
    plt.plot(x, np.sin(x), label="sin(x)")
    plt.plot(x, np.cos(x), "--", label="cos(x)")
    plt.title("State-machine style")
    plt.xlabel("x (radians)")
    plt.ylabel("value")
    plt.legend()
    plt.grid(alpha=0.3)
    save(plt.gcf(), "01_line_pyplot.png")
    plt.close("all")

    # Object-oriented style: recommended for anything non-trivial
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x, np.sin(x), color="tab:blue", linewidth=2, label="sin")
    ax.plot(x, np.sin(2 * x), color="tab:orange", linewidth=1.5, label="sin(2x)")
    ax.set(title="Object-oriented style", xlabel="x", ylabel="amplitude")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.set_xlim(0, 2 * np.pi)
    save(fig, "02_line_oo.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2. Subplots and layout
# ---------------------------------------------------------------------------
def subplots() -> None:
    section("2. Subplots, gridspec, and shared axes")

    x = np.linspace(-3, 3, 200)

    fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
    axes[0, 0].plot(x, x, label="linear")
    axes[0, 0].set_title("linear")
    axes[0, 1].plot(x, x**2, color="tab:orange")
    axes[0, 1].set_title("quadratic")
    axes[1, 0].plot(x, x**3, color="tab:green")
    axes[1, 0].set_title("cubic")
    axes[1, 1].plot(x, np.tanh(x), color="tab:red")
    axes[1, 1].set_title("tanh")
    fig.suptitle("2×2 subplot grid", fontsize=13)
    fig.tight_layout()
    save(fig, "03_subplots.png")
    plt.close(fig)

    # Uneven layout with gridspec
    fig = plt.figure(figsize=(8, 5))
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[2, 1])
    ax_big = fig.add_subplot(gs[0, :])
    ax_left = fig.add_subplot(gs[1, 0])
    ax_mid = fig.add_subplot(gs[1, 1])
    ax_right = fig.add_subplot(gs[1, 2])

    ax_big.plot(x, np.sinc(x / np.pi), color="black")
    ax_big.set_title("gridspec: wide top panel")
    for ax, color, fn in zip(
        (ax_left, ax_mid, ax_right),
        ("tab:blue", "tab:orange", "tab:green"),
        (np.sin, np.cos, np.tanh),
    ):
        ax.plot(x, fn(x), color=color)
        ax.set_yticks([])
    fig.tight_layout()
    save(fig, "04_gridspec.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Scatter and bubble charts
# ---------------------------------------------------------------------------
def scatter() -> None:
    section("3. Scatter plots, colour mapping, and bubbles")

    rng = np.random.default_rng(3)
    n = 180
    x = rng.normal(size=n)
    y = 0.7 * x + rng.normal(scale=0.5, size=n)
    sizes = rng.uniform(20, 300, size=n)
    values = rng.uniform(0, 1, size=n)

    fig, ax = plt.subplots(figsize=(7, 5))
    scatter = ax.scatter(
        x, y, s=sizes, c=values, cmap="viridis", alpha=0.75, edgecolors="white", linewidths=0.5
    )
    ax.set(title="Bubble chart", xlabel="x", ylabel="y")
    fig.colorbar(scatter, ax=ax, label="score")
    save(fig, "05_scatter.png")
    plt.close(fig)

    # Marker styles
    fig, ax = plt.subplots(figsize=(7, 4))
    markers = ["o", "s", "^", "D", "x", "+", "*", "v"]
    for i, marker in enumerate(markers):
        ax.plot(i, i, marker=marker, markersize=10, linestyle="none", label=marker)
    ax.set_title("Marker reference")
    ax.set_xlim(-1, len(markers))
    ax.set_ylim(-1, len(markers))
    ax.legend(ncol=4)
    save(fig, "06_markers.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Bar charts and categorical data
# ---------------------------------------------------------------------------
def bars() -> None:
    section("4. Bar, grouped bar, stacked bar, and horizontal bars")

    categories = ["Q1", "Q2", "Q3", "Q4"]
    north = np.array([120, 135, 150, 170])
    south = np.array([90, 110, 105, 130])
    positions = np.arange(len(categories))
    width = 0.36

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(positions - width / 2, north, width, label="North", color="tab:blue")
    ax.bar(positions + width / 2, south, width, label="South", color="tab:orange")
    ax.set_xticks(positions, categories)
    ax.set(title="Grouped quarterly revenue", ylabel="revenue (k)")
    ax.legend()
    ax.bar_label(ax.containers[0], padding=2, fontsize=8)
    ax.bar_label(ax.containers[1], padding=2, fontsize=8)
    save(fig, "07_grouped_bar.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(categories, north, label="North", color="tab:blue")
    ax.bar(categories, south, bottom=north, label="South", color="tab:orange")
    ax.set(title="Stacked revenue", ylabel="revenue (k)")
    ax.legend()
    save(fig, "08_stacked_bar.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    errors = np.array([8, 10, 7, 12])
    ax.barh(categories, north, xerr=errors, color="tab:green", alpha=0.8, capsize=4)
    ax.set(title="Horizontal bars with error bars", xlabel="revenue (k)")
    ax.invert_yaxis()
    save(fig, "09_barh.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. Distributions
# ---------------------------------------------------------------------------
def distributions() -> None:
    section("5. Histograms, box plots, violin plots, and ECDF")

    rng = np.random.default_rng(21)
    data = rng.normal(loc=50, scale=12, size=1_500)
    groups = [rng.normal(loc=m, scale=8, size=300) for m in (40, 50, 60)]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(data, bins=30, density=True, alpha=0.65, color="tab:blue", edgecolor="white")
    ax.set(title="Histogram (density)", xlabel="value", ylabel="density")
    save(fig, "10_histogram.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot(groups, tick_labels=["group A", "group B", "group C"], showmeans=True)
    ax.set(title="Box plot with means", ylabel="value")
    save(fig, "11_boxplot.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    parts = ax.violinplot(groups, showmedians=True)
    for body in parts["bodies"]:
        body.set_alpha(0.65)
    ax.set_xticks([1, 2, 3], ["group A", "group B", "group C"])
    ax.set(title="Violin plot", ylabel="value")
    save(fig, "12_violin.png")
    plt.close(fig)

    # Empirical CDF
    sorted_data = np.sort(data)
    ecdf = np.arange(1, sorted_data.size + 1) / sorted_data.size
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(sorted_data, ecdf, where="post")
    ax.set(title="Empirical CDF", xlabel="value", ylabel="F(x)")
    ax.grid(alpha=0.3)
    save(fig, "13_ecdf.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. Heatmaps, contours, and images
# ---------------------------------------------------------------------------
def grids() -> None:
    section("6. Heatmaps, contours, and image display")

    x = np.linspace(-3, 3, 120)
    y = np.linspace(-3, 3, 100)
    xx, yy = np.meshgrid(x, y)
    z = np.exp(-(xx**2 + yy**2)) * np.cos(2 * xx) * np.sin(2 * yy)

    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(z, extent=[-3, 3, -3, 3], origin="lower", cmap="RdBu_r", aspect="auto")
    ax.set(title="imshow heatmap", xlabel="x", ylabel="y")
    fig.colorbar(image, ax=ax, label="z")
    save(fig, "14_heatmap.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    filled = ax.contourf(xx, yy, z, levels=20, cmap="viridis")
    lines = ax.contour(xx, yy, z, levels=8, colors="black", linewidths=0.7)
    ax.clabel(lines, inline=True, fontsize=7)
    ax.set(title="Filled + line contours")
    fig.colorbar(filled, ax=ax, label="z")
    save(fig, "15_contour.png")
    plt.close(fig)

    # Synthetic RGB image
    rgb = np.zeros((80, 120, 3))
    rgb[:, :, 0] = np.linspace(0, 1, 120)
    rgb[:, :, 1] = np.linspace(0, 1, 80)[:, None]
    rgb[:, :, 2] = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.imshow(rgb)
    ax.set_title("RGB array via imshow")
    ax.axis("off")
    save(fig, "16_rgb.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 7. Annotations, reference lines, and formatting
# ---------------------------------------------------------------------------
def annotations() -> None:
    section("7. Annotations, reference lines, and tick formatting")

    x = np.linspace(0, 12, 200)
    y = np.sin(x) * np.exp(-x / 10)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, y, color="tab:blue", label="damped sine")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(np.pi, color="tab:red", linestyle="--", linewidth=1, label="x = π")
    ax.axhspan(-0.5, -0.25, color="tab:orange", alpha=0.15, label="target band")

    peak_index = int(np.argmax(y))
    ax.annotate(
        "first peak",
        xy=(x[peak_index], y[peak_index]),
        xytext=(x[peak_index] + 1.5, y[peak_index] + 0.15),
        arrowprops=dict(arrowstyle="->", color="black"),
        fontsize=9,
    )
    ax.scatter([x[peak_index]], [y[peak_index]], color="black", zorder=5)

    ax.set(title="Annotations and reference lines", xlabel="x", ylabel="y")
    ax.xaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25)
    save(fig, "17_annotations.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 8. Multiple axes and twinx
# ---------------------------------------------------------------------------
def multiple_axes() -> None:
    section("8. Twin axes and inset axes")

    months = np.arange(1, 13)
    revenue = np.array([80, 85, 95, 110, 120, 130, 135, 140, 150, 160, 175, 190])
    growth = np.diff(revenue, prepend=revenue[0]) / revenue[0] * 100

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.bar(months, revenue, color="tab:blue", alpha=0.75, label="revenue")
    ax1.set(xlabel="month", ylabel="revenue (k)", title="Revenue and growth")
    ax1.set_xticks(months)

    ax2 = ax1.twinx()
    ax2.plot(months, growth, color="tab:red", marker="o", label="growth %")
    ax2.set_ylabel("growth (%)", color="tab:red")
    ax2.tick_params(axis="y", colors="tab:red")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    # Inset zoom
    inset = ax1.inset_axes([0.55, 0.15, 0.3, 0.3])
    inset.plot(months[-3:], revenue[-3:], color="black", marker="s")
    inset.set_title("last quarter", fontsize=8)
    inset.tick_params(labelsize=7)

    save(fig, "18_twin_axes.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 9. Shapes, patches, and a simple diagram
# ---------------------------------------------------------------------------
def shapes() -> None:
    section("9. Patches and diagrams")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(Rectangle((0.5, 0.8), 3.5, 2.0, facecolor="tab:blue", alpha=0.35, edgecolor="black"))
    ax.text(2.25, 1.8, "client", ha="center", va="center", fontsize=11)

    ax.add_patch(Rectangle((6.0, 3.2), 3.2, 2.0, facecolor="tab:green", alpha=0.35, edgecolor="black"))
    ax.text(7.6, 4.2, "server", ha="center", va="center", fontsize=11)

    ax.add_patch(Circle((5.0, 3.0), 0.55, facecolor="tab:orange", edgecolor="black"))
    ax.text(5.0, 3.0, "API", ha="center", va="center", fontsize=9)

    ax.annotate("", xy=(6.0, 4.2), xytext=(4.0, 1.9),
                arrowprops=dict(arrowstyle="->", linewidth=1.5))
    ax.annotate("", xy=(4.0, 1.9), xytext=(6.0, 3.4),
                arrowprops=dict(arrowstyle="->", linewidth=1.5, linestyle="--"))
    ax.set_title("Patch-based diagram")
    save(fig, "19_patches.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 10. Styles, colour maps, and saving
# ---------------------------------------------------------------------------
def styles_and_output() -> None:
    section("10. Styles, colour maps, and output formats")

    print("available styles (first 10):", plt.style.available[:10])

    x = np.linspace(0, 10, 100)
    with plt.style.context("ggplot"):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(x, np.sin(x), label="sin")
        ax.plot(x, np.cos(x), label="cos")
        ax.set_title("ggplot style context")
        ax.legend()
        save(fig, "20_style_ggplot.png")
        plt.close(fig)

    # Sample a colour map into hex values
    cmap = plt.get_cmap("plasma")
    print("plasma samples:", [mcolors.to_hex(cmap(v)) for v in np.linspace(0, 1, 5)])

    # Bar chart with a colour map by value
    values = np.array([3, 7, 2, 9, 5])
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(range(len(values)), values, color=plt.get_cmap("viridis")(values / values.max()))
    ax.set(title="Colour-mapped bars", xlabel="category", ylabel="value")
    ax.bar_label(bars)
    save(fig, "21_colormap_bars.png")
    plt.close(fig)

    # Save the same figure in several formats
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(x, x**2)
    ax.set_title("multi-format export")
    for extension in ("png", "pdf", "svg"):
        path = OUTPUT / f"22_export.{extension}"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        print("saved:", path)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    print("output directory:", OUTPUT)

    basics()
    subplots()
    scatter()
    bars()
    distributions()
    grids()
    annotations()
    multiple_axes()
    shapes()
    styles_and_output()

    print("\nAll Matplotlib example sections completed.")


if __name__ == "__main__":
    main()
