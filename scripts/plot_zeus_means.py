"""Plot the paper and local five-seed ZEUS means for the 34 OpenML datasets."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
comparison = pd.read_csv(RESULTS / "zeus_table9_comparison.csv")

paper = comparison["paper_zeus"]
local = comparison["local_zeus"]
colors = {"paper": "#3266a8", "local": "#e06b3c"}


fig, ax = plt.subplots(figsize=(6, 6), layout="constrained")
means = [paper.mean(), local.mean()]
bars = ax.bar(["Paper ZEUS", "Local ZEUS"], means,
              color=[colors["paper"], colors["local"]], width=0.55)
ax.bar_label(bars, fmt="%.2f", padding=4)
ax.set_ylim(0, 75)
ax.set_ylabel("Mean ARI × 100 across 34 datasets")
ax.set_title("ZEUS + K-means: overall mean")
ax.grid(axis="y", alpha=0.25)
ax.set_axisbelow(True)
fig.savefig(RESULTS / "zeus_means_bar.png", dpi=200)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 6), layout="constrained")
ax.plot([-10, 105], [-10, 105], "--", color="0.55", linewidth=1)
ax.scatter(paper, paper, s=90, facecolors="none", edgecolors=colors["paper"],
           linewidths=1.5, label="Paper ZEUS", zorder=3)
ax.scatter(paper, local, s=35, marker="x", color=colors["local"],
           linewidths=1.8, label="Local ZEUS", zorder=4)
ax.set(xlim=(-10, 105), ylim=(-10, 105),
       xlabel="Paper ZEUS (ARI × 100)",
       ylabel="ZEUS mean (ARI × 100)",
       title="ZEUS + K-means: paper and local means")
ax.grid(alpha=0.2)
ax.legend()
for index in comparison["delta"].abs().nlargest(3).index:
    row = comparison.loc[index]
    ax.annotate(str(int(row["openml_id"])), (row["paper_zeus"], row["local_zeus"]),
                xytext=(5, 5), textcoords="offset points", fontsize=9)
fig.savefig(RESULTS / "zeus_means_scatter.png", dpi=200)
plt.close(fig)

print("Saved results/zeus_means_bar.png and results/zeus_means_scatter.png")
