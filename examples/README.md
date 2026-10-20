# 可复现示例与图注

所有表格由 `generate_examples.py` 生成，固定 seed=1729，**全部是合成演示数据**。
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

## 流程图与组合图

`diagram.json` 描述一个显式给定的检索增强系统，示意的是结构关系而不是测得的结果。
主链为 Question → Agent planner → Evidence retrieval → Answer；语料索引提供证据，
工具与结果生成交互，虚线表示回到 planner 的证据复核反馈。实际项目应依据实现更新
节点/边，不能把这张通用结构当作系统审计结论。

`composition.json` 组合该示意图与两张独立数据 SVG。面板 a 为 180×85 mm 原比例；
b 为 90×60 mm；c 在 85 mm 宽槽内等比缩放。字母标签占 5 mm 顶部带，最终文件
再次审核缩放后字号、引用隔离和文字保留。

## 预览说明

PNG/PDF 由同一 Matplotlib Figure 生成。发布验证还使用 Inkscape 渲染实际 SVG，
以发现依赖 SVG 阅读器才能出现的字体/间距/色条问题。SVG 是主文件，PNG 是便于
预览的副本。所有自动记录都有确定范围，视觉/科学审阅仍单独记录在测试报告。
