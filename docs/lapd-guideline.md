# LAPD 操作手册：本地 ZEUS 向量与远程 MATLAB

本手册把 [LAPD 阶段计划](plan-lapd.md)变成可逐步执行的命令。**本地是 Windows PowerShell，远程假定为 Linux bash**。LAPD 算法在远程 MATLAB 中运行；本地只负责导出 `.mat`、传输文件、读取返回结果并与 ZEUS + K-means 比较。官方核心入口为 `main(X,LAPDopts)`，其中 `X` 的形状为样本数 × 特征数。[LAPD 官方仓库](https://github.com/HYfromLA/LAPD)、[MATLAB `-batch` 文档](https://www.mathworks.com/help/matlab/ref/matlablinux.html)

## 先约定路径与交接方式

本地项目根目录为 `E:\dev\manifold-clustering`。阶段 0 日志确认远程项目当前位于 `/tmp/ruan/manifold-clustering`；若服务器之后移动或清理了该目录，先更新以下路径。请把 `USER@HOST` 替换为实际 SSH 地址。以下 PowerShell 命令均从本地项目根目录执行；bash 命令均在远程终端执行。阶段 1 仍显式上传 `matlab/lapd_run.m`，以确保远程运行的是本手册对应的版本。

本地 PowerShell 先设置本次会话变量：

```powershell
Set-Location E:\dev\manifold-clustering
$LapdRemote = "USER@HOST"
$LapdRemoteRoot = "/tmp/ruan/manifold-clustering"
```

每一阶段完成后，把该阶段列出的文件复制回本地项目的 `results/lapd_returns/`，告诉我所在目录。我会直接读取这些文件并决定下一阶段是否需要调整。**不要通过 Git 传输 `data/` 中的向量或远程运行生成的大文件**；项目已忽略 `data/` 和 `vendor/LAPD/`。远程脚本的每次输出为一个 `.mat`，对应的 `.log` 保留 MATLAB 标准输出和错误信息。失败时也请返回 `.log`。

## 阶段 0：远程环境、官方数据与源码检查

**本地：** 暂不计算。确认本项目中的 [MATLAB 入口](../matlab/lapd_run.m) 可见。

**远程：** 在 bash 中执行；`git clone` 只在 `vendor/LAPD` 不存在时运行。

```bash
cd /tmp/ruan/manifold-clustering
mkdir -p vendor matlab data/lapd_mat results/lapd/logs
if [ ! -d vendor/LAPD/.git ]; then git clone https://github.com/HYfromLA/LAPD.git vendor/LAPD; fi
git -C vendor/LAPD rev-parse HEAD > results/lapd/logs/lapd_commit.txt
matlab -batch "disp(version); ver; disp(which('knnsearch')); disp(which('pdist')); disp(which('parpool'))" > results/lapd/logs/environment.log 2>&1
matlab -batch "cd('vendor/LAPD'); addpath(genpath(pwd)); disp(which('main')); disp(which('accuracy'))" > results/lapd/logs/functions.log 2>&1
find vendor/LAPD -iname 'coil20.mat' -o -iname 'USPS.mat' > results/lapd/logs/benchmark_files.txt
```

核对 `environment.log` 中 MATLAB 版本与 `knnsearch`、`pdist` 的解析路径，`functions.log` 中应能找到官方 `main.m` 和 `accuracy.m`。`benchmark_files.txt` 应列出 COIL20 与 USPS 文件。若为空，先返回这一阶段的日志；不要凭空猜数据路径。若 `matlab` 不在 PATH，用 MATLAB 可执行文件的绝对路径替代。`parpool` 仅用于检查，第一轮不启用并行。

**返回本地：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\stage0 | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd/logs" .\results\lapd_returns\stage0\
```

返回目录是 `results/lapd_returns/stage0/logs/`，至少包含 `lapd_commit.txt`、`environment.log`、`functions.log` 和 `benchmark_files.txt`。

## 阶段 1：COIL20 与 USPS 官方示例复现

**本地：** 上传项目自有的 MATLAB 入口。它只运行一个数据集，避免官方 `real_data_demo.m` 一次串行运行 COIL20、MNIST、USPS。入口对 COIL20 和 USPS 使用官方 demo 的全类别参数，结果中保存预测标签、真实标签、参数、运行时间、诊断量、官方 `accuracy`、MATLAB 版本和 LAPD commit。[官方真实数据 demo](https://github.com/HYfromLA/LAPD/blob/main/real_data_demo.m)

```powershell
scp .\matlab\lapd_run.m "${LapdRemote}:${LapdRemoteRoot}/matlab/lapd_run.m"
```

**远程：** 先用阶段 0 的 `benchmark_files.txt` 确认数据文件确实存在，再执行：

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
COIL_FILE=$(find vendor/LAPD -iname 'coil20.mat' -print -quit)
USPS_FILE=$(find vendor/LAPD -iname 'USPS.mat' -print -quit)
test -f "$COIL_FILE"
test -f "$USPS_FILE"
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('coil20','$PROJECT_ROOT/$COIL_FILE','$PROJECT_ROOT/results/lapd/bench_coil20_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > results/lapd/logs/bench_coil20_known.log 2>&1
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('usps','$PROJECT_ROOT/$USPS_FILE','$PROJECT_ROOT/results/lapd/bench_usps_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > results/lapd/logs/bench_usps_known.log 2>&1
```

运行后检查两份 `.mat` 是否生成。如果某个命令失败，请保留对应 `.log` 并停止该数据集的后续操作。官方 `main.m` 在参数不合适时可能请求 `input`；非交互 `-batch` 下不能依靠人手回答。需要根据日志核对 `epsilon`、带宽和近邻数后修正，不能用真实标签挑选最优参数。[官方 `main.m`](https://github.com/HYfromLA/LAPD/blob/main/Auxiliary/main.m)、[MathWorks `-batch` 说明](https://www.mathworks.com/help/matlab/ref/matlablinux.html)

**返回本地：** 把整个 `results/lapd` 复制到单独的阶段目录，避免与后续结果混淆。

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\stage1 | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd" .\results\lapd_returns\stage1\
```

我需要 `bench_coil20_known.mat`、`bench_usps_known.mat`、对应 `.log` 和阶段 0 的环境信息。论文 Table 3 使用准确率，比较时应核对相同类别子集；不要直接拿它与 ZEUS 表格数据的 ARI 比较。[LAPD 论文 Table 3](https://arxiv.org/html/2507.10710v1)

## 阶段 2：本地 ZEUS 向量导出与远程数据核对

**本地：** 先导出 Iris（OpenML ID 61）与 ID 14。脚本读取原有 `.npz`，检查 512 维、有限值和从 0 开始的样本索引，生成 MATLAB 可读的 `X`、`labelsGT`、`sample_indices`、`openml_id`、`embedding_variant`。默认使用与现有 ZEUS + K-means 基线一致的 `embeddings_scaled`。

```powershell
.\.venv\Scripts\python.exe .\scripts\export_lapd_mat.py --ids 61 14
scp .\data\lapd_mat\openml_61_scaled.mat "${LapdRemote}:${LapdRemoteRoot}/data/lapd_mat/"
scp .\data\lapd_mat\openml_14_scaled.mat "${LapdRemote}:${LapdRemoteRoot}/data/lapd_mat/"
```

如果本地使用 `uv`，第一条也可写为 `uv run python scripts/export_lapd_mat.py --ids 61 14`。输出位于 `data/lapd_mat/`，该目录已被 `.gitignore` 中的 `data/` 覆盖。

**远程：** 只核对数据结构，不运行算法。日志应显示 `X` 分别为 `150×512` 和 `2000×512`，标签和索引长度与样本数相同。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
matlab -batch "A=load('$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat'); B=load('$PROJECT_ROOT/data/lapd_mat/openml_14_scaled.mat'); disp(size(A.X)); disp(size(B.X)); assert(size(A.X,1)==numel(A.labelsGT)); assert(size(B.X,1)==numel(B.labelsGT)); assert(all(A.sample_indices(:)==(0:size(A.X,1)-1)')); assert(all(B.sample_indices(:)==(0:size(B.X,1)-1)'))" > results/lapd/logs/mat_input_check.log 2>&1
```

**返回本地：** 导出的 `.mat` 已在本地，无需再从远程下载；只需复制数据检查日志。

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\stage2 | Out-Null
scp "${LapdRemote}:${LapdRemoteRoot}/results/lapd/logs/mat_input_check.log" .\results\lapd_returns\stage2\
```

若日志中的形状不是预期值，暂不运行阶段 3。

## 阶段 3：ZEUS 向量小规模试跑

**远程：** 使用同一组预先固定的 OpenML 参数先跑 ID 61，再跑 ID 14。`known` 仅使用真实标签的**类别数**传入 `K`；`estimate` 不传 `K`，记录 LAPD 估计的 `k_hat`。两种协议的结果必须分开。**传入 `K` 不保证实际输出 `k_hat=K`**：阶段 3 的 ID 14 传入 `K=10`，实际只输出 7 个簇。因此 `known` 表示“提供类别数”，不能称为“固定输出类别数”；汇总时同时报告 `opts.K` 和实际 `k_hat`。入口当前初始参数为 `intrdim=1`、`epsilon=0`、`bandwidth=10`、`weight='two sided'`、`parallel=0`，并显式给足近邻搜索数量；这是一组**试跑配置**，不等于已验证的最佳配置。每次运行的实际 `opts` 都保存在 `.mat` 中。官方 `main.m` 会自行调用 `rng('default')`，因此外部设置不同随机种子可能不会改变结果。[官方 `main.m`](https://github.com/HYfromLA/LAPD/blob/main/Auxiliary/main.m)

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat','$PROJECT_ROOT/results/lapd/openml_61_scaled_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > results/lapd/logs/openml_61_scaled_known.log 2>&1
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat','$PROJECT_ROOT/results/lapd/openml_61_scaled_estimate.mat','$PROJECT_ROOT/vendor/LAPD','estimate')" > results/lapd/logs/openml_61_scaled_estimate.log 2>&1
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_14_scaled.mat','$PROJECT_ROOT/results/lapd/openml_14_scaled_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > results/lapd/logs/openml_14_scaled_known.log 2>&1
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_14_scaled.mat','$PROJECT_ROOT/results/lapd/openml_14_scaled_estimate.mat','$PROJECT_ROOT/vendor/LAPD','estimate')" > results/lapd/logs/openml_14_scaled_estimate.log 2>&1
```

若第一条失败，先返回日志，不必继续后三条。每份成功结果应含 `predicted_labels`、`labelsGT`、`sample_indices`、`opts`、`intrinsic_dim`、`epsilon`、`k_hat`、`runtime`、`misc`、`openml_id`、`embedding_variant`、`lapd_commit`。脚本对预测长度作检查；若预测中存在无效或未分配标签，返回文件后再统一判断，不要手工删行。

**返回本地：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\stage3 | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd" .\results\lapd_returns\stage3\
```

我会读取 `.mat` 中的逐样本预测，检查顺序并计算 ARI，再决定是否能按同一配置扩展。若某个模式失败，也请返回该模式 `.log`。

## 阶段 4：全部 34 个 OpenML 数据集

只有阶段 3 的输入、预测与日志检查通过后再执行。如果需调整参数，先修改并重新上传 `matlab/lapd_run.m`，同时保留旧结果以便区分配置。

**本地：** 导出 34 份缩放向量，并把整个导出目录上传。若该目录已有先前生成的 `raw` 文件，先确认上传范围与远程剩余空间；不要把 `raw` 与 `scaled` 的实验结果混在一起。

```powershell
.\.venv\Scripts\python.exe .\scripts\export_lapd_mat.py --all
scp -r .\data\lapd_mat "${LapdRemote}:${LapdRemoteRoot}/data/"
```

**远程：** 一次跑一个 `.mat`，每个模式都保留独立日志与退出码。以下循环包括阶段 3 的两个 ID；若想避免重跑，可在循环中按文件名跳过，但应在运行记录里注明。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
printf 'dataset\tmode\texit_code\n' > results/lapd/run_status.tsv
for input_file in data/lapd_mat/openml_*_scaled.mat; do
  stem=$(basename "$input_file" .mat)
  for mode in known estimate; do
    matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/$input_file','$PROJECT_ROOT/results/lapd/${stem}_${mode}.mat','$PROJECT_ROOT/vendor/LAPD','$mode')" > "results/lapd/logs/${stem}_${mode}.log" 2>&1
    printf '%s\t%s\t%s\n' "$stem" "$mode" "$?" >> results/lapd/run_status.tsv
  done
done
```

预计应有 34 个数据集 × 2 种簇数协议，即 68 条运行状态记录；失败记录也保留在 `run_status.tsv` 和 `.log` 中。该循环会为每次运行启动 MATLAB，时间可能较长；远程有作业调度器时，请按服务器规则提交同样的单数据集命令。不要在一次 MATLAB 调用里无记录地跳过失败 ID。

**返回本地：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\stage4 | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd" .\results\lapd_returns\stage4\
```

我需要 `run_status.tsv`、全部成功的 `openml_*_scaled_*.mat`、对应 `.log`、`lapd_commit.txt` 和 `environment.log`。返回后在本地运行：

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_lapd_results.py
```

该脚本输出 `results/lapd_stage4_audit.csv`，逐项核验 `.npz` 标签和样本顺序，记录实际输出簇数、未分配样本数、覆盖率、耗时，以及预测完整时的全样本 ARI。**退出码 0 不保证每个样本都有预测。** 首次 34 数据集实验的 68 次 MATLAB 进程全部退出码为 0，但 9 份结果包含 `NaN` 预测；这些运行的全样本 ARI 留空，不能悄悄删除未分配样本后计算。分析时将 `known`/`estimate` 分开，与已有 ZEUS + K-means 比较，并报告每个模式的完整运行数。若某个 ID 失败，保留它及错误原因，不只统计成功数据集。

## 常见停止点

- `benchmark_files.txt` 为空：先把阶段 0 的日志返回，确认官方数据是否随仓库提供或需要单独取得。
- `which('main')` 或 `which('knnsearch')` 为空：先处理路径或 toolbox；不要继续跑 LAPD。
- `matlab -batch` 无 `.mat` 输出：返回该次 `.log`，核对是否触发交互式 `input`、数组越界或内存不足。
- `.mat` 的样本数、标签长度、索引对不上：停止聚类，回到阶段 2 核对导出与传输。
- 需要改变 `intrdim`、半径、带宽或输入表征：生成新的配置标识并保留旧结果，避免覆盖后无法追溯。参数选择不能使用真实标签上的 ARI。
