# CPP 阶段计划

## 目标

先用官方代码复现一个图像数据集上的 CPP 结果，再让 CPP 读取本项目已有的 ZEUS 向量，最后与同一批数据上的 ZEUS + K-means 和 LAPD 比较。本阶段关注聚类预测，不做论文中的图像文字描述和图像检索。

CPP 使用预训练模型生成的特征，再训练两个分支：一个调整特征，另一个计算样本之间的关联。训练希望同组样本的特征形成较紧凑的结构，不同组更容易区分；最后根据样本关联做谱聚类。论文还提供了估计组数的方法，但已知组数的实验可以先独立完成。[论文方法](https://arxiv.org/html/2306.05272v5#S3)、[官方仓库](https://github.com/LeslieTrue/CPP)

## 开始前核对源码

固定官方仓库的 commit，先读 `README.md`、`main.py`、`main_efficient.py`、`model/CPP_model.py`、`loss/loss_fn.py` 和聚类评估代码。官方仓库提供原始图像和预提取 CLIP 特征两种入口；ZEUS 已有每个样本的向量，应走后者。官方特征入口把输入维数写为 768，启动时仍加载 CLIP，而 ZEUS 向量是 512 维。训练入口默认 `drop_last=True`、批量大小较大；小数据集可能一个训练批次都没有。[官方 README](https://github.com/LeslieTrue/CPP#readme)、[特征训练入口](https://github.com/LeslieTrue/CPP/blob/main/main_efficient.py)

源码的两个训练入口还有差别：`main_efficient.py` 在前向计算后用 `logits = z` 覆盖了聚类分支的输出，`main.py` 没有这一句。先以 `main.py` 的训练逻辑和论文描述为依据核对结果，记录任何必要修正；不能把两个入口的结果当成同一实现。官方训练脚本只在部分批次上即时评估并保存模型，完整数据集的预测需另写简短入口。[两个训练入口](https://github.com/LeslieTrue/CPP/blob/main/main.py)、[网络结构](https://github.com/LeslieTrue/CPP/blob/main/model/CPP_model.py)

## 按顺序实施

### 1. 复现一个官方实验

优先选 README 给出命令的 CIFAR-10，沿用论文对应的 CLIP 特征、网络结构、训练参数、数据划分和聚类准确率，记录官方 commit、环境、随机种子与耗时。先确保训练和预测流程可运行，再与论文数值比较。若机器资源不足以完成论文规模的实验，记录已跑通的步骤和资源限制，不把缩小后的试跑称为论文复现。论文的图像准确率与本项目表格数据的 ARI 是不同指标。[官方运行说明](https://github.com/LeslieTrue/CPP#training)、[论文实验与训练细节](https://arxiv.org/html/2306.05272v5#S4)

### 2. 接入 ZEUS 向量

从 `data/embeddings/openml_<id>.npz` 读取 `embeddings_scaled`，保持原有样本顺序。先用 ID 61（150 条）和 ID 14（2000 条）检查输入、训练、预测和保存结果，再扩展到全部 34 个数据集。输入层改为 512 维，直接使用无 CLIP 主干的 `CPPNet`；按实际样本数设置批量大小并保留最后一个批次。标签只用于确定已知组数协议的组数，以及训练结束后的评分，不进入训练损失或参数选择。

从官方实现保留必要的网络、损失、样本关联计算和谱聚类。写一个清楚的 ZEUS 数据读取与运行入口即可；不复制图像数据管线，不预先搭建通用训练框架。训练时记录输入版本、参数、种子和模型；预测时按原样本顺序保存逐样本结果。样本关联矩阵随批量大小按平方增长，先观察 ID 14 的内存和时间，再决定 34 个数据集的运行批量。

### 3. 做可比的实验

主实验使用真实类别数作为谱聚类组数，与现有 ZEUS + K-means 的条件一致；每个数据集独立训练，不用真实标签挑选效果最好的参数。先固定一组有依据的参数跑完 34 个 ID，再按需要检查随机种子带来的差异。不要把不同输入缩放、组数设置或训练参数的结果混在同一均值里。

主指标用 ARI。逐数据集记录 CPP 的 ARI、预测组数、运行时间和失败原因，并与 `results/zeus_openml_baseline.csv` 中同一数据集的 ZEUS + K-means 比较。与 LAPD 比较时，只在双方都有完整预测的同一批数据集上计算均值，同时报告覆盖数量；LAPD 已有的未分配预测不能略过。[ZEUS 结果](../summary/zeus_summary.md)、[LAPD 结果](../summary/lapd_summary.md)

### 4. 再研究未知组数

已知组数实验稳定后，再单独运行论文和 `optimalcluster.py` 的组数估计方法。它是在训练后比较不同组数的结果，不需要为每个候选组数重新训练。单独报告估计组数与 ARI，并与 LAPD 的自行估计组数实验比较；不把真实类别数用于选择候选组数。[论文组数估计](https://arxiv.org/html/2306.05272v5#S3.SS3)、[官方脚本](https://github.com/LeslieTrue/CPP/blob/main/optimalcluster.py)

## 完成标准

- 官方图像实验有可追溯的运行记录，并清楚说明与论文设置和结果的差异。
- 34 个 OpenML 数据集各有 CPP 预测和指标，或明确的失败记录。
- CPP、ZEUS + K-means、LAPD 的比较使用相同数据集和可比的组数条件；已知组数与估计组数分别报告。
- 代码只包含实际用到的数据读取、CPP 训练、预测和结果保存；官方代码版本及必要改动有记录。

## 主要依据

- [毕设草案](proposals_draft.md)
- [CPP 论文](https://arxiv.org/html/2306.05272v5)
- [CPP 官方源码](https://github.com/LeslieTrue/CPP)
