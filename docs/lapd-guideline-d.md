# LAPD 的 D 参数检查：分阶段操作指南

这次实验对应 [next-step.md](next-step.md) 中的 LAPD 参数检查：先手动尝试几个 `D`，再测试官方程序自动选择 `D`。本地修改脚本并通过 Git 推送，远程拉取后运行 MATLAB，结果通过 `scp` 回传。**每个阶段完成后先和我确认，再进入下一阶段。**

目前只执行阶段 0。后面的命令是之后逐步执行的说明，不需要一次全部运行。

## 先说明这次要改变什么

`D` 是 LAPD 用来描述数据局部结构的维度。在代码里它叫 `opts.intrdim`，不是 ZEUS 向量的 512 个特征，也不是类别数 `K`。可以先把它理解为：算法用几维的局部结构来连接样本。

第一轮 OpenML 实验使用 `D=1`。这次先比较 `D=1、2、3`，其中重跑 `D=1` 是为了检查新入口与旧实验是否一致。暂时不扩大范围，先看看运行时间和预测情况。

所有运行都提供真实类别数 `K`，沿用原来的 `known` 协议。提供 `K` 不保证最终输出恰好 `K` 个簇。原入口的 `estimate` 模式估计的是 **K**，这次自动选择 **D** 仍使用 `known`。

其他显式参数保持原样：

| 项目 | 设置 |
| --- | --- |
| 输入 | 已保存的 `embeddings_scaled`，不重新生成 ZEUS 向量 |
| 类别数 | `mode='known'` |
| 半径 | `epsilon=0` |
| 带宽 | `bandwidth=10` |
| 近邻搜索数量 | 保持原入口的计算公式 |
| 权重 | `weight='two sided'` |
| 并行 | `parallel=0` |

这里固定的是我们传给程序的其他参数。官方内部有些默认设置会随 `D` 改变，因此不是所有内部计算都完全相同。`D` 增大也会增加局部组合数量，运行时间和内存需求可能上升，先通过小规模试跑了解情况。

