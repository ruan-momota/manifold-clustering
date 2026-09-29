# Master Thesis Topic: Multi-Manifold Clustering for Tabular Data

## Introduction

Clustering high-dimensional data is a challenging task because, as the dimensionality increases, data points tend to become increasingly similar in the original feature space. Despite their high ambient dimensionality, many real-world datasets are believed to lie on low-dimensional structures.

Most state-of-the-art deep clustering methods assume that the data lie in a union of linear (or affine) subspaces and therefore propose various deep subspace clustering approaches. However, a recent study [1] suggests that image data are more accurately modeled as lying on a union of multiple nonlinear manifolds rather than linear subspaces. This observation naturally leads to the following research questions.

## Research Questions

- To what extent can neural networks transform data from nonlinear manifolds into latent linear (or affine) subspaces?
- Can clustering methods that explicitly model data as a union of multiple manifolds outperform methods based on the union-of-subspaces assumption?

While most existing work evaluates these methods on image datasets, tabular data remain relatively underexplored. Motivated by the recent success of tabular foundation models, this thesis investigates whether embeddings extracted from pretrained tabular foundation models, such as ZEUS (Zero-shot Embeddings for Unsupervised Separation of Tabular Data), can improve the performance of state-of-the-art clustering algorithms.

Specifically, the project will evaluate pretrained ZEUS embeddings in combination with modern clustering methods, including:

- CPP (Image Clustering via the Principle of Rate Reduction in the Age of Pretrained Models)
- TEMI (Exploring the Limits of Deep Image Clustering Using Pretrained Models)
- LAPD (Robust Multi-Manifold Clustering via Simplex Paths)

The objective is to investigate whether pretrained tabular embeddings provide a suitable representation for both subspace clustering and multi-manifold clustering methods.

## Experimental Plan

1. Reproduce the results of Robust Multi-Manifold Clustering via Simplex Paths (LAPD) on its original benchmark image datasets (e.g., COIL-20 and USPS).
2. Apply LAPD to embeddings extracted by ZEUS from the OpenML tabular datasets listed in Appendix D (Table 6) of the ZEUS paper.
3. Reproduce the results of CPP and conduct a feasibility study on applying CPP to ZEUS embeddings for tabular data.
4. Compare the performance of subspace clustering methods (e.g., CPP) and multi-manifold clustering methods (e.g., LAPD) on pretrained tabular embeddings to evaluate the validity of the underlying geometric assumptions.

## References

[1] Brown, B. C., Caterini, A. L., Ross, B. L., Cresswell, J. C., & Loaiza-Ganem, G. (2023). Verifying the Union of Manifolds Hypothesis for Image Data. International Conference on Learning Representations (ICLR).
[2] Chen, H., Little, A., & Narayan, A. (2025). Robust Multi-Manifold Clustering via Simplex Paths. arXiv preprint arXiv:2507.10710.
Link to code: 
- LAPD: https://github.com/HYfromLA/LAPD 
    - paper: https://arxiv.org/html/2507.10710v1
- ZEUS: https://github.com/gmum/zeus 
    - paper: https://arxiv.org/html/2505.10704v2
- CPP:  https://github.com/leslietrue/cpp 
    - paper: https://arxiv.org/html/2306.05272v5
- TEMI: https://github.com/HHU-MMBS/TEMI-official-BMVC2023
