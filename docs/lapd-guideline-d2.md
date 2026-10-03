# LAPD d=2 实验操作手册

本手册参考 [原 LAPD 操作手册](lapd-guideline.md)，用于检验：在同一批 ZEUS 缩放表征上，将 LAPD 的内在维度设置从 `d=1` 改为 `d=2`，聚类效果、预测覆盖率和耗时如何变化。

本地使用 Windows PowerShell，远程使用 Linux bash 和 MATLAB。主实验只运行 **known K**：提供真实类别数，但不使用类别标签选择参数。提供 K 不保证 LAPD 最终恰好输出 K 个簇。此次是维度敏感性实验，不是内在维度自动估计，也不表示已经确认数据的真实维度为 2。

## 实验配置与目录

显式输入参数中，只将 OpenML 分支的 `opts.intrdim` 从 1 改为 2；其他设置沿用现有入口：

| 项目 | 本次设置 |
| --- | --- |
| 输入 | 同一批 `embeddings_scaled`，不新增降维或归一化 |
| 内在维度 | `opts.intrdim = 2` |
| 类别数协议 | `known`，`opts.K = numel(unique(labelsGT))` |
| 半径参数 | `epsilon = 0` |
| 带宽 | `bandwidth = 10` |
| 近邻数 | `min(n, max(100, ceil(0.1*n) + bandwidth))` |
| 权重 | `two sided` |
| 并行 | `parallel = 0` |
| 随机性 | 保持原入口和官方实现的行为 |

官方内部依赖 d 的默认参数或计算过程可能随之改变；这里固定的是其他显式输入参数。保存完整 `opts` 和 `misc`，以便检查实际行为。

使用独立 MATLAB 入口 `matlab/lapd_run_d2.m`，保留原来的 `matlab/lapd_run.m`。本手册中的命令会从原入口生成新文件，无需手动修改原文件。

目录约定：

- 远程试跑：`results/lapd_d2_smoke/`
- 远程全量：`results/lapd_d2/`
- 本地回传：`results/lapd_returns/d2_smoke/lapd_d2_smoke/` 和 `results/lapd_returns/d2/lapd_d2/`
- 本地审计：`results/lapd_d2_audit.csv`
- 与 d=1 比较：`results/lapd_d1_d2_known_comparison.csv`

不要写入原来的 `results/lapd/` 或 `results/lapd_returns/stage4/`。本次不需要重跑 COIL20 和 USPS，也不需要重新提取 ZEUS 表征。

## 阶段 0：准备独立入口与确认环境

**本地 PowerShell：**

```powershell
Set-Location E:\dev\manifold-clustering
$LapdRemote = "USER@HOST"
$LapdRemoteRoot = "/tmp/ruan/manifold-clustering"
```

替换 SSH 地址；远程目录沿用原手册，若已经移动，请同步替换。生成 d=2 入口：

```powershell
@'
from pathlib import Path

source = Path("matlab/lapd_run.m").read_text(encoding="utf-8")
header = "function lapd_run(kind, input_file, output_file, lapd_root, mode)"
assert source.count(header) == 1
start = source.index("    case 'openml'")
end = source.index("    otherwise", start)
block = source[start:end]
assert block.count("opts.intrdim = 1;") == 1
updated = source[:start] + block.replace("opts.intrdim = 1;", "opts.intrdim = 2;") + source[end:]
updated = updated.replace(header, header.replace("lapd_run(", "lapd_run_d2("), 1)
target = Path("matlab/lapd_run_d2.m")
if target.exists() and target.read_text(encoding="utf-8") != updated:
    raise RuntimeError("Existing lapd_run_d2.m differs; inspect it before replacing")
target.write_text(updated, encoding="utf-8")
print("Generated", target)
'@ | .\.venv\Scripts\python.exe -
```

此命令只改变函数名和 OpenML 分支的维度设置；COIL20、USPS 分支保持原样，但本次不调用它们。

**远程 bash：** 创建独立目录，核对源码与 MATLAB。复用原实验的官方源码，不更新或重新克隆。

```bash
cd /tmp/ruan/manifold-clustering
mkdir -p matlab data/lapd_mat results/lapd_d2_smoke/logs results/lapd_d2/logs
git -C vendor/LAPD rev-parse HEAD > results/lapd_d2/logs/lapd_commit.txt
git -C vendor/LAPD status --short > results/lapd_d2/logs/lapd_git_status.txt
matlab -batch "disp(version); ver; disp(which('knnsearch')); disp(which('pdist')); cd('vendor/LAPD'); addpath(genpath(pwd)); disp(which('main'))" > results/lapd_d2/logs/environment.log 2>&1
```

