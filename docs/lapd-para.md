# LAPD 参数与实验记录

最后整理：2026-10-09。以后每次参数实验都在这里追加配置、状态和结果，保留旧记录。

本文件区分三件事：官方程序在没有传参数时的默认值、本项目实际传入的配置、各次运行的结果。**我们此前的 OpenML 配置并不是官方全默认配置。**

## 1. 官方原始默认参数

以下以实验使用的官方 commit `d678a0baa2a4d9b0134ff1719c80c42e78eda108` 为准，依据实际执行代码，而不是文件开头的参数注释。

源码入口：[main.m](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/main.m)。形状筛选：[buildsimplex.m](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/buildsimplex.m)。

下表的 `n` 是样本数，`d` 是算法使用的局部维度，`log` 是自然对数。

| 参数字段 | 未传入时的官方行为 | 简单说明 |
| --- | --- | --- |
| `intrdim` | 由 `MSVD` 估计 d | 用边、三角形或更高维结构描述局部数据 |
| `K` | 从不同尺度的分组中估计 | 希望分成多少类；提供 K 也不保证实际输出 K 类 |
| `noise_level` | 按需由 `MSVD` 估计，没有固定常数 | 辅助设置半径；已经提供 d 和 epsilon 时不必估计它 |
| `epsilon` | 根据估计噪声设置，并按近邻距离等信息限制范围 | 选邻居时排除距离不大于 epsilon 的样本 |
| `bandwidth` | `25` | 每个样本用于构建局部结构的邻居数量 |
| `knnnumber` | `floor(0.1*n)` | 预先搜索多少个邻居，供半径筛选和构建使用 |
| `weight` | `'one sided'` | 如何将结构间的角度转换为连接权重 |
| `filter` | `1.25 + 0.15*(d-2)`；d=1 时不做此形状筛选 | 最长边/最短边的上限，越大越宽松 |
| `numscales` | `100` | 用多少个连接阈值观察图的变化 |
| `denoisingmethod` | `'automatic'` | 自动确定去噪阈值；源码还支持交互式 `'examinefigure'` |
| `SKNN` | `floor(10*log(n))` | 去噪时查看结构的第几个路径近邻；不是样本近邻 |
| `componentsize` | `0.01` | 最终选择组数时，只统计占结构数至少 1% 的组 |
| `parallel` | `0` | 不启用并行 |

`epsilon` 没有单一默认数值：程序先取 `sqrt(2)*tau`，其中 tau 是噪声估计，再用数据相关的下限、上限约束它。官方默认参数会随样本数、维度和数据变化；这张表不表示它们在每个小数据集上都能直接跑通。

`main` 会调用 `rng('default')`。当前实验沿用这一随机行为。

去噪还有两个写在代码里的条件：保留的结构至少覆盖 95% 的样本，保留结构数相对 `knndistances < 5` 的计数至少为 85%。这些不是当前入口可直接传入的选项。`cutoff` 也由去噪内部计算，不能假设写 `opts.cutoff` 就会生效。[denoise.m](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/denoise.m)

## 2. 本项目现有配置

入口是 [matlab/lapd_run.m](../matlab/lapd_run.m)。下表只列入口显式设置或数据协议；未列出的参数使用上面的官方默认值。

| 参数 | COIL20 复现 | USPS 复现 | OpenML 第一轮及当前 D 检查 |
| --- | --- | --- | --- |
| 输入 | 原始 COIL20，20 类 | 原始 USPS，10 类 | 缓存的 `embeddings_scaled`，不新增降维或归一化 |
| `intrdim` | 1 | 2 | 第一轮为 1；新入口可在调用时指定或传 `[]` 自动估计 |
| `epsilon` | 0 | 0 | 0 |
| `bandwidth` | 22 | 17 | 10 |
| `knnnumber` | 官方默认 | 官方默认 | `min(n, max(100, ceil(0.1*n) + bandwidth))` |
| `weight` | `'two sided'` | `'two sided'` | `'two sided'` |
| `filter` | 未显式设置，d=1 不使用 | 1.3 | 未显式设置，随 d 使用官方默认值 |
| `componentsize` | 官方默认 0.01 | 0.008 | 官方默认 0.01 |
| `parallel` | 0 | 0 | 0 |
| `K` | 提供真实类别数 | 提供真实类别数 | `known` 提供真实类别数；`estimate` 不提供 K |

