# Synthetic 方法比较图集：FigureFoundry 1.1.0

两张独立科研图已完成实际生成、SVG 渲染、最终尺寸与灰度审阅、数值核验和可编辑源交接。所有数据、图内标题和图注均明确标记为 **Synthetic**。本图集采用 180 mm 宽的论文版式规划。

## 正式交付与当前可编辑源

| 图 | 当前可编辑主源 | 同版预览与 PDF | 最终尺寸 |
|---|---|---|---|
| 1：学习轨迹 | [figure-1.svg](figures/figure-1.svg) | [300 dpi PNG](figures/figure-1.png)、[96 dpi 预览](figures/figure-1-96dpi.png)、[PDF](figures/figure-1.pdf) | 180 × 85 mm |
| 2：最终结果与独立运行 | [figure-2.svg](figures/figure-2.svg) | [300 dpi PNG](figures/figure-2.png)、[96 dpi 预览](figures/figure-2-96dpi.png)、[PDF](figures/figure-2.pdf) | 180 × 90 mm |

**以后继续精修时，从表中的 SVG 打开。** 所选变体在 [project.json](project.json) 和 [图集索引](notes/FIGURE_INDEX.md) 中均登记为 `polished`，`source.type` 为 `svg`。上游 JSON、共享样式、初始 SVG、重建脚本与原样复制的运行时均在 `frozen_upstream` 中留有身份与哈希；详情见 [源文件交接说明](notes/SOURCE_HANDOVER.md)。

[完整图注](notes/CAPTIONS.md) 与 [替代文本](notes/ALT_TEXT.md) 已由技能的 `project` 命令生成。SVG 根元素也带有实际写入的无障碍 title、desc 和对应关系。

## 图件表达与实算结果

图 1 显示每个 epoch 的六个运行均值、样本 SD 误差条及同义阴影带。每个运行包含七个重复时间点，独立样本数按 seed 计算为每方法六个运行。图 2 的左面板用从零开始的柱形和 SD 比较最终均值，右面板将所有 18 个终点分别显示在其 seed ID 上，并明确使用 50–85% 的扩展纵轴。右面板不连接独立运行，也不根据相同 seed 标签臆定方法之间的配对。

| 方法 | 最终成功率均值 (%) | 样本 SD（百分点） | 六个运行的范围 (%) |
|---|---:|---:|---:|
| Baseline | 57.881333 | 0.866006 | 56.337–58.904 |
| Context | 69.476167 | 1.252156 | 67.671–71.353 |
| Proposed | 79.047500 | 1.307871 | 77.382–80.181 |

这些值由独立的 Python 标准库核验脚本重新计算。SD 使用 n−1 分母，描述运行间离散程度；它不是泛化性能的置信区间。两张输入表分别有 126 行和 18 行，无缺失、无排除。18 个终点与学习表 epoch 30 的原值逐项完全相等。`latency` 原列完整保留，本任务没有使用它作图。依据：[独立数据与 SVG 坐标核验](qa/independent-data-check.json)、[原始数据副本哈希](reports/source-copies.json)。

全套图共享如下编码；线型仅用于有明确顺序含义的学习曲线。

| 方法 | 颜色 | 点形 | 线型 |
|---|---|---|---|
| Baseline | `#666A73` | 圆形 | 虚线 |
| Context | `#D55E00` | 三角形 | 点线 |
| Proposed | `#0072B2` | 方形 | 实线 |

Baseline 与 Proposed 的灰度明度接近，实际图中依靠点形、线型、方法标签和独立图例保持辨认能力。[配色分析](reports/palette.command-result.json) 实测文字 `#222222` 对白底对比度为 15.91。已查看 [图 1 灰度](figures/figure-1-grayscale-96dpi.png) 和 [图 2 灰度](figures/figure-2-grayscale-96dpi.png)。

## 版式候选与选择

图 2 两个候选使用相同数据、面板、统计定义、数值范围和语义样式，物理宽度均为 180 mm。

| 候选 | 尺寸 | 实际审阅结果 | 决定 |
|---|---|---|---|
| [横排](figures/figure-2-horizontal-v2.svg) | 180 × 90 mm | 均值与逐运行点可同时阅读；图例完整；单次运行差异清楚；页面占用较少 | 选中，并进行同样式精修 |
| [竖排](figures/figure-2-stacked-v2.svg) | 180 × 130 mm | 阅读顺序明确、面板更宽，但三个类别及六个 seed 产生较多空白；新增面积未增加信息 | 保留为未选候选 |

