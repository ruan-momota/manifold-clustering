"""Plot LAPD paper-demo reproduction and OpenML34 results.

Only runs with a prediction for every sample receive an ARI. Aggregate bars
use the same datasets for LAPD and K-means within each LAPD mode.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy.io import loadmat


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
AUDIT = RESULTS / "lapd_stage4_audit.csv"
COLORS = {"kmeans": "#3973a7", "known": "#e47a3f", "estimate": "#55a685"}


def plot_paper_reproduction() -> None:
    # Table 3, full-class rows, LAPD^2 (two-sided weights):
    # https://arxiv.org/html/2507.10710v1#S5.SS4
    benchmarks = [
        ("COIL20, 20 classes", "bench_coil20_known.mat", 0.904, 1440, 20),
        ("USPS, 10 classes", "bench_usps_known.mat", 0.935, 9298, 10),
    ]
    labels, paper, local = [], [], []
    for label, filename, paper_accuracy, n_samples, k in benchmarks:
        saved = loadmat(RESULTS / "lapd_returns" / "stage1" / "lapd" / filename,
                        squeeze_me=True, struct_as_record=False)
        if (
            len(np.asarray(saved["labelsGT"]).ravel()) != n_samples
            or int(saved["opts"].K) != k
            or str(saved["opts"].weight) != "two sided"
        ):
            raise ValueError(f"Stage-1 benchmark does not match paper row: {filename}")
        labels.append(label)
        paper.append(paper_accuracy)
        local.append(float(saved["clustering_accuracy"]))

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    bars_paper = ax.bar(x - 0.18, paper, 0.35, color=COLORS["kmeans"],
                        label="Paper, LAPD two-sided")
    bars_local = ax.bar(x + 0.18, local, 0.35, color=COLORS["known"],
                        label="Local reproduction")
    ax.bar_label(bars_paper, fmt="%.4f", padding=4)
    ax.bar_label(bars_local, fmt="%.4f", padding=4)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Clustering accuracy")
    ax.set_title("LAPD paper benchmarks: full-class subsets")
    ax.grid(axis="y", color="0.85")
    ax.set_axisbelow(True)
    ax.legend(loc="lower right")
    fig.savefig(RESULTS / "lapd_paper_reproduction.png", dpi=200)
    plt.close(fig)


def load_results() -> pd.DataFrame:
    data = pd.read_csv(AUDIT)
    expected_modes = {"known", "estimate"}
    if (
        set(data["mode"]) != expected_modes
        or len(data) != 68
        or data["openml_id"].nunique() != 34
        or data.duplicated(["openml_id", "mode"]).any()
    ):
        raise ValueError("Expected 34 OpenML IDs and one result per LAPD mode")
    if data["status"].eq("complete").ne(data["ari"].notna()).any():
        raise ValueError("Incomplete predictions must not have an ARI")
    by_id = data.pivot(index="openml_id", columns="mode", values="kmeans_ari")
    if not np.allclose(by_id["known"], by_id["estimate"]):
        raise ValueError("K-means baseline differs between LAPD modes")
    return data


def plot_dataset_scores(data: pd.DataFrame) -> None:
    wide = data.pivot(index="openml_id", columns="mode", values="ari")
    baseline = data[data["mode"] == "known"].set_index("openml_id")["kmeans_ari"]
    ids = baseline.sort_values(ascending=False).index
    y = np.arange(len(ids))
    fig, ax = plt.subplots(figsize=(11.5, 11), layout="constrained")
    ax.axvspan(-0.14, -0.055, color="#f0f0f0", zorder=0)
    ax.scatter(baseline.loc[ids], y + 0.22, s=42, color=COLORS["kmeans"],
               marker="o", label="ZEUS + K-means", zorder=3)
    for mode, offset, label in [
        ("known", 0, "LAPD, K supplied"),
        ("estimate", -0.22, "LAPD, K estimated"),
    ]:
        scores = wide.loc[ids, mode]
        complete = scores.notna().to_numpy()
        ax.scatter(scores[complete], y[complete] + offset, s=43,
                   color=COLORS[mode], marker="D" if mode == "known" else "s",
                   label=label, zorder=4)
        ax.scatter(np.full((~complete).sum(), -0.097), y[~complete] + offset,
                   s=53, color=COLORS[mode], marker="x", linewidth=1.8,
                   zorder=5)
    ax.set_yticks(y, labels=[str(i) for i in ids])
    ax.invert_yaxis()
    ax.set_xlim(-0.14, 1.02)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Adjusted Rand index (ARI); crosses in shaded column = missing")
    ax.set_ylabel("OpenML dataset ID (sorted by K-means ARI)")
    ax.set_title("OpenML34: LAPD reproduction vs ZEUS + K-means")
    ax.grid(axis="x", color="0.85", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", ncol=3, frameon=True)
    fig.savefig(RESULTS / "lapd_openml34_by_dataset.png", dpi=200)
    plt.close(fig)


def plot_matched_means(data: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
    group_labels = []
    for group, mode in enumerate(("known", "estimate")):
        subset = data[(data["mode"] == mode) & (data["status"] == "complete")]
        n = len(subset)
        values = [subset["kmeans_ari"].mean(), subset["ari"].mean()]
        bars = ax.bar([group * 2.5, group * 2.5 + 0.8], values, width=0.7,
                      color=[COLORS["kmeans"], COLORS[mode]])
        ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=4)
        group_labels.append(f"K {'supplied' if mode == 'known' else 'estimated'}\n{n}/34 complete")
    ax.set_xticks([0.4, 2.9], group_labels)
    ax.set_ylim(0, max(data["kmeans_ari"].mean(), data["ari"].mean()) * 1.35)
    ax.set_ylabel("Mean ARI on the same complete datasets")
    ax.set_title("OpenML34: matched-set mean ARI")
    ax.grid(axis="y", color="0.85")
    ax.set_axisbelow(True)
    ax.legend(handles=[
        Patch(color=COLORS["kmeans"], label="ZEUS + K-means"),
        Patch(color=COLORS["known"], label="LAPD, K supplied"),
        Patch(color=COLORS["estimate"], label="LAPD, K estimated"),
    ], loc="upper right")
    fig.savefig(RESULTS / "lapd_openml34_matched_means.png", dpi=200)
    plt.close(fig)


def plot_scatter(data: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.3), sharex=True, sharey=True,
                             layout="constrained")
    for ax, mode in zip(axes, ("known", "estimate")):
        subset = data[data["mode"] == mode]
        complete = subset[subset["status"] == "complete"]
        missing = subset[subset["status"] != "complete"]
        ax.plot([-0.1, 1], [-0.1, 1], linestyle="--", color="0.55", linewidth=1)
        ax.scatter(complete["kmeans_ari"], complete["ari"], s=48,
                   color=COLORS[mode], alpha=0.85)
        ax.set_title(f"LAPD {mode}: {len(complete)}/34 complete")
        ax.set_xlabel("ZEUS + K-means ARI")
        ax.grid(alpha=0.2)
        ax.set_aspect("equal", adjustable="box")
        if not missing.empty:
            ax.text(0.02, 0.98, "Missing LAPD ARI: " + ", ".join(
                str(int(i)) for i in missing["openml_id"]),
                transform=ax.transAxes, va="top", fontsize=8.5,
                bbox={"facecolor": "white", "edgecolor": "0.85", "alpha": 0.9})
    axes[0].set_ylabel("LAPD ARI")
    axes[0].set_xlim(-0.1, 1.02)
    axes[0].set_ylim(-0.1, 1.02)
    fig.suptitle("OpenML34: paired ARI on complete LAPD runs")
    fig.savefig(RESULTS / "lapd_openml34_scatter.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    plot_paper_reproduction()
    results = load_results()
    plot_dataset_scores(results)
    plot_matched_means(results)
    plot_scatter(results)
    print("Saved LAPD paper-reproduction and three OpenML34 charts in results/")
