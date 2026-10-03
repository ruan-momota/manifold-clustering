# Next Steps

## 当前阶段的目标

现在先不急着决定最终要改哪种算法，也不急着确定最终 research question。

目前已经完成的 ZEUS + K-means、CPP、LAPD、WMC 实验，可以看作第一轮 **benchmarking**：先比较不同方法在同一批数据上的表现，找出哪些地方现有方法做得不好。

接下来最重要的是弄清楚：

**ZEUS + K-means 表现差的数据集，为什么会差？**

如果只是因为数据量太少，那么这些数据集可能本身就很难聚类，也不一定适合作为后续重点。如果不是数据量的问题，而是和数据结构、密度等因素有关，那么这些情况才更值得继续研究。

---

## 1. 先分析 K-means 表现差的数据集

### 要做什么

先把 34 个数据集整理到一张表里，至少加入：

- dataset ID
- 样本数
- 类别数
- 平均每类样本数
- ZEUS + K-means ARI
- CPP ARI
- LAPD ARI
- WMC ARI

然后重点看 K-means ARI 较低的数据集，例如 ARI < 0.5 的数据集。

### 为什么做

导师担心 K-means 表现差可能只是因为这些数据集样本太少。

如果确实是：

> 样本越少，K-means 越差

那么问题可能不是 K-means 本身，而是数据不足。这种情况下，换更复杂的聚类方法也未必能解决。

如果一些样本很多的数据集仍然表现很差，那这些数据集更值得继续研究。

---

## 2. 检查数据量和聚类效果的关系

### 要做什么

先画几个简单的图：

- 样本数 vs K-means ARI
- 平均每类样本数 vs K-means ARI
- 类别数 vs K-means ARI

同时对比：

- K-means 表现很差的数据集
- K-means 表现很好的数据集

### 为什么做

这是最快判断“低分是不是主要由数据量造成”的方法。

这一步会决定后面应该继续研究哪些数据集。

---

## 3. 对值得研究的数据集做结构分析

### 要做什么

如果发现 K-means 的低分不能简单用样本量解释，再分析这些数据集的 embedding 结构。

优先看：

- intrinsic dimension
- nearest-neighbor 距离
- 数据是否很稀疏
- kNN graph 是否容易断开
- 不同类别之间是否明显重叠

不用一次做很多指标，先从最容易解释的几个开始。

### 为什么做

目的是找出：

> 什么样的数据上 ZEUS + K-means 容易失败？

如果能找到比较稳定的规律，就可以把它变成后面的 research question。

---

## 4. 加入 ZEUS + Spectral Clustering baseline

### 要做什么

在 K-means 表现较差、但数据量不算特别少的数据集上，先测试普通 Spectral Clustering。

重点尝试几个不同的 nearest-neighbor 数量。

### 为什么做

这样可以判断：

> K-means 差的时候，单纯换成基于邻接图的聚类方法是否就能改善。

如果 Spectral 已经能明显提升，说明这些数据可能更适合用局部邻接关系来聚类。

如果 Spectral 也不行，但 CPP 能提升，那么 CPP 学到的新 representation 可能才是关键。

---

## 5. 对 LAPD 做参数检查

### 要做什么

重点测试 LAPD 的 `D`。

包括：

- 手动尝试几个不同的 D
- 如果代码支持，测试自动选择 D
- 对比 estimated intrinsic dimension 和较好的 D 是否有关

先在少量代表性数据集上测试，不需要马上跑全部 34 个数据集。

### 为什么做

现在 LAPD 的结果还不能直接说明算法不适合 ZEUS embedding。

如果 D 没有调好，当前低分可能只是参数问题。

所以需要先确认：

> 调整 D 后，LAPD 是否仍然表现差。

---

## 6. 对 WMC 先检查 graph 问题

### 要做什么

目前先不要追求 WMC 的最终 ARI。

先看不同参数下：

- graph 有多少 connected components
- 每个点平均连接多少邻居
- graph 是否过于稀疏
- graph 变得更连通后 ARI 是否提高

重点调整和稀疏程度、输入尺度有关的参数。

### 为什么做

现在 WMC 的 graph 在绝大多数数据集上都严重断开。

如果 graph 本身已经碎成很多小块，后面的聚类结果就很难可靠。

所以要先确认 WMC 表现差是不是因为 graph 构建出了问题。

---

## 7. 暂时不要急着换新的 foundation model

### 要做什么

先把 ZEUS 上的问题分析清楚。

只有在后面发现：

> 某些方法可能是被 ZEUS embedding 的结构限制了

再考虑换一个 tabular foundation model 做对照。

### 为什么做

换 foundation model 工作量比较大，而且现在还不知道问题到底出在 ZEUS、聚类方法，还是数据本身。

先把现有结果分析清楚，后面再决定是否值得做。

---

## 8. 根据 benchmarking 结果重新确定 research question

现在不用马上固定最终题目。

目前可以先用下面这个问题指导实验：

> **在什么样的数据上，ZEUS + K-means 会表现较差？这些失败是否可以通过其他聚类方法改善？**

后面根据结果再收窄。

例如：

- 如果主要问题是数据量太少，就需要换研究重点；
- 如果和 density / intrinsic dimension 有明显关系，可以研究不同数据结构适合什么聚类方法；
- 如果 CPP 在某一类数据上稳定优于 K-means，可以进一步研究 CPP 为什么有效；
- 如果 Spectral 就能改善，可以重点研究 graph-based clustering；
- 如果 LAPD 或 WMC 调参后仍然很差，也可以把“不适合的原因”作为结果的一部分。

---

## 建议的执行顺序

1. 整理 34 个数据集的样本数、类别数和现有 ARI。
2. 先检查样本量和 K-means ARI 的关系。
3. 找出“数据量不算少，但 K-means 仍然很差”的数据集。
4. 对这些数据集做简单的结构分析。
5. 跑 ZEUS + Spectral Clustering。
6. 在少量代表性数据集上调 LAPD 的 D。
7. 检查 WMC graph 连通性和参数的关系。
8. 根据这些结果，再决定后面的 research question 和是否需要改进某个方法。

核心原则是：

**先通过 benchmarking 找到真正的问题，再决定要改什么。不要为了“必须提出一个新算法”而硬做改进。**