自动 `D` 使用官方的 `MSVD` 方法，它从不同邻域大小下的数据变化估计维度。它与分析 notebook 中的 TWO-NN 估计不是同一种方法，两个数可以对照，但不必相同。[官方入口源码](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/main.m)和[MSVD 源码](https://github.com/HYfromLA/LAPD/blob/d678a0baa2a4d9b0134ff1719c80c42e78eda108/Auxiliary/MSVD/MSVD.m)是本指南调用方式的依据。

## 阶段 0：确认远程路径、源码和现有输入

**本地 PowerShell：** 在项目根目录设置传输变量。把 `USER@HOST` 改为实际 SSH 地址；远程路径沿用此前实验，如果已移动就同步修改。

```powershell
Set-Location E:\dev\manifold-clustering
$LapdRemote = "USER@HOST"
$LapdRemoteRoot = "/tmp/ruan/manifold-clustering"
```

**远程 bash：** 登录服务器后执行。之后每个远程阶段都从这个项目目录开始。

```bash
cd /tmp/ruan/manifold-clustering
git status --short
git -C vendor/LAPD rev-parse HEAD
git -C vendor/LAPD status --short
ls data/lapd_mat/openml_{61,14,51,481,694,820,1495,40705}_scaled.mat
matlab -batch "cd('vendor/LAPD'); addpath(genpath(pwd)); disp(version); disp(which('main')); disp(which('MSVD'))"
```

旧实验的 LAPD commit 是 `d678a0baa2a4d9b0134ff1719c80c42e78eda108`。这次复用同一份官方源码，不更新它。`main` 和 `MSVD` 应能显示具体文件路径。`git status --short` 没有输出表示没有未提交修改。

`data/` 和 `vendor/LAPD/` 被 Git 忽略，所以拉取项目不会下载输入或官方代码。远程应已有第一轮使用的文件。如果上述输入缺失，远程先创建目录：

```bash
mkdir -p data/lapd_mat
```

然后在本地导出并上传这 8 份输入；文件已经齐全时不用执行：

```powershell
.\.venv\Scripts\python.exe .\scripts\export_lapd_mat.py --ids 61 14 51 481 694 820 1495 40705
scp .\data\lapd_mat\openml_61_scaled.mat .\data\lapd_mat\openml_14_scaled.mat .\data\lapd_mat\openml_51_scaled.mat .\data\lapd_mat\openml_481_scaled.mat .\data\lapd_mat\openml_694_scaled.mat .\data\lapd_mat\openml_820_scaled.mat .\data\lapd_mat\openml_1495_scaled.mat .\data\lapd_mat\openml_40705_scaled.mat "${LapdRemote}:${LapdRemoteRoot}/data/lapd_mat/"
```

**本阶段和我确认：** 发来远程检查的终端输出。先确认源码版本、输入和 MATLAB 路径；如果有未提交修改或文件缺失，先处理具体问题。

## 阶段 1：本地让入口支持指定 D，再推送和拉取

只对 `matlab/lapd_run.m` 做下面三处小修改，不复制多份入口，也不修改官方 `vendor/LAPD`。可以由我在你确认阶段 0 后完成修改，你检查差异再提交。

**第一处：** 函数增加第六个参数 `d`，旧的五参数调用默认仍使用 `D=1`。

```matlab
function lapd_run(kind, input_file, output_file, lapd_root, mode, d)
% d: a positive integer for manual D; [] for automatic D on OpenML.
if nargin < 6
    d = 1;
end
```

**第二处：** 只替换 `case 'openml'` 分支中的 `opts.intrdim = 1;`：

```matlab
if ~isempty(d)
    opts.intrdim = d;
end
```

这样传 `2` 就设置 `D=2`；传 `[]` 就不设置 `opts.intrdim`，由官方 `main` 自动估计。不要把 `opts.intrdim` 设成 `0` 或字符串。COIL20、USPS 的分支不用改。

**第三处：** 在调用 `main` 的下一行增加实际维度的日志：

```matlab
fprintf('Actual D=%d\n', intrinsic_dim);
```

原脚本已经保存 `opts`、`intrinsic_dim`、预测、标签、样本索引和耗时，不需要再增加一套结果格式。手动运行时 `opts.intrdim` 记录指定值；自动运行时这个字段不存在，以输出中的 `intrinsic_dim` 为准。

**本地 PowerShell：** 检查并提交这次的两个文件，然后推送当前分支。

```powershell
git diff -- matlab/lapd_run.m
git status --short
git add matlab/lapd_run.m docs/lapd-guideline-d.md
git commit -m "Support LAPD dimension checks and document workflow"
git push
git rev-parse HEAD
git branch --show-current
```

只暂存上述文件。当前工作区还有 `docs/lapd-guideline-d2.md` 的删除，不要顺手把它包含进这次提交。

**远程 bash：** 核对与本地是同一个分支，拉取项目代码。

```bash
cd /tmp/ruan/manifold-clustering
git branch --show-current
git pull --ff-only
git rev-parse HEAD
head -n 8 matlab/lapd_run.m
```

若两边分支不同，先告诉我分支名；若拉取失败，发来输出。这里不需要更新 `vendor/LAPD`。

**本阶段和我确认：** 发来本地脚本差异，以及两端的分支名和 commit。两端 commit 应一致，远程函数定义应有第六个参数 `d`。

## 阶段 2：只在 Iris 上手动试 D=1、2、3

先用 ID 61（Iris，150 个样本）检查新入口。结果全部写入新的 `results/lapd_d_check/`，不会写入第一轮的结果目录。

**远程 bash：** 创建目录并记录版本。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/manual_smoke/logs
git rev-parse HEAD > results/lapd_d_check/project_commit.txt
git -C vendor/LAPD rev-parse HEAD > results/lapd_d_check/lapd_commit.txt
git -C vendor/LAPD status --short > results/lapd_d_check/lapd_git_status.txt
matlab -batch "disp(version); ver" > results/lapd_d_check/environment.log 2>&1
```

运行三次，每次单独启动 MATLAB并保存日志。如果某次失败，停止循环，先回传已有结果。

```bash
printf 'openml_id\td_setting\texit_code\n' > results/lapd_d_check/manual_smoke/run_status.tsv
for d in 1 2 3; do
  name="openml_61_d${d}_known"
  matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/manual_smoke/${name}.mat','$PROJECT_ROOT/vendor/LAPD','known',$d)" > "results/lapd_d_check/manual_smoke/logs/${name}.log" 2>&1
  code=$?
  printf '61\t%s\t%s\n' "$d" "$code" >> results/lapd_d_check/manual_smoke/run_status.tsv
  if [ "$code" -ne 0 ]; then break; fi
done
```

**返回本地 PowerShell：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\d_check | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd_d_check" .\results\lapd_returns\d_check\
```

以下阶段都复用这条回传命令，新增结果会进入同一份本地目录。成功结果是 `.mat`，失败原因在 `.log` 中，失败日志也要带回。

**本阶段和我确认：** 告诉我结果已回到 `results/lapd_returns/d_check/lapd_d_check/`。我会读取结果，核对实际 `D`、预测是否完整、运行时间和 ARI，并将新的 `D=1` 与第一轮 Iris 结果比较。确认入口正常后再扩大数据规模。

同一组命令再次执行会覆盖同名输出。需要重试时，换一个目录名，例如 `manual_smoke_retry`，同时修改命令中的输出和日志路径，保留第一次结果。

## 阶段 3：在较大的数据集和低分数据集上手动比较

先对 ID 14（2000 个样本）运行同样三种 `D`，了解较大输入的耗时。**远程 bash：**

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/manual_14/logs
printf 'openml_id\td_setting\texit_code\n' > results/lapd_d_check/manual_14/run_status.tsv
for d in 1 2 3; do
  name="openml_14_d${d}_known"
  matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_14_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/manual_14/${name}.mat','$PROJECT_ROOT/vendor/LAPD','known',$d)" > "results/lapd_d_check/manual_14/logs/${name}.log" 2>&1
  code=$?
  printf '14\t%s\t%s\n' "$d" "$code" >> results/lapd_d_check/manual_14/run_status.tsv
  if [ "$code" -ne 0 ]; then break; fi
done
```

运行后先用阶段 2 的 `scp` 命令回传，和我确认耗时、预测覆盖情况及是否适合继续。

然后对 6 个低分数据集运行：`51、481、694、820、1495、40705`。它们都在已有结构分析中出现，也覆盖了邻接关系、重复向量和不同方法表现的差异。这是第一批候选，不表示已经证明低分原因；在执行前可以结合前两个试跑结果调整名单。

**远程 bash：** 确认名单后执行。以下共 18 次运行，单次失败会保留记录并继续其余组合。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/manual_selected/logs
printf 'openml_id\td_setting\texit_code\n' > results/lapd_d_check/manual_selected/run_status.tsv
for id in 51 481 694 820 1495 40705; do
  for d in 1 2 3; do
    name="openml_${id}_d${d}_known"
    matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_${id}_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/manual_selected/${name}.mat','$PROJECT_ROOT/vendor/LAPD','known',$d)" > "results/lapd_d_check/manual_selected/logs/${name}.log" 2>&1
    code=$?
    printf '%s\t%s\t%s\n' "$id" "$d" "$code" >> results/lapd_d_check/manual_selected/run_status.tsv
  done
done
```

**本阶段和我确认：** 回传整个目录。我会整理每个数据集在三个 `D` 下的 ARI、未分配样本数、实际簇数和耗时，先回答“改 D 是否有帮助”，再决定是否补充其他 `D`。这里允许观察 ARI 随参数的变化，但不能将每个数据集最高的 ARI 拼成一项统一配置的结果。

## 阶段 4：先看看官方方法会估计出什么 D

手动比较完成后，先单独运行维度估计，不立即运行自动 `D` 的完整聚类。这样能提前知道它选了多大的维度，也能发现自动估计所需函数是否能在服务器上正常运行。

**远程 bash：** 对本次 8 个数据集调用官方 `MSVD`。使用与 `main` 相同的默认随机初始化。每份结果保存维度、噪声估计和估计耗时。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/d_estimates/logs
printf 'openml_id\texit_code\n' > results/lapd_d_check/d_estimates/run_status.tsv
for id in 61 14 51 481 694 820 1495 40705; do
  matlab -batch "cd('$PROJECT_ROOT/vendor/LAPD'); addpath(genpath(pwd)); rng('default'); S=load('$PROJECT_ROOT/data/lapd_mat/openml_${id}_scaled.mat'); openml_id=$id; tic; [estimated_d,estimated_noise]=MSVD(double(S.X),0); estimate_seconds=toc; save('$PROJECT_ROOT/results/lapd_d_check/d_estimates/openml_${id}_msvd.mat','openml_id','estimated_d','estimated_noise','estimate_seconds','-v7'); fprintf('ID=%d, estimated D=%d, seconds=%.3f\n',openml_id,estimated_d,estimate_seconds)" > "results/lapd_d_check/d_estimates/logs/openml_${id}_msvd.log" 2>&1
  code=$?
  printf '%s\t%s\n' "$id" "$code" >> results/lapd_d_check/d_estimates/run_status.tsv
done
```

这里的噪声估计是官方方法的附带输出。这次保持 `epsilon=0`，不把它用于改半径。

**本阶段和我确认：** 回传目录，我会整理估计出的 `D`，与 TWO-NN 结果及手动试跑范围对照。若估计值较大，先讨论计算量；若不在当前带宽 10 可支持的范围内，先检查原因。不要静默把自动值改成 3 或 10，也不要为了跑通而同时更改其他参数。

## 阶段 5：让 LAPD 自动选择 D 并完成聚类

先在 Iris 上跑一遍。最后一个参数传 `[]`，仍然传入 `known`。程序会自行调用 `MSVD`，然后使用估计出的维度继续聚类；不是把阶段 4 的数字手动填进去。

**远程 bash：**

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/auto_smoke/logs
matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_61_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/auto_smoke/openml_61_auto_known.mat','$PROJECT_ROOT/vendor/LAPD','known',[])" > results/lapd_d_check/auto_smoke/logs/openml_61_auto_known.log 2>&1
code=$?
printf 'openml_id\td_setting\texit_code\n61\tauto\t%s\n' "$code" > results/lapd_d_check/auto_smoke/run_status.tsv
```

回传并和我确认自动入口正常。之后再运行其余 7 个数据集；**下面的名单以阶段 4 确认能继续的名单为准**，如果有某个数据集暂不运行，记录原因，不从报告中隐藏它。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
mkdir -p results/lapd_d_check/auto_selected/logs
printf 'openml_id\td_setting\texit_code\n' > results/lapd_d_check/auto_selected/run_status.tsv
for id in 14 51 481 694 820 1495 40705; do
  name="openml_${id}_auto_known"
  matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run('openml','$PROJECT_ROOT/data/lapd_mat/openml_${id}_scaled.mat','$PROJECT_ROOT/results/lapd_d_check/auto_selected/${name}.mat','$PROJECT_ROOT/vendor/LAPD','known',[])" > "results/lapd_d_check/auto_selected/logs/${name}.log" 2>&1
  code=$?
  printf '%s\tauto\t%s\n' "$id" "$code" >> results/lapd_d_check/auto_selected/run_status.tsv
done
```

**本阶段和我确认：** 回传整个目录。我会核对实际 `intrinsic_dim` 与阶段 4 的估计是否一致，再比较自动 `D` 与固定 `D=1、2、3` 的结果。自动运行的耗时包含维度估计；固定 `D` 的运行不含这一步，报告时说明这个差别。

如果过程中需要修改入口，仍按阶段 1 的方式在本地修改、提交、推送，远程拉取；不要只在服务器上临时改脚本。新一轮结果换目录，并保存对应的项目 commit。

## 阶段 6：本地整理结果，决定是否扩大实验

这一阶段由我读取回传文件并整理，你确认分析和下一步安排。现在不需要再复制一大段审计代码。**不要直接运行原来的 `scripts/audit_lapd_results.py`**：它固定读取第一轮 stage4 的 68 次运行，不能用来汇总这次的 D 检查。

整理表格至少包含：

- 数据集 ID、指定 D 或自动模式、实际使用的 D。
- 进程是否成功、未分配样本数、预测覆盖率。
- 请求的 K、实际输出簇数、完整预测时的全样本 ARI。
- 耗时，以及同一数据集的 K-means ARI。

计算 ARI 前会核对返回标签和样本索引与本地缓存一致。进程成功不代表预测完整；预测含 `NaN` 时保留该运行，但全样本 ARI 留空，不删除样本后评分。比较平均 ARI 时，只使用被比较配置都预测完整的同一批数据集，并同时报告各配置的完整预测数量。

我们要逐项回答：

1. 第一轮低分是否与固定 `D=1` 有关？换成 2 或 3 后，是分数改善、预测更完整，还是仅耗时增加？
2. 自动方法选出的 D 是否合理，能否带来稳定改善？
3. TWO-NN 的维度估计与较有效的 D 是否有一致趋势？当前样本有限，先作为线索。

再根据结果决定是否增加其他 D、扩展到全部 34 个数据集，或转向检查其他参数。固定 D 的最好分数只用于描述参数敏感性，不能称为无需标签即可选择的配置；自动方法是否有效，应单独评价。

## 每次交接时告诉我什么

可以直接说：“阶段 2 已完成，结果在 `results/lapd_returns/d_check/lapd_d_check/`，请核对后再继续。”如果命令失败，先发报错和对应 `.log`，已有结果也照常回传。

源码和指南通过 Git 同步；输入、`.mat` 结果和日志通过 `scp` 传输。远程结果目录不要加入 Git，本地回传目录已被项目忽略。服务器有作业调度要求时，将上述 MATLAB 命令放进现有作业脚本运行，参数与输出路径保持一致。