### 已完成的复现与第一轮实验

| 实验 | 配置 | 结果 |
| --- | --- | --- |
| COIL20 复现 | 上表 COIL20 配置，提供 K=20 | 聚类准确率 0.9028 |
| USPS 复现 | 上表 USPS 配置，提供 K=10 | 聚类准确率 0.9348 |
| OpenML34，提供 K | 上表 OpenML 配置，d=1 | 27/34 预测完整；这 27 个的平均 ARI 约 0.326 |
| OpenML34，估计 K | 上表 OpenML 配置，d=1 | 32/34 预测完整；这 32 个的平均 ARI 约 0.286 |

后两行使用的完整数据集集合不同，不能直接用两个均值评价哪种模式更好。两种模式都完整的同一批 25 个数据集上，提供 K 的平均 ARI 为 0.351847，估计 K 为 0.285655。

依据：[LAPD 总结](../summary/lapd_summary.md)、[第一轮逐数据集审计](../results/lapd_stage4_audit.csv)。COIL20、USPS 的准确率与 OpenML 的 ARI 是不同指标。

## 3. 参数改动记录

### D-01：Iris 手动 D 检查，已执行

目的：在同一输入和其他显式参数下，比较 d=1、2、3。d 改变时，官方默认 filter 也会随之变化。

共同配置：ID 61（Iris），150 个样本、512 维 ZEUS 缩放向量；提供 K=3；epsilon=0；bandwidth=10；knnnumber=100；weight='two sided'；parallel=0；numscales=100；denoisingmethod='automatic'；SKNN=50；componentsize=0.01。

环境：MATLAB R2022b（9.13.0.2049777）。项目 commit：`f1bd570295ff28358d5708eb2450297ce4c495cb`；官方 commit 与第 1 节一致，回传的官方 Git 状态为空。

| 运行 | d | 实际 filter | 退出码 | 预测情况 | 实际输出类数 | ARI | LAPD 耗时 |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |
| D-01a | 1 | 不使用形状筛选 | 0 | 150/150 完整 | 3 | 0.548465 | 9.416618 秒 |
| D-01b | 2 | 默认 1.25 | 1 | 去噪报错，没有预测结果 | — | — | 未保存 |
| D-01c | 3 | 默认 1.40 | 1 | 去噪报错，没有预测结果 | — | — | 未保存 |

D-01a 的逐样本预测与第一轮 Iris d=1 完全一致，标签和样本索引与缓存一致。D-01b、D-01c 都在官方 `denoise.m` 第 101 行比较距离与阈值时发生数组尺寸错误；失败不是 ARI=0，也不能据此评价准确度。

本地回传位置：[manual_smoke](../results/lapd_returns/d_check/manual_smoke/)。其中 d=1 有 `.mat`；d=2、3 只有失败日志。实际本地目录没有额外嵌套 `lapd_d_check/`。

### D-01 的补充检查，已执行

本地按官方几何构建规则检查共享面连接，结果如下。没有运行完整 Python 聚类，未计算角度权重；覆盖数字是这种连接下的上限，不是最终预测覆盖率。

| d | 结构数 | 连接部分数 | 最大部分的结构数 | 位于至少 50 个结构的部分中的比例 | 这些部分最多覆盖的样本 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 951 | 2 | 634 | 100% | 150/150 |
| 2 | 415 | 39 | 133 | 63.3735% | 101/150 |
| 3 | 65 | 24 | 16 | 0% | 0/150 |

d=2、3 的比例与远程警告打印值吻合，支持连接不足的解释。去噪要求覆盖至少 143/150 个样本，这两种配置达不到。结合源码，阈值候选耗尽或非有限阈值导致空数组是报错原因的判断；尚未保存远程报错瞬间的 cutoff。

依据：[调查说明](lapd-d-diagnosis.md)、[几何检查结果](../results/lapd_d_geometry.csv)、[检查脚本](../scripts/diagnose_lapd_geometry.py)。

### F-01：Iris d=2 放宽 filter，已执行

目的：检查 d=2 失败是否与形状筛选过严有关。只改变 filter，保留 D-01b 的其余配置。

