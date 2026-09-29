"""Export saved ZEUS embeddings as MATLAB v5 files for LAPD."""

import argparse
from pathlib import Path

import numpy as np
from scipy.io import savemat


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "embeddings"
OUTPUT_DIR = ROOT / "data" / "lapd_mat"


def export(openml_id: int, variant: str) -> Path:
    source = SOURCE_DIR / f"openml_{openml_id}.npz"
    key = "embeddings_scaled" if variant == "scaled" else "embeddings"
    with np.load(source) as saved:
        if int(saved["openml_id"]) != openml_id:
            raise ValueError(f"ID mismatch in {source}")
        x = np.asarray(saved[key], dtype=np.float64)
        labels = np.asarray(saved["labels"]).reshape(-1)
        indices = np.asarray(saved["sample_indices"]).reshape(-1)
    if x.ndim != 2 or x.shape[1] != 512 or len(x) != len(labels):
        raise ValueError(f"Unexpected shape in {source}: {x.shape}, labels={len(labels)}")
    if not np.isfinite(x).all() or not np.array_equal(indices, np.arange(len(x))):
        raise ValueError(f"Nonfinite values or sample-order mismatch in {source}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"openml_{openml_id}_{variant}.mat"
    savemat(
        output,
        {
            "X": x,
            "labelsGT": labels.reshape(-1, 1),
            "sample_indices": indices.reshape(-1, 1),
            "openml_id": openml_id,
            "embedding_variant": variant,
        },
        do_compression=True,
    )
    print(f"{output.relative_to(ROOT)}: X={x.shape}, clusters={np.unique(labels).size}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--ids", nargs="+", type=int)
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--variant", choices=("scaled", "raw"), default="scaled")
    args = parser.parse_args()
    ids = (
        [int(path.stem.split("_")[1]) for path in sorted(SOURCE_DIR.glob("openml_*.npz"))]
        if args.all
        else args.ids
    )
    if not ids:
        parser.error("No embedding files found")
    for openml_id in ids:
        export(openml_id, args.variant)


if __name__ == "__main__":
    main()
