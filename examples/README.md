# 可复现示例与图注

主绘图示例表格由 `generate_examples.py` 生成，固定 seed=1729，**全部是合成演示数据**。
不要引用这些数值作为实际实验结论。运行 `python examples/generate_examples.py`
会重建表格、规格、SVG/PDF/PNG、manifest 和拼版审核。

## 四面板图

`outputs/benchmark.svg`，180×135 mm。三个方法的颜色和线/标记编码保持一致。

**示例图注：** Synthetic demonstration of a four-panel scientific figure. (a)
Learning trajectories show arithmetic means and pointwise two-sided Student-t
95% confidence intervals across six synthetic independent run IDs per method;
the same IDs recur across epochs, and no simultaneous confidence-band or paired
hypothesis-test claim is made. (b) Final-epoch outcomes show every run with a
boxplot summary (median, quartiles and 1.5-IQR whiskers). (c) The separate supplied
synthetic task summary is represented by editable vector cells and a common color
scale; these cells are demonstration percentages, not a reaggregation of panels
(a–b). (d) A separate synthetic set of quality/cost operating points marks strict
Pareto dominance (lower cost and higher success are preferred). No unobserved
operating points are interpolated. All examples are illustrative.

## 非对称主结果图

[asymmetric.svg](outputs/asymmetric.svg)，183×125 mm。
[asymmetric.json](asymmetric.json) 用三张真实数据面板示范跨行跨列：左侧学习曲线
占两行，右上为末次结果和独立运行点，右下为各方法的经验累积分布。

**示例图注：** Synthetic evidence hierarchy. The main panel shows mean learning
trajectories and pointwise 95% Student-t confidence intervals across six independent
run IDs per method. The upper-right panel shows final-epoch mean and SEM
with every independent run overlaid. The lower-right panel shows the empirical
cumulative distribution of those final-epoch results. Color, marker and line
identities are shared across panels; the larger panel is a layout choice and does
not alter the data or its statistical weight.

## 四类 Seaborn 配方

运行 `python examples/custom_seaborn.py --out build/seaborn-demo` 重建四类配方。
包装脚本显式传入 `--synthetic-demo`；Skill 内的 `ff_seaborn.py` 也可接收
`--data` 指定真实输入表。配方的字段与统计约定见
[quality-workflow.md](../skills/figurefoundry/references/quality-workflow.md)。

| 配方与 SVG | 本例实际表达 | 输入与变换 |
|---|---|---|
| [FacetGrid](outputs/seaborn/facet.svg) | 分条件比较剂量与响应，方法同时用颜色和点形区分 | 每个原始观测点，使用表中全部条件 |
| [PairGrid](outputs/seaborn/pair.svg) | 三个变量的成对关系和对角分布 | 同一变量在各方法间使用共同分箱 |
| [JointGrid](outputs/seaborn/joint.svg) | 剂量—响应点图与边际分布 | 原始点；边际分箱由完整数据确定 |
| [clustermap](outputs/seaborn/cluster.svg) | 独立单位的三变量聚类矩阵 | 全部 48 行，逐列 z-score，average/euclidean 层次聚类 |

四类配方均输出 SVG、PNG 和 manifest。Manifest 记录数据状态、源、处理方法、
所需标签与最终 SVG 检查；聚类图还记录实际使用的单位及行列顺序。

## 流程图与组合图

`diagram.json` 描述一个显式给定的检索增强系统，示意的是结构关系而不是测得的结果。
主链为 Question → Agent planner → Evidence retrieval → Answer；语料索引提供证据，
工具与结果生成交互，虚线表示回到 planner 的证据复核反馈。实际项目应依据实现更新
节点/边，不能把这张通用结构当作系统审计结论。

`composition.json` 组合该示意图与两张独立数据 SVG。面板 a 为 180×85 mm 原比例；
b 为 90×60 mm；c 在 85 mm 宽槽内等比缩放。字母标签占 5 mm 顶部带，最终文件
再次审核缩放后字号、引用隔离和文字保留。

## 预览说明

数据图的 PNG/PDF 由同一 Matplotlib Figure 生成；Seaborn 示例生成 SVG/PNG。
发布验证还使用 Inkscape 渲染实际 SVG，
以发现依赖 SVG 阅读器才能出现的字体/间距/色条问题。SVG 是主文件，PNG 是便于
预览的副本。所有自动记录都有确定范围，视觉/科学审阅仍单独记录在测试报告。