现有 d=1 结果记录的 LAPD commit 为 `d678a0baa2a4d9b0134ff1719c80c42e78eda108`。确认本次相同，并检查工作区是否存在影响算法的修改。若源码或环境变化，先查清差异，必要时在相同环境重新运行 d=1 对照；不要把版本变化造成的差异归因于 d。

**本地 PowerShell：** 上传新入口。

```powershell
scp .\matlab\lapd_run_d2.m "${LapdRemote}:${LapdRemoteRoot}/matlab/lapd_run_d2.m"
```

## 阶段 1：ID 61 和 ID 14 小规模试跑

复用原实验导出的 `data/lapd_mat/openml_61_scaled.mat` 和 `openml_14_scaled.mat`。如果远程缺少它们，执行：

```powershell
.\.venv\Scripts\python.exe .\scripts\export_lapd_mat.py --ids 61 14
scp .\data\lapd_mat\openml_61_scaled.mat .\data\lapd_mat\openml_14_scaled.mat "${LapdRemote}:${LapdRemoteRoot}/data/lapd_mat/"
```

**远程 bash：** 顺序试跑两个数据集，单独记录退出码。已有输出时停止，避免旧文件被误认为本次结果。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
(
  set -e
  for id in 61 14; do
    test -f "data/lapd_mat/openml_${id}_scaled.mat"
    if [ -e "results/lapd_d2_smoke/openml_${id}_scaled_known.mat" ] || [ -e "results/lapd_d2_smoke/logs/openml_${id}_scaled_known.log" ]; then
      echo "Existing smoke output for ID $id; use a new directory for another run."
      exit 1
    fi
  done
  printf 'dataset\tmode\texit_code\n' > results/lapd_d2_smoke/run_status.tsv
  for id in 61 14; do
    stem="openml_${id}_scaled"
    if matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run_d2('openml','$PROJECT_ROOT/data/lapd_mat/${stem}.mat','$PROJECT_ROOT/results/lapd_d2_smoke/${stem}_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > "results/lapd_d2_smoke/logs/${stem}_known.log" 2>&1; then
      code=0
    else
      code=$?
    fi
    printf '%s\tknown\t%s\n' "$stem" "$code" >> results/lapd_d2_smoke/run_status.tsv
    if [ "$code" -ne 0 ]; then exit "$code"; fi
  done
)
```

检查成功结果的参数和预测：

```bash
matlab -batch "for id=[61 14]; S=load('$PROJECT_ROOT/results/lapd_d2_smoke/openml_'+string(id)+'_scaled_known.mat'); assert(S.opts.intrdim==2); assert(S.intrinsic_dim==2); assert(numel(S.predicted_labels)==numel(S.labelsGT)); assert(all(S.sample_indices(:)==(0:numel(S.labelsGT)-1)')); fprintf('ID=%d, d=%d, requested_K=%d, k_hat=%d, unassigned=%d, runtime=%.3f\n',id,S.opts.intrdim,S.opts.K,S.k_hat,sum(~isfinite(S.predicted_labels)),S.runtime); end" > results/lapd_d2_smoke/logs/check.log 2>&1
```

若发生交互式半径提示、内存不足或无输出文件，先检查日志。若有非有限预测，保留全部样本和结果，先分析覆盖问题再决定是否扩展；不要删去缺失样本后计分。d=2 的耗时和内存可能高于 d=1，以试跑结果为依据。

**返回本地：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\d2_smoke | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd_d2_smoke" .\results\lapd_returns\d2_smoke\
```

回传目录应包含两份 `.mat`、`run_status.tsv`、每次运行的日志和 `check.log`。确认输入、参数、覆盖率和资源使用后再扩展。不能因为某个 d 的 ARI 更高而临时修改其他参数。

## 阶段 2：全部 34 个数据集，known K

**本地 PowerShell：** 如远程已经有同一批 34 份 scaled 输入，无需再次导出和上传。否则：

```powershell
.\.venv\Scripts\python.exe .\scripts\export_lapd_mat.py --all
scp .\data\lapd_mat\openml_*_scaled.mat "${LapdRemote}:${LapdRemoteRoot}/data/lapd_mat/"
```

只上传 scaled 文件，不混入 raw 输入。

**远程 bash：** 使用独立全量目录，每个数据集单独启动 MATLAB。全量包含试跑的两个 ID，重新运行并独立保存；不要混用两个目录的结果。

```bash
cd /tmp/ruan/manifold-clustering
PROJECT_ROOT="$PWD"
(
  set -e
  shopt -s nullglob
  inputs=(data/lapd_mat/openml_*_scaled.mat)
  if [ "${#inputs[@]}" -ne 34 ]; then
    echo "Expected 34 scaled inputs, found ${#inputs[@]}."
    exit 1
  fi
  if [ -e results/lapd_d2/run_status.tsv ]; then
    echo "Existing run_status.tsv; use a new directory for another run."
    exit 1
  fi
  for input_file in "${inputs[@]}"; do
    stem=$(basename "$input_file" .mat)
    if [ -e "results/lapd_d2/${stem}_known.mat" ] || [ -e "results/lapd_d2/logs/${stem}_known.log" ]; then
      echo "Existing output for $stem; use a new directory for another run."
      exit 1
    fi
  done
  sha256sum matlab/lapd_run_d2.m > results/lapd_d2/logs/entry_sha256.txt
  sha256sum "${inputs[@]}" > results/lapd_d2/logs/input_sha256.txt
  printf 'dataset\tmode\texit_code\n' > results/lapd_d2/run_status.tsv
  for input_file in "${inputs[@]}"; do
    stem=$(basename "$input_file" .mat)
    if matlab -batch "addpath('$PROJECT_ROOT/matlab'); lapd_run_d2('openml','$PROJECT_ROOT/$input_file','$PROJECT_ROOT/results/lapd_d2/${stem}_known.mat','$PROJECT_ROOT/vendor/LAPD','known')" > "results/lapd_d2/logs/${stem}_known.log" 2>&1; then
      code=0
    else
      code=$?
    fi
    printf '%s\tknown\t%s\n' "$stem" "$code" >> results/lapd_d2/run_status.tsv
  done
)
```

预期是 34 条状态记录，不是原手册的 68 条。单个数据集失败后继续其余数据集，保留退出码和错误日志。远程有调度器时，按服务器规则提交相同任务。

**返回本地：**

```powershell
New-Item -ItemType Directory -Force .\results\lapd_returns\d2 | Out-Null
scp -r "${LapdRemote}:${LapdRemoteRoot}/results/lapd_d2" .\results\lapd_returns\d2\
```

需要回传 `run_status.tsv`、全部已生成的 `.mat`、所有日志和源码、环境记录。退出码为 0 仍可能存在未分配预测。

## 阶段 3：本地审计并与 d=1 比较

不要直接运行原 `scripts/audit_lapd_results.py` 或原绘图脚本来处理 d=2：它们绑定了 stage4 的路径与 68 次运行，并会写入原结果文件。

下面的独立审计命令核对全部 34 个 ID，检查标签、索引、实际维度和显式参数；失败和未分配情况均保留。d=1 的逐样本结果也重新核对后，才计算配对比较。

**本地 PowerShell：**

```powershell
@'
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.metrics import adjusted_rand_score

root = Path.cwd()
run_dir = root / "results/lapd_returns/d2/lapd_d2"
d1_dir = root / "results/lapd_returns/stage4/lapd"
baseline = pd.read_csv(root / "results/zeus_openml_baseline.csv")
baseline = baseline.loc[baseline.method.eq("scaled_zeus")].set_index("openml_id")
assert len(baseline) == 34 and baseline.index.is_unique
status = pd.read_csv(run_dir / "run_status.tsv", sep="\t")
expected = {f"openml_{int(i)}_scaled" for i in baseline.index}
assert len(status) == 34 and set(status.dataset) == expected
assert not status.dataset.duplicated().any() and set(status["mode"]) == {"known"}

def inspect(path, dataset_id, d):
    saved = loadmat(path, squeeze_me=True, struct_as_record=False)
    truth = np.asarray(saved["labelsGT"]).ravel()
    pred = np.asarray(saved["predicted_labels"]).ravel()
    indices = np.asarray(saved["sample_indices"]).ravel()
    with np.load(root / f"data/embeddings/openml_{dataset_id}.npz") as source:
        assert np.array_equal(truth, source["labels"]), path
        assert np.array_equal(indices, source["sample_indices"]), path
        assert len(truth) == len(source["embeddings_scaled"]), path
    assert len(pred) == len(truth), path
    opts = saved["opts"]
    assert int(saved["openml_id"]) == dataset_id, path
    assert str(saved["mode"]) == "known" and str(saved["embedding_variant"]) == "scaled", path
    assert int(opts.intrdim) == d and int(saved["intrinsic_dim"]) == d, path
    assert opts.epsilon == 0 and opts.bandwidth == 10 and opts.parallel == 0, path
    assert str(opts.weight) == "two sided", path
    assert int(opts.knnnumber) == min(len(truth), max(100, int(np.ceil(.1 * len(truth))) + 10)), path
    true_k = len(np.unique(truth))
    assert int(opts.K) == true_k, path
    finite = np.isfinite(pred)
    complete = bool(finite.all())
    return {
        "status": "complete" if complete else "unassigned_predictions",
        "d": d, "n_samples": len(truth), "true_k": true_k,
        "requested_k": int(opts.K), "k_hat": int(saved["k_hat"]),
        "predicted_k": len(np.unique(pred[finite])),
        "n_unassigned": int((~finite).sum()), "coverage": float(finite.mean()),
        "ari": adjusted_rand_score(truth, pred) if complete else np.nan,
        "runtime_seconds": float(saved["runtime"]),
        "lapd_commit": str(saved["lapd_commit"]),
        "matlab_version": str(saved["matlab_version"]),
    }

rows = []
for run in status.itertuples(index=False):
    dataset_id = int(run.dataset.split("_")[1])
    row = {"openml_id": dataset_id, "mode": "known", "d": 2,
           "exit_code": int(run.exit_code), "kmeans_ari": float(baseline.loc[dataset_id, "ari"])}
    path = run_dir / f"{run.dataset}_known.mat"
    if run.exit_code != 0:
        row.update(status="process_failed", ari=np.nan)
    elif not path.is_file():
        row.update(status="missing_output", ari=np.nan)
    else:
        row.update(inspect(path, dataset_id, 2))
    rows.append(row)
d2 = pd.DataFrame(rows).sort_values("openml_id")
d2.to_csv(root / "results/lapd_d2_audit.csv", index=False, float_format="%.6f")
print("d=2 status:")
print(d2.status.value_counts().to_string())

d1_rows = []
for dataset_id in sorted(baseline.index):
    path = d1_dir / f"openml_{int(dataset_id)}_scaled_known.mat"
    d1_rows.append({"openml_id": int(dataset_id), **inspect(path, int(dataset_id), 1)})
d1 = pd.DataFrame(d1_rows)
fields = ["openml_id", "status", "ari", "coverage", "requested_k", "predicted_k",
          "runtime_seconds", "lapd_commit", "matlab_version"]
comparison = d1[fields].merge(d2.reindex(columns=fields + ["kmeans_ari"]),
                              on="openml_id", suffixes=("_d1", "_d2"), validate="one_to_one")
comparison["delta_d2_minus_d1"] = comparison.ari_d2 - comparison.ari_d1
comparison.to_csv(root / "results/lapd_d1_d2_known_comparison.csv", index=False, float_format="%.6f")
paired = comparison.loc[comparison.status_d1.eq("complete") & comparison.status_d2.eq("complete")]
print(f"Complete predictions: d1={d1.status.eq('complete').sum()}/34, d2={d2.status.eq('complete').sum()}/34")
print(f"Matched complete datasets: {len(paired)}/34")
if len(paired):
    if not paired.lapd_commit_d1.eq(paired.lapd_commit_d2).all():
        raise RuntimeError("LAPD commits differ; inspect before interpreting the comparison")
    if not paired.matlab_version_d1.eq(paired.matlab_version_d2).all():
        print("MATLAB versions differ: inspect before attributing changes to d")
    print(paired[["ari_d1", "ari_d2", "kmeans_ari"]].mean().to_string())
    delta = paired.delta_d2_minus_d1
    print(f"d2 wins/ties/losses (tolerance 1e-6): {(delta > 1e-6).sum()}/{(delta.abs() <= 1e-6).sum()}/{(delta < -1e-6).sum()}")
else:
    print("No matched complete datasets; no paired mean is available")
'@ | .\.venv\Scripts\python.exe -
```

如核对失败，先处理输入、参数或版本差异，不能跳过该项后直接报告排名。源码 commit 相同也不能排除工作区修改，需要结合阶段 0 的记录判断。

## 如何报告结果

先列出两种维度设置各自的完整预测数、未分配样本情况和失败数，再报告双方都有完整预测的交集上的平均 ARI。K-means 的均值也必须在同一个交集重算。

同时查看逐数据集 ARI 差值、实际簇数、覆盖率和耗时。若 d=2 改善了原来未分配的情况，这部分属于覆盖率改善，应单独说明；不能用不同成功集合的均值直接判断性能提升。对照中的 ARI 来自逐样本重新计算，输出 CSV 保留全部 34 个 ID。

本次可以回答“固定其他显式设置时，d=2 相比 d=1 的效果如何”，但不能仅凭一次结果断言真实内在维度是 2，或多流形方法的最佳表现就是这一结果。若后续改变半径、带宽、输入表征或源码，使用新的配置名称和目录，保留本次结果。
