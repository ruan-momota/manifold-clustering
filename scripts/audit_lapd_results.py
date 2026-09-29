"""Validate returned LAPD runs and summarize complete predictions against ZEUS K-means."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.metrics import adjusted_rand_score


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "results" / "lapd_returns" / "stage4" / "lapd"
OUTPUT = ROOT / "results" / "lapd_stage4_audit.csv"

status = pd.read_csv(RUN_DIR / "run_status.tsv", sep="\t")
baseline = pd.read_csv(ROOT / "results" / "zeus_openml_baseline.csv")
baseline = baseline[baseline["method"] == "scaled_zeus"].set_index("openml_id")
expected_datasets = {f"openml_{openml_id}_scaled" for openml_id in baseline.index}
if (
    len(status) != 68
    or set(status["dataset"]) != expected_datasets
    or status.duplicated(["dataset", "mode"]).any()
    or set(status["mode"]) != {"known", "estimate"}
):
    raise ValueError("Expected 34 datasets and 68 mode runs")

rows = []
for run in status.itertuples(index=False):
    openml_id = int(run.dataset.split("_")[1])
    path = RUN_DIR / f"{run.dataset}_{run.mode}.mat"
    if not path.is_file():
        raise FileNotFoundError(path)
    saved = loadmat(path, squeeze_me=True, struct_as_record=False)
    truth = np.asarray(saved["labelsGT"]).ravel()
    predicted = np.asarray(saved["predicted_labels"]).ravel()
    indices = np.asarray(saved["sample_indices"]).ravel()
    with np.load(ROOT / "data" / "embeddings" / f"openml_{openml_id}.npz") as source:
        if not np.array_equal(truth, source["labels"]):
            raise ValueError(f"Label mismatch: {path}")
        if not np.array_equal(indices, source["sample_indices"]):
            raise ValueError(f"Sample-order mismatch: {path}")
    if len(predicted) != len(truth):
        raise ValueError(f"Prediction length mismatch: {path}")

    finite = np.isfinite(predicted)
    complete = bool(finite.all())
    ari = adjusted_rand_score(truth, predicted) if complete else np.nan
    kmeans_ari = float(baseline.loc[openml_id, "ari"])
    options = saved["opts"]
    rows.append(
        {
            "openml_id": openml_id,
            "mode": run.mode,
            "exit_code": int(run.exit_code),
            "status": "complete" if complete else "unassigned_predictions",
            "n_samples": len(truth),
            "n_unassigned": int((~finite).sum()),
            "coverage": float(finite.mean()),
            "true_k": int(np.unique(truth).size),
            "requested_k": int(options.K) if hasattr(options, "K") else np.nan,
            "k_hat": int(saved["k_hat"]),
            "predicted_k": int(np.unique(predicted[finite]).size),
            "ari": ari,
            "kmeans_ari": kmeans_ari,
            "delta_vs_kmeans": ari - kmeans_ari if complete else np.nan,
            "runtime_seconds": float(saved["runtime"]),
            "lapd_commit": str(saved["lapd_commit"]),
            "embedding_variant": str(saved["embedding_variant"]),
        }
    )

audit = pd.DataFrame(rows).sort_values(["openml_id", "mode"])
audit.to_csv(OUTPUT, index=False, float_format="%.6f")
print(f"Saved {OUTPUT.relative_to(ROOT)}: {len(audit)} runs")
print(audit.groupby(["mode", "status"]).size().to_string())
