# WMC 阶段计划

当前进度：实现保留在 `notebooks/08_wmc_zeus_openml.ipynb`，尚未抽取到 `.py`。已使用同一组参数完成全部 34 个数据集，均保存完整预测，平均 ARI 为 0.014943；33 张图的独立部分数超过目标组数，运行中还出现 Lasso 数值警告。ID 61、ID 14 的连接矩阵已与本地原实现直接核对，最大绝对差均为 0。[结果总结](../summary/wmc_summary.md)记录同批比较和限制。下一步先分析连接稀疏程度与求解器的数值表现。

## 为什么值得做

值得把 WMC 加入现有实验。当前已有 K-means、CPP 和 LAPD，但 LAPD 在 ZEUS 向量上的初始结果较低，还有部分样本没有预测。加入另一种流形聚类方法，可以进一步观察：这是当前 LAPD 设置的局限，还是这批向量对利用局部几何关系的算法都不太有利。

WMC 的想法是用其他样本的加权组合重建每个样本，并让较远的样本更难被选中；它还鼓励组合系数的总和接近 1，使附近样本能够近似描述一小段弯曲结构。随后把重建系数转成样本之间的连接强度，再用谱聚类分组。谱聚类在这里就是先根据这些连接生成新的表示，再做 K-means。[论文第 2 节与 Algorithm 1](https://proceedings.neurips.cc/paper_files/paper/2024/file/e8b782d03c623e3e587fdbcc521dd581-Paper-Conference.pdf)

它与 LAPD 构造连接的方式不同，也不像 CPP 那样训练神经网络来调整表示。因此，WMC 能补充一个直接使用固定 ZEUS 向量的对照。不过，聚类得分的高低只能反映这些方法在当前输入和参数下的表现，不能单独证明数据属于线性子空间或非线性流形。

## 本阶段范围

首轮只做 **L-WMC**，即用线性距离权重的版本。直接读取已有的 `embeddings_scaled`，先跑通两个数据集，再扩展到全部 34 个 OpenML 数据集。真实类别数只用于指定最终聚类组数，标签不参与重建或参数选择。

本阶段不要求完整复现 CIFAR 图像实验，不重新提取 ZEUS 向量，也不训练 ZEUS。首轮完成后，再决定是否需要多种子或参数敏感性实验；暂不把这些备选流程写入运行代码。

## 源码现状与采用方式

实际源码目录是 `vendor/WMC/NeurIPS2024-Manifold/`。重点参考：

- `readme.md`：运行步骤。
- `utils/selfrepresentation.py`：重建系数、求解过程和连接矩阵。
- `exps/240301-benchmark-mc.py`：原实验的参数与调用方式。
- `exps/240329_MC_generate_affinity.py`：连接矩阵的后处理实验。

本地 HEAD 是 `2be324a659a66997403b667e3257e51b0d421c60`，远程地址为 `https://github.com/tianjiaoding/subspace-clustering.git`，但工作区存在修改、删除和新增文件，包括修改过的核心实现。这个 commit 不能独立标识当前使用的代码。保留现有副本，开始实验时记录上述信息及核心文件的 SHA-256，并在项目代码中注明所参考的函数和实际改动，不把本地修改描述为干净的官方版本。

有三处需要作出明确选择：

1. **只采用线性权重。** 本地指数分支先把距离除以距离总和，再计算 `exp(w² / 0.5) / exp(1 / 0.5)`；它与论文第 3.2.2 节的指数权重写法不同。L-WMC 对应 `expW=False`，避免在首轮引入这一差异。
2. **只保留一个求解器。** 使用源码已有的 scikit-learn `lasso_lars` 路径，设置 `tau=1`。当前环境没有 `spams`，而核心文件在顶层直接导入它，因此不能原样导入整个模块。抽取实际使用的核心函数，去掉未使用的 SPAMS 分支和依赖；不为此增加 SPAMS、CLIP、图像加载或合成数据绘图依赖。
3. **固定参数和后处理。** 原脚本遍历参数与后处理组合，并根据真实标签记录最佳结果。表格主实验不沿用这种选优方式，不逐数据集取最高 ARI。

## 首轮设置

| 项目 | 设置与含义 |
| --- | --- |
| 输入 | `data/embeddings/openml_<id>.npz` 中的 `embeddings_scaled`；样本 × 512 维，保持缓存顺序 |
| 额外预处理 | 不再做 PCA、白化或逐样本归一化 |
| 方法 | L-WMC，按源码计算线性距离权重 |
| `gamma` | 50；控制重建与稀疏性的平衡，保留源码按每个样本计算实际惩罚强度的方式 |
| `eta` | 20；鼓励重建系数总和接近 1 |
| `tau` | 1；使用加权稀疏重建，不加入额外的弹性网项 |
| 求解 | `lasso_lars`，启用源码的工作集搜索；先对一部分候选样本求解，再按需要扩充候选集 |
| 工作集设置 | 沿用源码默认的 `support_size=100`、`maxiter=40` |
| 系数保留 | 沿用源码每行最多保留 50 个非零系数；重建时排除样本自身 |
| 连接矩阵 | 沿用源码：系数矩阵逐行做 L2 归一化，再取绝对值并与转置求平均 |
| 最终分组 | scikit-learn `SpectralClustering`，输入上述连接矩阵，`assign_labels='kmeans'`、`n_init=100` |
| 组数与随机性 | 真实类别数作为 `n_clusters`，`random_state=42` |
| 主指标 | ARI，与现有单种子结果比较 |

`gamma=50`、`eta=20` 取自论文附录 B.2 中 L-WMC 的 CIFAR-10 设置，作为统一起点，不表示它们适合所有表格数据。源码通过 `alpha=alpha0/gamma` 设置求解器惩罚强度，不能把 `gamma=50` 直接当成求解器的 `alpha=50`。[论文附录 B.2](https://proceedings.neurips.cc/paper_files/paper/2024/file/e8b782d03c623e3e587fdbcc521dd581-Paper-Conference.pdf)

最后一步采用与现有 CPP 实验一致的 scikit-learn 谱聚类入口；原 WMC 类自行求特征向量并调用 K-means，两条路径的细节不完全相同。记录这一替换，将本阶段称为“L-WMC 接入 ZEUS 的初始实验”，不称为论文数值复现。

## 按顺序实施

### 1. 写最小实现并跑通两个数据集

先在 `notebooks/08_wmc_zeus_openml.ipynb` 中编写最小实现，从本地源码整理 `active_support_elastic_net` 和 `elastic_net_manifold_clustering` 中实际使用的计算，保留线性权重、系数总和惩罚、工作集更新和系数还原。只保留 `lasso_lars` 路径，不复制整套估计器类及其他聚类算法。代码稳定、确实需要复用后，再把算法函数固定到 `src/wmc.py`。

对外提供一个清楚的 `wmc_affinity(X, gamma=50, eta=20)` 函数，返回稀疏连接矩阵。算法函数不接受真实标签，不读取数据文件，也不负责绘图。这样以后更换输入或单独研究参数时，只需再次调用同一个函数。

同一个 notebook 负责读取缓存、调用 WMC、谱聚类、计时、评分和保存。参数集中写在开头，先按顺序运行 ID 61（150 条）和 ID 14（2,000 条），将试跑结果写入 `results/wmc_zeus_smoke.csv`。两者覆盖小数据集和当前较大的样本规模，足以观察 CPU 耗时。

只检查当前流程需要的内容：输入行数与标签、索引一致，数值有限；连接矩阵有限、对称且没有自连接；最终每个样本有一个预测。遇到全零连接或求解不收敛，直接记录并分析，不自动切换算法、改参数或用标签补救。不为这一步搭建测试框架。

### 2. 扩展到 34 个数据集

两次试跑能正常完成、耗时可接受后，使用同一组参数处理已有的全部 34 份缓存。目前每份最多 2,000 条样本，先用 CPU 顺序运行；WMC 需要为每个样本分别求解，不能根据 CPP 的运行时间推断它也会同样快。

连接矩阵保持稀疏格式，不默认保存或转成完整稠密矩阵。保存预测即可，不需要模型检查点、并行调度或断点恢复系统。若个别数据集无法完成，在外层循环记录该项失败原因并继续；失败项保留在汇总表中。

输出约定：

- `data/wmc_zeus/openml_<id>.npz`：预测、标签和原始 `sample_indices`。
- `results/wmc_zeus_openml.csv`：每个数据集一行，记录样本数、请求与实际组数、ARI、重建和聚类耗时、参数、种子、输入版本、源码标识及运行状态。
- `summary/wmc_summary.md`：说明采用的实现、覆盖范围与主要结果。

大文件沿用现有 `data/` 忽略规则。核心源码来源和固定求解设置在 notebook 或总结中记录一次即可，不为每个数据集重复生成完整环境报告。

### 3. 与现有方法比较

首先与 `results/zeus_openml_baseline.csv` 中 `method='scaled_zeus'` 的单种子 K-means，以及 `results/cpp_zeus_openml.csv` 比较。如果 WMC 全部成功，报告全体 34 个数据集的平均 ARI、逐数据集差值和胜平负数量；沿用 CPP 总结中 `1e-6` 的近似相同阈值。

与 LAPD 比较时，只用 `results/lapd_stage4_audit.csv` 中“提供 K”且预测完整的结果，并与 WMC、CPP、K-means 按 OpenML ID 取交集。若 WMC 全部成功，这一交集应为现有的 27 个数据集。所有方法的均值都在同一个交集上重算，同时写出覆盖数量，不能把 WMC 的 34 项均值与 LAPD 的 27 项均值直接排成排名。

先做一张逐数据集表和一张同批数据的均值图即可。只对实际数据行计算均值，不把汇总 CSV 中已有的 Mean 行再次当作数据集。LAPD 提供 K 不保证输出恰好 K 个簇，这个区别继续说明。

### 4. 根据结果决定后续实验

首轮结束后，再决定是否补做多种子或少量统一参数设置。若 WMC 与现有方法有值得解释的差异，可以进一步检查局部连接或输入缩放的影响。若需要单独判断距离权重是否有帮助，再增加同一求解流程下不使用距离权重的对照，而不是只从 WMC 与 CPP 的分数差推断原因。

这些属于后续研究决策。首轮代码保持一条清楚的运行路径，不提前加入指数权重、未知组数、全部后处理排列或逐数据集调参入口。

## 完成标准

- ID 61、ID 14 的 CPU 试跑完成，并记录参数、耗时和预测。
- 34 个数据集各有完整预测与 ARI，或明确的失败记录。
- 源码来源、本地修改标识与项目实际采用的计算可以追溯。
- 与 K-means、CPP、LAPD 的比较使用相同数据集，并注明已知组数条件。
- 初期实现集中在一个实验 notebook，稳定后再抽取小型算法文件；说明文字能区分初始实验与论文复现。

## 主要依据

- [用户提供的论文入口](https://openreview.net/pdf?id=nBQHTBVnfr)；本次该入口触发浏览器验证，正文通过 [NeurIPS 2024 正式论文](https://proceedings.neurips.cc/paper_files/paper/2024/file/e8b782d03c623e3e587fdbcc521dd581-Paper-Conference.pdf)阅读。
- 本地源码：[说明](../vendor/WMC/NeurIPS2024-Manifold/readme.md)、[核心实现](../vendor/WMC/NeurIPS2024-Manifold/utils/selfrepresentation.py)、[原实验入口](../vendor/WMC/NeurIPS2024-Manifold/exps/240301-benchmark-mc.py)。
- 现有结果：[ZEUS](../summary/zeus_summary.md)、[CPP](../summary/cpp_summary.md)、[LAPD](../summary/lapd_summary.md)。
