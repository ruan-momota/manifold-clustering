# CPP 官方 CIFAR-10 实验：远程执行手册

本手册对应 [04_cpp_cifar10.ipynb](../notebooks/04_cpp_cifar10.ipynb)。本地项目使用 Windows PowerShell，以下远程命令假定服务器使用 Linux bash。按顺序完成；每一步只核对当前实验需要的信息。论文的 CIFAR-10 结果是 ACC 97.4%、NMI 93.6%；notebook 目前记录的是训练批次的指标均值，两者的统计方式不完全相同，不能只凭数值接近就宣布完整复现。[论文 Table 1](https://arxiv.org/html/2306.05272v5#S4.SS1)、[官方训练入口](https://github.com/LeslieTrue/CPP/blob/main/main.py)

## 0. 核对服务器

在远程终端进入项目目录。此前 LAPD 实验使用的是 `/tmp/ruan/manifold-clustering`；若服务器清理过 `/tmp`，先找到或重新同步项目。

```bash
cd /tmp/ruan/manifold-clustering
pwd
nvidia-smi
python3 --version
df -h .
```

**核验：** `pwd` 是实际项目根目录；`nvidia-smi` 列出 GPU、驱动版本、显存和当前占用；Python 至少为 3.10；磁盘有空间容纳 CIFAR-10、CLIP 权重和特征缓存。请先把这四项输出发给我，尤其是 GPU 型号、显存、驱动和可用磁盘。它们决定下一步该安装哪个 CUDA 版 PyTorch。

## 1. 传入 notebook，固定官方源码

本地新增的 notebook 尚未通过 Git 发布。从本地 PowerShell 在项目根目录执行，替换登录地址；如果远程项目路径不同，也替换路径：

```powershell
$CppRemote = "USER@HOST"
$CppRoot = "/tmp/ruan/manifold-clustering"
scp notebooks/04_cpp_cifar10.ipynb "${CppRemote}:${CppRoot}/notebooks/"
```

远程执行：

```bash
cd /tmp/ruan/manifold-clustering
mkdir -p vendor
git clone https://github.com/LeslieTrue/CPP.git vendor/CPP
git -C vendor/CPP checkout cb39bdc65f346b4cb5950d14af2e393a5f6a3566
git -C vendor/CPP rev-parse HEAD
ls -l notebooks/04_cpp_cifar10.ipynb
```

**核验：** Git 输出的完整 commit 为 `cb39bdc65f346b4cb5950d14af2e393a5f6a3566`，notebook 文件存在。若 `vendor/CPP` 已存在，直接核对 commit，不重复克隆。该目录已在本项目的 `.gitignore` 中；远程 `git pull` 不会带来它。

## 2. 准备独立的 GPU 环境

本项目 `uv.lock` 固定了 CPU 版 PyTorch，因此不要在远程 GPU 环境里直接执行 `uv sync`。先新建独立环境：

```bash
cd /tmp/ruan/manifold-clustering
python3 -m venv .venv-cpp
source .venv-cpp/bin/activate
python -m pip install --upgrade pip
```

根据第 0 步的驱动信息，到 [PyTorch 官方安装页](https://pytorch.org/get-started/locally/)选择 **Linux / Pip / Python / 适合该服务器的 CUDA 版本**，在已激活的 `.venv-cpp` 中执行页面给出的安装命令。随后安装 notebook 其余依赖：

```bash
python -m pip install numpy pandas scipy scikit-learn tqdm ipykernel jupyterlab
python -m pip install git+https://github.com/openai/CLIP.git
python -c "import torch, torchvision, clip; ok=torch.cuda.is_available(); print(torch.__version__, torchvision.__version__, ok, torch.cuda.get_device_name(0) if ok else 'no CUDA device')"
python -m ipykernel install --user --name cpp-gpu --display-name "CPP GPU"
```

**核验：** 最后一条 Python 检查输出 `True` 和预期 GPU 名称；`torchvision` 与 `torch` 都能导入。保留实际 PyTorch 安装命令及版本输出。若 CUDA 检查为 `False`，停在这里，返回第 0 步输出和安装日志。[PyTorch 安装与 GPU 检查](https://pytorch.org/get-started/locally/)

## 3. 提取 CIFAR-10 的 CLIP 特征

用远程 Jupyter 打开 `notebooks/04_cpp_cifar10.ipynb`，选择 `CPP GPU` 内核。依次运行“环境”代码单元和“提取并缓存 CLIP 特征”代码单元。首次运行会下载 CIFAR-10 与 CLIP ViT-L/14 权重，并将特征写到 `data/cpp/cifar10_clip_vitl14.pt`。后续重开 notebook 会直接读缓存。

**核验：** 首个代码单元显示 `device cuda` 和正确的 CPP commit；特征单元输出 `features: (50000, 768) labels: (50000,)`。若下载、CUDA 显存或形状检查失败，保存错误输出，暂不运行训练单元。

## 4. 训练并保存结果

接着运行“训练 CPP”与“汇总与保存”两个代码单元。notebook 使用论文附录 C 的 CIFAR-10 网络维度、批量大小和 5 轮训练；第一轮用于初始化。官方 README 的示例命令写 15 轮、预热 50 步，不能把两种设置混称为同一次实验。[论文附录 C](https://arxiv.org/html/2306.05272v5)、[官方 README](https://github.com/LeslieTrue/CPP#training)

**核验：** 训练打印 `epoch 1/5` 到 `epoch 5/5`，没有非有限损失或 CUDA 错误；汇总表含第 2～5 轮的 ACC、NMI；生成 `results/cpp_cifar10_batch_scores.csv` 与 `models/cpp_cifar10_paper_settings.pt`。若显存不足，先记录报错和 GPU 占用，不直接调小论文的批量或网络维度后继续声称复现。

## 5. 返回给我核对

请把以下内容带回本地或发给我：

- 第 0、2 步的环境输出和实际 PyTorch 安装命令。
- 运行后保存的 notebook，以及 `results/cpp_cifar10_batch_scores.csv`。
- 若中途失败，发生错误的完整单元输出；模型权重先留在服务器，不必传回。

在远程 Jupyter 中先保存 notebook。本地 PowerShell 可用第 1 步的变量取回两个小文件：

```powershell
scp "${CppRemote}:${CppRoot}/notebooks/04_cpp_cifar10.ipynb" results/cpp_cifar10_executed.ipynb
scp "${CppRemote}:${CppRoot}/results/cpp_cifar10_batch_scores.csv" results/
```

拿到这些结果后，我会先核对数据形状、版本、训练是否完整和批次分数，再决定是否需要补充与论文更严格一致的完整数据集评分。不要将批次均值直接写成论文 Table 1 的复现分数。