| 项目 | D-01b | F-01 实际配置 |
| --- | --- | --- |
| d | 2 | 2 |
| filter | 默认 1.25 | 显式传入 1.50 |
| bandwidth | 10 | 10 |
| epsilon | 0 | 0 |
| knnnumber | 100 | 100 |
| K | 提供 3 | 提供 3 |
| 其余参数 | D-01 共同配置 | 相同 |
| 结果目录 | 原 manual_smoke | `results/lapd_d_check/filter_check/d2_filter150/` |
| 运行状态与结果 | 失败 | 退出码 0；150/150 预测完整；输出 3 类 |

环境：MATLAB R2022b（9.13.0.2049777），官方 commit 与第 1 节一致。项目 commit：`20b052a3d143de39b4725f6ff2b92b16162f6319`。结果中的标签和样本索引已与缓存逐项核对，实际 D=2，实际 filter=1.50，其他显式参数与 D-01b 相同。

| 比较项 | 结果 |
| --- | ---: |
| F-01 全样本 ARI | 0.562087 |
| F-01 LAPD 耗时 | 10.601109 秒 |
| 同一 Iris 的 D-01a（d=1）ARI | 0.548465 |
| F-01 相对 D-01a 的 ARI 差值 | +0.013622 |
| 同一 Iris 的 ZEUS + K-means ARI | 0.851457 |

官方结果保存的结构数为 1194，`percentkept=0.176889`，SKNN=50，去噪阈值为 0.761157。percentkept 是结构构建阶段记录的比例，不是最终样本预测覆盖率。三个预测簇分别有 50、90、10 个样本。

结论：放宽 filter 后，此前失败的 d=2 配置能够完成运行且预测完整，支持形状筛选影响连接和可运行性的解释。相比 d=1，ARI 小幅上升，但仍明显低于 K-means。由于 d=2、filter=1.25 没有成功预测，不能计算放宽 filter 带来的 ARI 提升；与 d=1 比较也不代表只改变了 filter。1.50 仍是试探值，不是已验证的最佳参数。

本地文件：[F-01 回传目录](../results/lapd_returns/d_check/filter_check/d2_filter150/)，包含 `.mat`、运行日志、状态表和项目 commit。

### F-02：Iris d=3、filter=1.50，已执行

目的：与 F-01 比较，固定 filter=1.50 和其他参数，只把 d 从 2 改成 3。

实际传入配置已从日志核对：d=3、filter=1.50、bandwidth=10、epsilon=0、knnnumber=100、weight='two sided'、K=3、parallel=0。其余字段沿用官方默认；默认 SKNN=50 也在警告中得到确认。

项目 commit：`20b052a3d143de39b4725f6ff2b92b16162f6319`，与 F-01 一致。本次回传没有成功 `.mat`，因此没有新的 MATLAB 版本或官方 commit 记录，只能按原运行流程说明沿用环境，不能从本次结果文件独立核实。

| 项目 | F-02 结果 |
| --- | --- |
| 退出码 | 1 |
| 失败位置 | 官方 `denoise.m` 第 101 行，`knndistances < cutoff` 数组尺寸错误 |
| 预测、实际输出簇数、ARI、耗时 | 未生成 `.mat`，均无结果 |
| 图连接提示 | 警告打印 0.00%；源码实际统计的是距离小于 5 的比例 |

结论：filter 从默认 1.40 放宽至 1.50 后，d=3 仍在去噪阶段失败，尚未解决当前配置的连接问题。不能将失败视为 ARI=0，也不能断言 d=3 本身不适合数据。与 F-01 的比较只能说明这两组配置的可运行性不同，无法比较聚类准确度。报错瞬间的 cutoff 和具体结构数量尚未保存。

本地文件：[F-02 回传目录](../results/lapd_returns/d_check/filter_check/d3_filter150/)，包含日志、状态表和项目 commit，没有 `.mat`。

### M-01：Iris 的 MSVD 自动维度估计，已尝试但失败

目的：先单独估计 d，了解官方自动方法的选择，再决定自动 D 聚类的配置。本次没有运行后续聚类。

配置：ID 61 的同一批 `embeddings_scaled`，转换为 double；`rng('default')`；调用 `MSVD(X,0)`，不启用并行。MSVD 内部估计选项沿用官方默认，没有改动 filter、bandwidth 或聚类参数。

项目 commit：`20b052a3d143de39b4725f6ff2b92b16162f6319`；官方 commit：`d678a0baa2a4d9b0134ff1719c80c42e78eda108`。

