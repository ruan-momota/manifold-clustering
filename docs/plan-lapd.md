# LAPD 阶段计划

## 目标与现状

本阶段先复现 LAPD 官方实现的真实数据示例，再把 LAPD 用于已保存的 ZEUS 表格向量，比较 LAPD 与 ZEUS + K-means。论文总目标还包括后续 CPP 对照；本阶段不改 ZEUS 权重、不重新提取向量，也不把 LAPD 重写成 Python。

本仓库已有 34 个 OpenML 数据集的 `data/embeddings/openml_<id>.npz`。每份包含 `embeddings`、`embeddings_scaled`、`labels`、`sample_indices` 和 `processed_features`；`results/zeus_openml_baseline.csv` 是单种子 K-means 基线，`results/zeus_openml_5seeds.csv` 是缩放 ZEUS 向量的五种子结果。向量文件在 `.gitignore` 中，远程服务器不会因 `git pull` 自动得到它们。现有 ZEUS 对照采用真实类别数作为 K-means 簇数，主要指标是 ARI。

LAPD 官方仓库是 MATLAB 代码，核心函数 `Auxiliary/main.m` 接受 **样本 × 特征** 的矩阵 `X` 和参数结构 `LAPDopts`，返回内在维度、半径、估计簇数、逐样本标签、耗时及诊断信息。官方 `real_data_demo.m` 展示 COIL20、MNIST 和 USPS；论文真实数据表报告聚类准确率（accuracy），不能直接与我们的 ARI 数值比较。[官方代码](https://github.com/HYfromLA/LAPD)、[核心函数](https://github.com/HYfromLA/LAPD/blob/main/Auxiliary/main.m)、[论文 Table 3](https://arxiv.org/html/2507.10710v1)

## 运行方式：原生 MATLAB 为主

在远程服务器上以 `.m` 文件封装数据读取、LAPD 调用和结果保存，用 `matlab -batch` 从 shell 启动。数据导出与最终汇总继续用本项目的 Python 环境。这样保持官方算法调用路径，避免增加 Python–MATLAB Engine 的安装、版本匹配和跨语言数组传递环节。等到确实需要统一调度大量异构实验时，Python 才作为外层进程启动器；即使如此，LAPD 核心仍应由 MATLAB 脚本调用。`matlab -batch` 会在成功时返回 0，出错时返回非零状态，适合远程日志和批量实验。[MathWorks Linux 命令文档](https://www.mathworks.com/help/matlab/ref/matlablinux.html)

**不要直接把整个 `real_data_demo.m` 当作第一条批处理命令。** 它依次运行多个数据集；`fancy_shapes_demo.m` 还用 `input` 选择形状；官方 `main.m` 在半径过大时也会用 `input` 请求新值。先准备一个只跑一个数据集、固定参数、检查输入的非交互 `.m` 入口，再用 `-batch` 运行。若触发半径提示，应检查距离、`epsilon`、`bandwidth` 和近邻数，记录修正原因，不能由脚本读入真实标签来挑参数。[真实数据示例](https://github.com/HYfromLA/LAPD/blob/main/real_data_demo.m)、[合成数据示例](https://github.com/HYfromLA/LAPD/blob/main/fancy_shapes_demo.m)、[核心函数](https://github.com/HYfromLA/LAPD/blob/main/Auxiliary/main.m)

## 远程服务器准备

以下命令假设远程服务器为 Linux，项目放在 `~/manifold-clustering`；若实际目录不同，替换该路径。请在远程终端执行，先把输出留存，供后续确定具体运行脚本和参数。克隆仅在目录尚不存在时执行。

```bash
cd ~/manifold-clustering
mkdir -p vendor
git clone https://github.com/HYfromLA/LAPD.git vendor/LAPD
git -C vendor/LAPD rev-parse HEAD
matlab -batch "disp(version); ver; disp(which('knnsearch')); disp(which('pdist')); disp(which('parpool'))"
matlab -batch "cd('vendor/LAPD'); addpath(genpath(pwd)); disp(which('main')); disp(which('accuracy'))"
find vendor/LAPD -iname 'coil20.mat' -o -iname 'USPS.mat'
```

记录 MATLAB 版本、可用 toolbox、LAPD commit、示例数据文件路径。`knnsearch`、`pdist` 等函数需在服务器上实际解析成功；并行是可选项，第一轮使用 `parallel=0`，无需为了它先配置并行池。若 `matlab` 不在 PATH，改用服务器上的 MATLAB 可执行文件绝对路径。若远程尚无本项目仓库，先把项目同步上去；不要把 34 份本地 `.npz` 当成已经在远程。官方仓库自身的数据目录和所需 toolbox 以远程检查结果为准。

## 按顺序实施

### 1. 复现官方真实数据示例

在固定的 LAPD commit 上查看 `real_data_demo.m` 和 `Auxiliary/main.m`，确认 `.mat` 文件中 `X`、`labelsGT` 的形状，以及 `accuracy` 的定义。先单独运行 COIL20，再运行 USPS；使用 demo 中相应的 `intrdim`、`epsilon`、`bandwidth`、`weight` 等设置，记录任何与论文不同的类别子集和参数。不要一次执行整个 demo，因为它包含 MNIST 和多个清空工作区的段落。

结果保存逐样本预测、真实标签、类别子集、簇数设置、准确率、耗时及诊断量（至少 `numsimplices`、`percentkept`、`denoisingcutoff`），同时记录 MATLAB 版本、LAPD commit 和输入文件标识。与论文 Table 3 **同一类别子集、同一指标** 对照；无法复现时先核对数据文件、类别编码和参数，再考虑数值环境差异。[论文真实数据实验](https://arxiv.org/html/2507.10710v1)、[官方 demo](https://github.com/HYfromLA/LAPD/blob/main/real_data_demo.m)

### 2. 建立 ZEUS → MATLAB 数据接口

在本地用 `scipy.io.savemat` 将所需 `.npz` 转成每个 OpenML ID 一份 `.mat`，初版只导出少量数据集。`X` 为 `n × 512` 的有限浮点矩阵；主实验优先使用 `embeddings_scaled`，因为现有 ZEUS + K-means 基线也使用它。保留 `embeddings` 作为明确标记的第二种表征，用于后续敏感性分析，不在同一结果列中混用。`labelsGT`、`sample_indices` 随文件保存，用于回传后验证顺序和计算指标；**标签不参与距离、内在维度、降维或调参**。

导出时检查行数、维数、非有限值、类别数和样本索引；远程 MATLAB 加载后再次核对 `size(X,1)==numel(labelsGT)`。第一轮选 Iris（ID 61，150 条）与一个维度经 ZEUS 预处理走过 PCA 路径的数据集（如 ID 14，2000 条）。通过 `scp`/`rsync` 或既有文件传输方式单独传送 `.mat`；不要提交大向量到 Git。转置错误、标签顺序错位和重复样本会直接影响结果，因此保留源 `.npz` 的 ID 与索引以便逐行核验。

### 3. 先跑通小规模 LAPD，再扩展

在自己的 MATLAB 入口中调用 `main(X,LAPDopts)`。先设 `parallel=0`，显式记录 `intrdim`、`epsilon`、`bandwidth`、`knnnumber`、`weight`、去噪策略与随机状态。`main.m` 默认 `knnnumber=floor(0.1*n)`、`bandwidth=25`；小样本上近邻列表可能不足以覆盖带宽，因此 **不能直接沿用默认值**，需使近邻数足够并核查构图范围。`intrdim` 是流形内在维度，**不是** ZEUS 向量的 512 维；先依据无标签的诊断与官方实现确定小范围统一候选设置，不逐数据集用 ARI 选最优参数。[核心函数与默认值](https://github.com/HYfromLA/LAPD/blob/main/Auxiliary/main.m)

初始对照分两种预先声明的簇数协议：一是提供真实类别数 `K`，与现有 K-means 的评估条件一致；二是省略 `K`，记录 LAPD 自行估计的 `k_hat`。两种协议分别汇总，不能混成单一均值。先确认每个样本有一个有限、可用的预测标签；若出现未分配样本，报告数量与处理方式，不静默删去。单个数据集成功后，扩展到 34 个 ID，逐项保存预测、运行时长、参数及失败原因。

### 4. 比较与报告

表格数据主指标用 ARI，与 `results/zeus_openml_baseline.csv` 和五种子 K-means 结果比较；可以补充 NMI 与准确率，但需说明准确率是否做了标签置换匹配。官方图像复现实验仍按论文使用准确率。ZEUS 向量本身固定，不必为每个 LAPD 随机种子重新提取；若 LAPD 含随机步骤，先检查官方 `main.m` 的 `rng("default")` 是否使外部种子失效，再定义可复现的多次运行方案。报告每个 ID 的样本数、簇数协议、表征版本、LAPD 参数、ARI、`k_hat`、耗时及失败状态，最后汇总完整成功集，避免只统计成功数据集而不报告失败数。

对 512 维空间可另做无标签 PCA 降维的敏感性实验，但它是**独立的输入条件**；记录目标维数和拟合范围，不把降维后的 LAPD 与原始 512 维 LAPD 混为一项。论文给出的几何分离结论依赖采样、噪声和流形结构假设；ZEUS 表格向量是否满足这些假设要靠实验检验，不能由图像结果直接推断。[LAPD 论文方法与假设](https://arxiv.org/html/2507.10710v1)

## 阶段完成标准

- 固定并记录官方 LAPD commit 与远程 MATLAB 环境；COIL20、USPS 的至少一个论文类别子集可独立运行并按相同指标对照。
- 本地 `.npz` 到远程 `.mat` 的行顺序、形状和标签可核验；至少两份 ZEUS 数据集完成 LAPD 小规模试跑。
- 34 个数据集各有结果或明确失败记录；预测与配置可追溯，带 `K` 和估计 `k_hat` 的协议分开报告。
- 与现有 ZEUS + K-means 在同一批样本上比较 ARI，并说明输入表征、随机性和参数选择规则。

## 主要依据

- [毕设草案](proposals_draft.md)
- [LAPD 官方仓库](https://github.com/HYfromLA/LAPD)
- [LAPD 论文](https://arxiv.org/html/2507.10710v1)
- [MATLAB Linux `-batch` 文档](https://www.mathworks.com/help/matlab/ref/matlablinux.html)
