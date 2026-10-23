"""Make the three figures, saved to figures/ at 300 dpi.

1. heatmap_priority_signals.png
   Rows: the top 20 ranked candidates, then the standard drugs.
   Columns: the priority side effects. Colour: ROR (log scale) for signals only;
   blank where there is no signal.
2. forest_top5_clots_depression.png
   ROR with 95% CI for the top 5 candidates on DEEP VEIN THROMBOSIS,
   PULMONARY EMBOLISM and DEPRESSION.
3. bar_report_counts.png
   Reports per drug (drugs with at least 1 report), with a line at 50 reports.

Input: data/clean/signals.csv, data/clean/ranked_drugs.csv, decisions.md
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compute_ror import load_priority_terms  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
FIGURES = ROOT / "figures"
DPI = 300
MIN_REPORTS = 50
TOP_HEATMAP = 20
TOP_FOREST = 5
FOREST_TERMS = ["DEEP VEIN THROMBOSIS", "PULMONARY EMBOLISM", "DEPRESSION"]

# Colours (reference data-viz palette, light mode)
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
CANDIDATE = "#2a78d6"  # categorical slot 1, blue
STANDARD = "#eb6834"   # categorical slot 2, orange
SEQUENTIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": TEXT,
    "axes.labelcolor": TEXT_SECONDARY,
    "axes.edgecolor": GRID,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
})


def title_case(term):
    return term.capitalize()


def heatmap(signals, ranked, priority):
    enough = ranked[ranked["status"] == "enough data"]
    candidates = enough[enough["group"] == "candidate"].head(TOP_HEATMAP)["drug_name"].tolist()
    standard = enough[enough["group"] == "standard"]["drug_name"].tolist()
    rows = candidates + standard

    hits = signals[signals["signal"] & signals["priority"] & signals["drug_name"].isin(rows)]
    grid = hits.pivot(index="drug_name", columns="reaction", values="ror").reindex(index=rows, columns=priority)

    fig = plt.figure(figsize=(9, 11.5))
    ax = fig.add_axes([0.28, 0.25, 0.65, 0.68])
    colorbar_ax = fig.add_axes([0.45, 0.04, 0.35, 0.012])
    vmax = max(100, np.nanmax(grid.values))
    cmap = LinearSegmentedColormap.from_list("blue", SEQUENTIAL)
    cmap.set_bad(SURFACE)
    image = ax.imshow(grid.values, cmap=cmap, norm=LogNorm(vmin=1, vmax=vmax), aspect="auto")

    # Cell borders and ROR labels on signal cells
    ax.set_xticks(np.arange(-0.5, len(priority)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows)), minor=True)
    ax.grid(which="minor", color=GRID, linewidth=0.6)
    ax.tick_params(which="minor", length=0)
    for (i, j), value in np.ndenumerate(grid.values):
        if not np.isnan(value):
            dark = np.log(value) / np.log(vmax) > 0.45
            ax.text(j, i, f"{value:.1f}" if value < 10 else f"{value:.0f}",
                    ha="center", va="center", fontsize=6.5, color="white" if dark else TEXT)

    # Divider between candidates and standard drugs
    ax.axhline(len(candidates) - 0.5, color=TEXT, linewidth=1.5)
    ax.text(len(priority) - 0.45, len(candidates) / 2 - 0.5, f"Top {len(candidates)} candidates",
            rotation=270, va="center", ha="left", fontsize=8, color=TEXT_SECONDARY)
    ax.text(len(priority) - 0.45, len(candidates) + len(standard) / 2 - 0.5, "Standard treatments",
            rotation=270, va="center", ha="left", fontsize=8, color=TEXT_SECONDARY)

    labels = [f"{rank}. {name}" for name, rank in zip(candidates, range(1, len(candidates) + 1))] + standard
    ax.set_yticks(range(len(rows)), labels)
    ax.set_xticks(range(len(priority)), [title_case(t) for t in priority], rotation=45, ha="right")
    ax.tick_params(which="major", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    bar = fig.colorbar(image, cax=colorbar_ax, orientation="horizontal")
    bar.set_ticks([1, 2, 5, 10, 20, 50, 100])
    bar.set_ticklabels(["1", "2", "5", "10", "20", "50", "100"])
    bar.set_label("Reporting odds ratio (log scale)", color=TEXT_SECONDARY)
    bar.outline.set_visible(False)

    ax.set_title("Priority side-effect signals: top candidates vs standard treatments", pad=36)
    ax.text(0, 1.008, "Coloured cells are signals (at least 3 reports and lower 95% CI above 1); "
            "blank means no signal.\nWomen aged 12–35, FAERS.",
            transform=ax.transAxes, fontsize=8, color=TEXT_SECONDARY)
    fig.savefig(FIGURES / "heatmap_priority_signals.png", dpi=DPI)
    plt.close(fig)


def forest(signals, ranked):
    enough = ranked[ranked["status"] == "enough data"]
    top = enough[enough["group"] == "candidate"].head(TOP_FOREST)["drug_name"].tolist()

    fig, axes = plt.subplots(1, len(FOREST_TERMS), figsize=(10, 3.6), sharey=True)
    for ax, term in zip(axes, FOREST_TERMS):
        rows = signals[(signals["reaction"] == term) & signals["drug_name"].isin(top)].set_index("drug_name")
        ax.axvline(1, color=TEXT_SECONDARY, linewidth=1, linestyle="--", zorder=1)
        for y, drug in enumerate(top):
            if drug in rows.index and pd.notna(rows.loc[drug, "ror"]):
                r = rows.loc[drug]
                ax.plot([r["ci_lower"], r["ci_upper"]], [y, y], color=CANDIDATE, linewidth=2,
                        solid_capstyle="round", zorder=2)
                ax.plot(r["ror"], y, "o", markersize=8, color=CANDIDATE,
                        markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
                ax.text(1.0, y, f"{r['ror']:.2f} (n={int(r['a'])})", transform=ax.get_yaxis_transform(),
                        ha="right", va="center", fontsize=7, color=TEXT_SECONDARY)
            else:
                ax.text(1, y, "no reports", va="center", ha="center", fontsize=7,
                        color=TEXT_SECONDARY, style="italic",
                        bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))
        ax.set_xscale("log")
        ax.set_xlim(0.05, 60)
        ax.set_xticks([0.1, 0.5, 1, 2, 5, 10], ["0.1", "0.5", "1", "2", "5", "10"])
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_title(title_case(term), fontsize=9.5)
        ax.set_xlabel("ROR (95% CI, log scale)")
        for side in ["top", "right", "left"]:
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(top)), [f"{i}. {d}" for i, d in enumerate(top, start=1)])
    axes[0].invert_yaxis()

    fig.suptitle(f"Blood clots and depression: top {TOP_FOREST} candidates",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.text(0.01, 0.885, "Dot = ROR, line = 95% CI, n = reports with the drug and side effect. "
             "Dashed line at 1 = reported as often as with other drugs.",
             fontsize=8, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(FIGURES / "forest_top5_clots_depression.png", dpi=DPI)
    plt.close(fig)


def bars(ranked):
    drugs = ranked[ranked["total_reports"] > 0].sort_values("total_reports", ascending=False)
    zero = (ranked["total_reports"] == 0).sum()
    colours = drugs["group"].map({"candidate": CANDIDATE, "standard": STANDARD})

    fig, ax = plt.subplots(figsize=(16, 6))
    x = np.arange(len(drugs))
    ax.bar(x, drugs["total_reports"], width=0.8, color=colours, linewidth=0)
    ax.set_yscale("log")
    ax.axhline(MIN_REPORTS, color=TEXT, linewidth=1.2, linestyle="--")
    ax.text(len(drugs) - 1, MIN_REPORTS * 1.15, f"{MIN_REPORTS} reports: below this, not enough data",
            ha="right", va="bottom", fontsize=8.5, color=TEXT)

    ax.set_xticks(x, drugs["drug_name"], rotation=90, fontsize=3.6)
    for tick, group in zip(ax.get_xticklabels(), drugs["group"]):
        if group == "standard":
            tick.set_fontweight("bold")
            tick.set_color(TEXT)
    ax.set_xlim(-1, len(drugs))
    ax.set_ylabel("Reports (log scale)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)

    legend = [Patch(color=CANDIDATE, label="Candidate"), Patch(color=STANDARD, label="Standard treatment"),
              Line2D([0], [0], color=TEXT, linestyle="--", label=f"{MIN_REPORTS}-report cut-off")]
    ax.legend(handles=legend, frameon=False, loc="upper right")
    ax.set_title("FAERS reports per drug, women aged 12–35", pad=20)
    ax.text(0, 1.01, f"{len(drugs)} drugs with at least 1 report; {zero} drugs with 0 reports are not shown.",
            transform=ax.transAxes, fontsize=8, color=TEXT_SECONDARY)
    fig.tight_layout()
    fig.savefig(FIGURES / "bar_report_counts.png", dpi=DPI)
    plt.close(fig)


def main():
    FIGURES.mkdir(exist_ok=True)
    signals = pd.read_csv(CLEAN / "signals.csv")
    ranked = pd.read_csv(CLEAN / "ranked_drugs.csv")
    priority = load_priority_terms()

    heatmap(signals, ranked, priority)
    forest(signals, ranked)
    bars(ranked)
    for path in sorted(FIGURES.glob("*.png")):
        print(f"Saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