| 项目 | M-01 结果 |
| --- | --- |
| 退出码 | 1 |
| 失败位置 | MSVD 的近邻搜索调用 `covertreeD.mexa64` 时加载失败 |
| 直接错误 | 动态库 `libfftw3.so.3` 无法找到 |
| 估计 D、噪声、耗时 | 未返回结果，未生成 `.mat` |

这是当前服务器加载已编译程序时的依赖问题，与此前 D=3 的去噪错误不同；本次不能用于判断自动估计会选择什么 D。日志开头还出现 parfor 临时变量警告，但使进程停止的是后面的 MEX 加载错误。

下一步先在远程检查该 MEX 的动态库依赖，再处理缺失库。重试使用新的目录保留本次失败记录。

本地文件：[M-01 回传目录](../results/lapd_returns/d_check/d_estimates/)，包含日志、状态表和两份 commit 记录，没有 `.mat`。

### M-02：使用项目目录内的 FFTW 库重试 MSVD，仍失败

维度估计输入和设置与 M-01 相同。没有 sudo 权限，因此用 apt 下载 `libfftw3-double3`，通过 `dpkg-deb -x` 解包到 `data/runtime_libs/fftw/unpacked/`；仅为本次 MATLAB 进程在 LD_LIBRARY_PATH 中加入解包后的库目录，没有修改系统安装或官方源码。

FFTW 包版本：`libfftw3-double3 3.3.8-2ubuntu8`。项目和官方 commit 与 M-01 相同。

| 项目 | M-02 结果 |
| --- | --- |
| 退出码 | 1 |
| 新的失败位置 | `FastRoughSetDownsample.m` 第 192 行调用 `nn_prepare(cXt)` |
| 直接错误 | MATLAB 不支持把当前解析到的 `NearestNeighbors/nn_prepare.m` 脚本作为函数执行 |
| 估计 D、噪声、耗时 | 未生成 `.mat`，均无结果 |

此次没有再出现 FFTW 库加载错误，执行已进入后续下采样步骤。新的障碍是 nn_prepare 的可执行函数解析：可能缺少当前 Linux 平台可用的 MEX，或该文件没有正确加入路径，需进一步检查文件列表和 MATLAB 解析结果。不能把本次错误归因于数据或估计维度。parfor 临时变量警告仍存在，但进程停止于 nn_prepare 错误。

本地文件：[M-02 回传目录](../results/lapd_returns/d_check/d_estimates_userlib/)，包含日志、状态、FFTW 包版本及两份 commit 记录，没有 `.mat`。

后续远程检查已确认：NearestNeighbors 目录中只有 nn_prepare.m、nn_search.m 的脚本文件、macOS 的 `.mexmaci64` 文件及 nn_search.dll；当前 MATLAB 的 mexext 为 `.mexa64`，which -all 仅解析到两个 `.m`。因此不是现有 Linux 文件没有加入路径，而是缺少当前平台的编译版本。

下一步检查服务器的 C++ 编译器与 MATLAB MEX 编译配置，再取得对应模块源码编译 Linux 版本。macOS 的编译文件不能通过改后缀变成 Linux 文件。

后续已确认编译条件：服务器为 g++ 11.4.0；MATLAB R2022b 的 Installed 和 Selected C++ 编译器都指向 `/usr/bin/g++`。

### Linux 近邻模块补充：待编译验证

