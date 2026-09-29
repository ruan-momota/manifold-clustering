# LAPD 结果总结

## 论文示例复现

先用官方 LAPD 的双侧权重设置运行完整类别的 COIL20 和 USPS。这里沿用论文的**聚类准确率**：

| 数据集 | [论文 Table 3](https://arxiv.org/html/2507.10710v1) | [本地复现](../results/lapd_paper_reproduction.png) |
| --- | ---: | ---: |
| COIL20，20 类 | 0.9040 | 0.9028 |
| USPS，10 类 | 0.9350 | 0.9348 |

两项都很接近论文值，说明官方示例在当前 MATLAB 环境中能够复现。对应的[原始结果文件](../results/lapd_returns/stage1/lapd/)保留了预测、参数和耗时。

## OpenML34 实验

接着把 LAPD 用于 ZEUS 已保存的 34 份向量，并与同一向量上的 ZEUS + K-means 比较。这里改用 **ARI**。LAPD 分两种运行方式：提供真实类别数 `K`，或让算法自行估计组数。提供 `K` 也不保证最终恰好分出 `K` 组。

| LAPD 方式 | 预测完整的数据集 | LAPD 平均 ARI | 同批数据集的 ZEUS + K-means 平均 ARI |
| --- | ---: | ---: | ---: |
| 提供 `K` | 27/34 | 0.326 | 0.601 |
| 自行估计 `K` | 32/34 | 0.286 | 0.564 |

每一行的两个均值只使用该行**相同的完整数据集**；因此两行的 ZEUS 均值不同。ZEUS 没有重新运行，只对已有的单种子结果重新取平均。完整运行中，LAPD 分别在 3/27 和 2/32 个数据集上超过 ZEUS + K-means。[均值图](../results/lapd_openml34_matched_means.png)、[逐数据集图](../results/lapd_openml34_by_dataset.png)和[结果明细](../results/lapd_stage4_audit.csv)列出了比较依据。

## 结果分析与限制

68 次 MATLAB 运行都正常结束，但 9 次运行合计有 **1,681 个样本**没有得到有效预测。官方代码在样本没有可用的单纯形标签时，会尝试用近邻标签补上；如果近邻中也找不到已标注样本，这一步可能产生 `NaN`。这些运行的全样本 ARI 留空，没有把缺失样本删除后计分。[官方标签分配代码](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/cluster.m)

当前配置下，LAPD 在这些 ZEUS 向量上的结果明显低于 ZEUS + K-means；但 COIL20、USPS 示例能够接近论文值。两部分使用的数据与指标不同：示例报告准确率，OpenML34 报告 ARI。OpenML34 使用一组统一的试跑参数，尚未验证其他参数或输入方式，所以这些数字描述的是**当前实验设置**，不能代替对 LAPD 所有设置的评价。