两版均实际查看了 96 dpi、放大和灰度预览。横排比竖排少占 40 mm 高度。详细判断与版本对应关系见 [视觉审阅记录](notes/VISUAL_REVIEW.md)。

## 实际执行的复现与核验

以下命令已经执行。工作目录为本 README 所在目录；前两次构建的完整子命令与退出码分别保存在 `figures/reproduction-log.json` 与 `logs/rebuild-commands.json`；核验输出按结果类型集中在 `reports/`、`qa/` 和每张正式图的审核文件中。渲染器消息保存在 `logs/renderer-warnings.json`。初始命令也保存在 [logs](logs)。

```bash
PYTHONDONTWRITEBYTECODE=1 python reproduce.py --outdir figures
PYTHONDONTWRITEBYTECODE=1 python reproduce.py --outdir qa/rebuild
PYTHONDONTWRITEBYTECODE=1 python qa/verify_numbers.py
PYTHONDONTWRITEBYTECODE=1 python qa/check_edit_guard.py
```

再次构建时给 `--outdir` 一个新的包内路径，例如 `qa/rebuild-next`；输出保护会拒绝覆盖已有文件。重建脚本只使用文档给出的 `plot`、`annotate`、`revision`、`audit` 命令、明确列出的 SVG 样式修改，以及 Inkscape 导出。

项目合同也已实际运行三次：先以 JSON 选源建立基线，然后进行 SVG 主源交接，最后用交接后的冻结基线复核。

```bash
python source/figurefoundry/scripts/figurefoundry.py project --spec project-before-polish.json --out reports/project-baseline.json --notes-dir notes/baseline
python source/figurefoundry/scripts/figurefoundry.py project --spec project.json --baseline reports/project-baseline.json --out reports/project-index.json --notes-dir notes
python source/figurefoundry/scripts/figurefoundry.py project --spec project.json --baseline reports/project-index.json --out reports/project-frozen-recheck.json
```

| 已执行的检查 | 结果与证据 |
|---|---|
| 原始表、完整重复、缺失及终点对应 | 两表 126 / 18 行；每方法六个运行；所有终点逐项匹配；无缺失或排除 |
| 数值与真实 SVG 数据图元 | 所选最终图 1 的全部 21 个均值顶点、所选图 2 的 18 个终点和三根柱高均与独立计算相符；两版布局候选也逐项核验 |
| 最终 SVG 结构、标签、尺寸 | 两图均通过；分别有 24 / 33 个可见文字元素、52 / 34 个 path、零 image；实际最小字号均 7.5 pt |
| 精修前后内容检查 | 两张图的 `revision` 均通过；只改文字颜色与非数据网格颜色，没有更改几何或文字内容 |
| 可编辑性真实试验 | 在独立副本中改标题 `<text>` 和原生背景 `<path>` 填色，Inkscape 重渲染可见两项修改；正式图 SHA 不变 |
| 样式修改的负例 | 未允许的文字修改返回 exit 2；用具体 text ID 允许后 exit 0；单独移动一个数据点返回 exit 2 |
| 来源交接与冻结基线 | `project` 两次 baseline 比较均通过，`revision.changes` 为空 |
| 独立重建 | 两张 SVG 与 PNG 均逐字节相同；PDF 的解压后页内容、资源及除创建时间外的元数据一致 |

证据入口：[最终尺寸与重建结果](qa/reproduction-and-size-report.json)、[PDF 内容比较](qa/pdf-metadata-comparison.json)、[编辑与误改拦截记录](qa/editability-and-guard-report.json)、[图 1 审核](figures/figure-1-audit.json)、[图 2 审核](figures/figure-2-audit.json)、[项目最终索引](reports/project-index.json)。

SVG 与 PDF 保存明确的 180 mm 物理宽度，同时提供 96 dpi 预览。最终 PNG 为 2126 × 1004 和 2126 × 1063 像素，标记约 300 dpi。

## 复现资料与使用记录

`source/figurefoundry` 提供本次使用的 1.1.0 运行时原样快照。[环境记录](source/ENVIRONMENT.json)、[源代码哈希](source/SNAPSHOT.json)、[使用记录](notes/USAGE_AND_FINDINGS.md) 与 [源文件交接说明](notes/SOURCE_HANDOVER.md) 支持后续修改和重建。