采用保留 OpenTSTOOL 源码的 [MuTE 仓库](https://github.com/mapefast/mute_neurips/tree/2ef31a09a681ad58a9bbbf17c6ea8785ec9e5fb5/OpenTSTOOL)，固定 commit 为 `2ef31a09a681ad58a9bbbf17c6ea8785ec9e5fb5`。原 [makemex.m](https://github.com/mapefast/mute_neurips/blob/2ef31a09a681ad58a9bbbf17c6ea8785ec9e5fb5/OpenTSTOOL/mex-dev/makemex.m) 给出了 NN 模块的头文件路径及 PARTIAL_SEARCH 编译选项。

本项目新增 [build_lapd_neighbors.m](../matlab/build_lapd_neighbors.m)，只编译 nn_prepare、nn_search、range_search 三个文件。使用旧数组接口及 C++11 兼容选项，生成文件放在远程 LAPD 的 NearestNeighbors 目录，与原说明脚本同目录。没有修改官方 `.m` 算法文件；但官方目录会新增平台编译文件，需要作为环境补充记录。

本地提交并推送编译脚本和本文后，在远程执行：

```bash
cd /tmp/ruan/manifold-clustering
git pull --ff-only
git clone https://github.com/mapefast/mute_neurips.git data/runtime_libs/opentstool_src
git -C data/runtime_libs/opentstool_src checkout 2ef31a09a681ad58a9bbbf17c6ea8785ec9e5fb5

mkdir -p results/lapd_d_check/neighbors_build
git -C data/runtime_libs/opentstool_src rev-parse HEAD > results/lapd_d_check/neighbors_build/source_commit.txt
matlab -batch "addpath('matlab'); build_lapd_neighbors" > results/lapd_d_check/neighbors_build/build.log 2>&1
code=$?
printf 'exit_code\n%s\n' "$code" > results/lapd_d_check/neighbors_build/run_status.tsv
cat results/lapd_d_check/neighbors_build/build.log
```

下载步骤只执行一次。编译脚本会显示三个 `.mexa64` 的解析路径，并把一个小型近邻查询与 MATLAB 的 knnsearch 比较。预期最后打印 `Neighbor search check passed.`；当前本地没有 MATLAB，尚未验证编译或运行是否成功。

回传编译日志并确认检查通过后，再用此前项目目录内的 FFTW 库重试 MSVD。编译步骤本身不运行 MSVD，也不产生新的估计 D 或聚类结果。后续 MSVD 和自动 D 运行都要保留这个 FFTW 加载路径。

### B-01：Linux 近邻模块第一次编译，失败

源码 commit 与上一节一致；编译器为服务器已选定的 g++ 11。退出码为 1，在 nn_prepare.cpp 编译阶段停止，未进入近邻查询核对。

日志确认两项旧源码兼容问题：strlen、strncmp 缺少 cstring 声明；模板类中继承的 randindex 被直接调用，现代编译器要求通过 this-> 指明成员。与 FFTW、输入数据或 D 无关。

依据：[B-01 回传目录](../results/lapd_returns/d_check/neighbors_build/)。

### B-02：补充 C++ 兼容处理后重试，待执行

编译脚本现已增加两处处理：编译时强制包含 cstring；将外部工具箱 nearneigh_search.h 中的 `root.center = randindex(Nused);` 改为 `root.center = this->randindex(Nused);`。第二处会保存到项目 data/ 下的外部源码副本，重复执行不会重复添加 this->。没有改动 LAPD 的官方 `.m` 文件或聚类参数。

重新推送编译脚本后，远程拉取并重试。不重新 clone，也不重新 checkout 外部源码，以免清除兼容修改。用新目录保留 B-01 日志：

```bash
cd /tmp/ruan/manifold-clustering
git pull --ff-only
RUN_DIR=results/lapd_d_check/neighbors_build_retry
mkdir -p "$RUN_DIR"
git rev-parse HEAD > "$RUN_DIR/project_commit.txt"
git -C data/runtime_libs/opentstool_src rev-parse HEAD > "$RUN_DIR/source_commit.txt"
matlab -batch "addpath('matlab'); build_lapd_neighbors" > "$RUN_DIR/build.log" 2>&1
code=$?
printf 'exit_code\n%s\n' "$code" > "$RUN_DIR/run_status.tsv"
git -C data/runtime_libs/opentstool_src diff -- OpenTSTOOL/mex-dev/NNSearcher/nearneigh_search.h > "$RUN_DIR/source_patch.diff"
cat "$RUN_DIR/build.log"
```

本地无 MATLAB，尚未确认这次编译是否成功；以远程日志和小型查询核对结果为准。

自动 D 的完整聚类、ID 14 及其他代表性数据集的 D 检查尚未执行。待实际运行后追加记录，不提前填写结果。

## 4. 参数怎么传：是否修改源码

官方调用形式是 `main(X, opts)`。写入 `opts` 的值仅对这一次调用生效，不会自动写回官方源码。

例如以下是官方接口的说明，需要已经加载 X 并设置好 MATLAB 路径，不是当前项目入口的完整运行命令：

```matlab
opts.intrdim = 2;
opts.filter = 1.50;
opts.bandwidth = 10;
opts.epsilon = 0;
opts.knnnumber = 100;
opts.weight = 'two sided';
opts.K = 3;
opts.parallel = 0;
[d, epsilon, k_hat, labels, runtime, misc] = main(X, opts);
```

本项目入口 `lapd_run` 负责加载数据、组装 opts、调用官方 main 和保存结果。已经新增的第六个参数 d 只控制 OpenML 本次运行的维度：传整数指定 D，传 `[]` 让官方估计，省略则沿用本项目默认 D=1。

入口现已增加可选的第七个参数 `overrides`，用 MATLAB 的 struct 写出这次要改变的参数。不传这个参数时，现有五参数、六参数调用仍使用原有配置。

支持的字段是 `epsilon`、`bandwidth`、`knnnumber`、`weight`、`filter`、`numscales`、`denoisingmethod`、`SKNN`、`componentsize`、`parallel`、`noise_level`。不识别的字段会报错，避免拼写错误导致参数没有生效。D 仍通过第六个参数传入，K 仍由 `known`/`estimate` 决定，不在 overrides 里另设 intrdim 或 K。

例如，只将 d=2 的 filter 改成 1.50：

```matlab
lapd_run('openml', input_file, output_file, lapd_root, 'known', 2, ...
    struct('filter', 1.50));
```

修改多个参数或使用自动 D：

```matlab
% 指定 d=2，修改带宽与预搜索数量。
lapd_run('openml', input_file, output_file, lapd_root, 'known', 2, ...
    struct('bandwidth', 15, 'knnnumber', 100));

% 自动 D，显式设置 filter。
lapd_run('openml', input_file, output_file, lapd_root, 'known', [], ...
    struct('filter', 1.50));
```

以上变量需换成实际路径，或先在 MATLAB 中赋值。overrides 里填写具体参数值；`[]` 在第六个参数处表示自动 D，不作为这些字段的重置方式。

OpenML 如果只修改 bandwidth，入口会使用新的 bandwidth 重新计算项目原有的 knnnumber 公式。如果显式传入 knnnumber，则原样使用该值。因此带宽实验想保持搜索数量不变时，应同时明确写出 knnnumber。

运行日志会显示传给官方程序的 opts；成功结果的 `.mat` 也会保存该 opts。未显式设置的官方内部默认值仍需按第 1 节核对，opts 不一定列出它们。

这次只是入口能力扩展，不是一条新实验结果。**入口的接口修改会保存到项目代码里，但传入某组参数不会永久改变官方默认值。** 不需要为了每组实验修改 `vendor/LAPD`。

### F-01 的远程运行命令

本地提交并推送入口与本文件后，远程拉取，再执行下面的单次运行。目录单独保存 F-01，运行完仍按之前的方式回传结果和日志。

```bash
cd /tmp/ruan/manifold-clustering
git pull --ff-only
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/filter_check/d2_filter150/logs
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/filter_check/d2_filter150/openml_61_d2_filter150_known.mat','$PROJECT_ROOT/vendor/LAPD','known',2,struct('filter',1.50))" > results/lapd_d_check/filter_check/d2_filter150/logs/openml_61_d2_filter150_known.log 2>&1
code=$?
printf 'openml_id\td\tfilter\texit_code\n61\t2\t1.50\t%s\n' "$code" > results/lapd_d_check/filter_check/d2_filter150/run_status.tsv
```

如果以后确实修复官方去噪代码，那属于源码改动，需要另行记录改动内容和使用版本，并与本文件中的原始实现区分。

## 5. 以后如何追加

每组实验复制下面这份短记录，配置相同的数据集可以共用一段配置说明，逐数据集列结果。

```text
记录编号与状态：已执行 / 待执行
目的：这次要检查什么
输入：数据集 ID、表征、样本数
完整配置：d、filter、bandwidth、epsilon、knnnumber、weight、K 协议、
          SKNN、numscales、denoisingmethod、componentsize、parallel
与哪条记录比较：改变了哪些参数，哪些仍用官方默认
版本：项目 commit、官方 commit；源码有修改则说明
结果：退出码、实际 D、实际类数、未分配样本数、ARI、耗时
文件位置：结果与日志目录
结论：观察到什么，哪些原因仍只是判断
```

预测不完整时，全样本 ARI 留空；比较平均分时使用同一批预测完整的数据集。未运行、运行失败、完整预测和部分预测分别记录。成功 `.mat` 的 opts 可能只包含显式传入的字段，官方内部默认值还需结合固定版本源码及保存的 misc、intrinsic_dim 等字段确认。
