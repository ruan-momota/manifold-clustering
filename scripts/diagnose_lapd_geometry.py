"""Inspect Iris local structures before LAPD's weighted graph and denoising."""

from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import cdist


ROOT = Path(__file__).resolve().parents[1]
with np.load(ROOT / "data/embeddings/openml_61.npz") as saved:
    features = saved["embeddings_scaled"].astype(np.float64)

distances = cdist(features, features)
order = np.argsort(distances, axis=1, kind="stable")
# epsilon=0: skip self and identical vectors, then take bandwidth=10 neighbors.
neighbors = [row[distances[i, row] > 0][:10] for i, row in enumerate(order)]
sknn = int(np.floor(10 * np.log(len(features))))
rows = []

for d in [1, 2, 3]:
    quality_filter = 1.25 + 0.15 * (d - 2)
    structures = set()
    for i, nearest in enumerate(neighbors):
        for chosen in combinations(nearest, d):
            nodes = tuple(sorted((i, *chosen)))
            lengths = [distances[a, b] for a, b in combinations(nodes, 2)]
            if d == 1 or (min(lengths) > 0 and max(lengths) / min(lengths) <= quality_filter):
                structures.add(nodes)
    structures = sorted(structures)

    faces = defaultdict(list)
    for index, nodes in enumerate(structures):
        for face in combinations(nodes, d):
            faces[face].append(index)
    edges = [edge for indices in faces.values() for edge in combinations(indices, 2)]
    source, target = zip(*edges)
    graph = coo_matrix(
        (np.ones(len(edges)), (source, target)),
        shape=(len(structures), len(structures)),
    ).tocsr()
    n_components, groups = connected_components(graph, directed=False)
    sizes = np.bincount(groups)
    # This graph includes all shared-face edges, so it bounds weighted connectivity.
    eligible = sizes[groups] >= sknn
    covered = {node for nodes, keep in zip(structures, eligible) if keep for node in nodes}
    rows.append({
        "openml_id": 61,
        "d": d,
        "quality_filter": quality_filter if d > 1 else np.nan,
        "n_structures": len(structures),
        "n_nodes_in_structures": len({node for nodes in structures for node in nodes}),
        "n_components": n_components,
        "largest_component": int(sizes.max()),
        "sknn": sknn,
        "fraction_in_components_ge_sknn": float(eligible.mean()),
        "max_nodes_covered_ge_sknn": len(covered),
        "max_coverage_ge_sknn": len(covered) / len(features),
    })

report = pd.DataFrame(rows)
output = ROOT / "results/lapd_d_geometry.csv"
report.to_csv(output, index=False, float_format="%.6f")
print(f"Samples: {len(features)}; unique vectors: {len(np.unique(features, axis=0))}")
print(report.to_string(index=False))
print(f"Saved {output.relative_to(ROOT)}")
