# 实际使用与核验记录

日期：2026-10-20。数据状态：Synthetic。范围：只使用 `learning.csv` 和 `endpoints.csv` 两张合成表；仅在本证据目录创建输出；未修改共享技能或共享测试，也未运行共享测试套件来替代实际任务。

## 使用的技能说明和接口

先阅读 `SKILL.md`，随后按任务路由阅读 scientific-integrity、plot-spec、project-workflow、quality-workflow、svg-contract。使用的技能 CLI 为 doctor、inspect、plot、palette、annotate、revision、audit、project。绘图本身完全使用文档列出的原生 JSON 接口；没有添加新绘图后端或修改内部实现。外加 Python 标准库的独立数字/坐标检查、明确的 SVG 样式编辑和 Inkscape 预览。原样复制的运行时用于单独重建。

## 第一轮真实使用的发现

1. Doctor 实测原生依赖齐备，Inkscape 可用。环境为 Python 3.12.14、Matplotlib 3.10.8、NumPy 2.3.5、pandas 2.2.3、SciPy 1.17.0、Inkscape 1.2.2。不曾调用缺失的可选后端。
2. Inspect 给出 126 与 18 行、所有列缺失为零，并记录源文件 SHA256。独立核验确认 18 条终点与 epoch 30 精确一致。
3. 共享 defaults 的 style SHA 在独立 plot 命令中一致；本地复制的运行时没有被修改。Palette 报告正确显示 Baseline / Proposed 的灰度亮度十分相近；没有将“总体 palette passed”误解成每种颜色都能靠灰度单独辨识。
4. 初版学习规格 `xlim=[0,30]` 使两端 marker 部分被裁切。最小复现就是 `specs/figure-1-learning.json` 配合 `figures/figure-1-learning.svg` 与 `qa/figure-1-learning-96dpi.png`。这是显式范围的版式副作用，工具已给出范围审查提示；v2 扩为 `[-0.8,30.8]`，未改数据。无需修改技能。
5. 初版图 2 未给散点另列图例，灰度下独立使用时依赖跨图关联。最小复现为 `specs/figure-2-horizontal.json` 和对应初版 SVG。两套 v2 候选都添加三列底部 marker 图例，再比较版式。所有原始点保持可见。

## 内容保护与交接的实际行为

精修只将文字填色改为 `#222222`，将非数据 y 网格 stroke 从 `#DDE2E7` 改为 `#C6CDD5`。所有数据颜色、线型、点形、文字内容和几何保持不变。两张 `revision` 都返回 exit 0。

一次性可编辑试验修改标题 text 和页面背景 path fill，渲染后确实可见两项改动。工具正确表现为：未允许改字 exit 2；按 `pilot-edit-title` 具体文字 ID 允许改字后 exit 0；只将一个真实散点的 SVG y 坐标移动 10 个 SVG 单位时 exit 2。正式 SVG 的 SHA256 在试验前后保持一致。相关命令及输出详见 `qa/editability-and-guard-report.json`。

主源选为 SVG 后，`project` 返回“Selected source is not a JSON plot specification”的 style identity warning。这是工具说明过的检查范围，不是自动完成了 SVG 的颜色解析。本图集保留 JSON 基线的样式检查、精修前后 `revision`、独立数据坐标检查和最终视觉审阅作为互补证据。用最终冻结索引再次核验，科学字段、来源及冻结关系均无变化。

`revision` 的内部 audit 仅检查存在可编辑文字，警告建议补充 expected labels；因此本任务对每张最终图额外执行了带完整预期字符串列表、物理尺寸和最小字号的 `audit`。未把内部文字存在性检查当成完整标签核对。

## 重建与输出的实际行为

`reproduce.py --outdir figures` 生成正式图，随后 `--outdir qa/rebuild` 在独立输出路径完成第二次完整生成。两张 SVG 和 Inkscape PNG 的 SHA256 分别与正式图完全相等。PDF 文件 SHA256 不等，创建时间不同；用 pypdf 读取并解压页面对象后，所有页内容、资源和非日期元数据相同。

最初尝试直接按明文正则检查 PDF CreationDate 未匹配压缩对象中的元数据，保留了 `qa/pdf-creationdate-raw-probe.json` 作为未奏效的方法记录；后续对象级读取成功，结果见 `qa/pdf-metadata-comparison.json`。这个检查方法的调整不是绘图技能错误，也没有重写原始 PDF。

## 未声称检查过的范围

没有目标期刊、文章类型或投稿阶段，采用 planning profile；没有声称期刊合规。没有运行完整色觉模型或所有 SVG 编辑器的交互往返测试。统计结论严格限于 Synthetic 表内描述，没有添加显著性检验、真实实验独立性证明或对新测试总体的泛化区间。结构审核和基线检查不能单独证明实验真实性。
