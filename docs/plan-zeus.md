# ZEUS 阶段计划

## 目标与边界

本阶段先把预训练 ZEUS 用作表格数据的特征提取器：从论文列出的 OpenML 数据集读取数据，得到每个样本的 ZEUS 向量，复现一个 ZEUS + K-means 基线，并保存向量供后续 LAPD、CPP 使用。这里的“向量”就是模型为每条记录生成的一组数；后续算法可以在同一组数上比较。

先不重新训练 ZEUS，也不在此阶段实现 LAPD、CPP 或 TEMI。先用 1～2 个数据集跑通，再扩展到论文附录 D 表 6 的 34 个 OpenML ID。论文的 34 个数据集经过“至少一种方法达到一定聚类效果”的筛选；后续结论应说明这一点，不能直接推广到所有表格数据。

## 项目起步

在仓库根目录使用 Python 3.11 和 uv 管理环境。项目已用 `uv init --bare --python 3.11` 初始化，并通过 `uv python pin 3.11` 固定解释器；`pyproject.toml` 记录直接依赖，`uv.lock` 固定实际解析出的版本，二者应提交；`.venv/` 不提交。当前 PyTorch 使用官方 CPU 包源的 2.5.1 版。以后在新环境中执行：[uv 项目文档](https://docs.astral.sh/uv/guides/projects/)

```bash
uv sync
uv run jupyter lab
```

只保留实际运行所需依赖；项目中的部分依赖来自 ZEUS 原仓库，以实际导入和版本兼容结果为准，不机械复制其旧 `requirements.txt`。当前机器无法使用 NVIDIA 驱动，因此先用 CPU；将来若使用 CUDA，再按 [uv 的 PyTorch 指南](https://docs.astral.sh/uv/guides/integration/pytorch/)调整 PyTorch 来源。

Jupyter 打开后选择本项目 `.venv` 的 Python 作为 kernel。若在 VS Code 中选择 notebook 内核，`ipykernel` 已作为开发依赖安装；命令行启动方式见 [uv 的 Jupyter 指南](https://docs.astral.sh/uv/guides/integration/jupyter/)。日常用 `uv add` 增减依赖、`uv run` 运行命令，避免在 notebook 里临时安装包后忘记记录。

建议目录逐步形成，不预先创建空模块：

```text
manifold-clustering/
├── docs/
│   ├── proposals_draft.md
│   └── plan-zeus.md
├── notebooks/
│   ├── 01_zeus_smoke.ipynb       # 单个数据集：读取、提取、观察
│   └── 02_zeus_openml.ipynb      # 多数据集：基线和结果汇总
├── src/                        # 稳定后才创建
│   └── zeus_embeddings.py       # 经常复用的读取与提取逻辑
├── data/                       # 下载数据、缓存和提取结果；不提交大文件
│   └── embeddings/
├── models/                     # 下载的 ZEUS 权重；不提交
├── vendor/zeus/                # 官方源码的本地副本；记录其 commit
├── pyproject.toml
├── uv.lock
└── .python-version
```

初期 notebook 可以在开头把 `vendor/zeus/` 加入 Python 导入路径，直接调用官方源码，不必立刻封装成包。`vendor/zeus/` 只放官方代码，不在其中开发自己的逻辑；记录其 Git commit 和权重来源，便于重做实验。`.gitignore` 忽略 `.venv/`、`data/`、`models/`、`vendor/zeus/` 和 notebook 的自动检查点；保留 notebook、项目依赖文件及小型结果表。若将来需要长期固定官方源码，再决定是否纳入版本控制。

## 按顺序实施

### 1. 跑通官方模型

已从 [ZEUS 官方仓库](https://github.com/gmum/zeus)获取源码和 README 所链接的预训练权重；源码 commit、权重来源和下载日期记录在 `notebooks/01_zeus_smoke.ipynb`。该 notebook 已确认权重能在 CPU 上加载并完成一次推理，输出每个样本的 512 维向量。官方配置默认 `cuda:0`，此处显式设为 `cpu`。此阶段不运行训练入口 `pretrain.py`，也不先跑完整的官方评估脚本；该脚本会启用 W&B 日志和批量评估。

### 2. 在 notebook 中提取一个数据集

`01_zeus_smoke.ipynb` 先选 OpenML ID 61（Iris，150 条、4 个数值特征），再选一个维度超过 30 的数据集，例如 ID 14，覆盖“补零”和“PCA 压到 30 维”两种输入路径。数据处理尽量沿用官方 `load_real_datasets` / `evaluate_model` 的顺序：数值缺失值填补与缩放、类别缺失值填补与 one-hot、超过 30 维时 PCA、少于 30 维时补零。记录原始行数、处理后维度、模型输入形状、输出形状及运行设备；确保输出向量行数等于样本数，且数值有限。

官方评估把整张表作为模型输入，输出中还包含簇中心对应的向量，因此保存前只取样本对应的部分。保存两种表征：ZEUS 原始样本向量；以及按官方 K-means 路径缩放到 `[-1, 1]` 的向量。不要在提取阶段把它们混为一种，以便后续判断缩放对 LAPD、CPP 的影响。[官方数据处理](https://github.com/gmum/zeus/blob/main/zeus/datasets.py)、[官方评估逻辑](https://github.com/gmum/zeus/blob/main/zeus/utils.py)

### 3. 建立最小比较基线

同一数据集上运行 K-means：一次用处理后的原始表格特征，一次用官方方式缩放后的 ZEUS 向量。先固定一个随机种子，使用调整兰德指数（ARI）比较聚类结果与真实标签；ARI 衡量两种分组的一致程度。保留数据集 ID、样本数、簇数、种子、预处理及得分。论文结果使用多个种子并以 `ARI × 100` 展示，因此对照论文表格时先统一量纲；初期的单次得分只用于确认流程，不宣称完整复现。[ZEUS 论文实验设置](https://arxiv.org/html/2505.10704v2)

为了先比较表征，初期可像官方评估一样用真实类别数指定 K-means 的簇数；这属于评估条件，必须在结果中明确标出。真实标签只用于指定这个预先约定的簇数和计算 ARI，不能用于特征预处理、挑选最优向量或逐数据集调参。若后续研究不预知簇数，再单独设计对应实验，不在第一版代码中塞入多个选簇方案。

### 4. 扩展与保存

`02_zeus_openml.ipynb` 使用论文附录 D 表 6 的 34 个 ID（官方源码 `openml_ids` 也列出了它们），逐个提取向量并汇总成一个小型 CSV。每个数据集单独保存 `.npz`，包含原始 ZEUS 向量、缩放后的向量、真实标签及样本顺序；文件名包含 OpenML ID。旁边的结果表记录 ID、样本数、维度、簇数、随机种子、源码 commit、权重标识和 ARI。保持样本顺序一致，后续方法直接复用这些文件，避免每跑一种算法都重新下载与推理。

先检查少量数据集的输入输出和得分，再运行全部 34 个。若结果与论文差异较大，优先核对权重、PCA/缩放顺序、输出切片、K-means 设置和随机种子；不急于增加复杂的异常处理。只有需要重做论文报告时，才加入多个种子并汇总均值或离散程度。

### 5. 稳定后固定为 Python 文件

当两个 notebook 的数据读取、预处理和向量提取流程不再频繁改动，再把重复且独立的步骤移到 `src/zeus_embeddings.py`。到这一步让 notebook 的导入路径包含 `src/` 即可，无需另套一层同名项目目录；文件名避开官方的 `zeus` 包。保持少量清楚的函数，例如“加载指定 OpenML ID”“用固定权重提取向量”“保存结果”；notebook 留作调用、图表和实验记录。只为已经出现的复用需求抽取函数，不提前设计通用数据框架、配置系统或大量备选实现。后续 LAPD、CPP 读同一份 `.npz`，各自的算法代码再按需要增加。

## 本阶段完成标准

- Python 3.11 + uv 环境能打开并运行 notebook，依赖文件可在新环境中恢复。
- 官方预训练权重能对至少两个不同维度的 OpenML 数据集输出与样本一一对应的向量。
- 有原始特征 K-means 与 ZEUS 向量 K-means 的 ARI 对比，结果写明簇数来源和随机种子。
- 34 个数据集的向量与简明结果表能够保存，后续聚类方法可以按 ID 读取相同样本顺序的数据。

## 主要依据

- [毕设草案](proposals_draft.md)
- [ZEUS 论文，含附录 D 数据集表](https://arxiv.org/html/2505.10704v2)
- [ZEUS 官方代码与权重入口](https://github.com/gmum/zeus)
- [uv 项目与 Jupyter 使用文档](https://docs.astral.sh/uv/guides/projects/)
