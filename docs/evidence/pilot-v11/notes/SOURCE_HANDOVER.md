# 可编辑源与冻结上游的交接

## 继续编辑从哪里开始

| 图 | 当前活动源 | 冻结的绘图规格 | 共享样式 |
|---|---|---|---|
| figure-1 | `figures/figure-1.svg` | `specs/figure-1-learning-v2.json` | `specs/plot-defaults.json` |
| figure-2 | `figures/figure-2.svg` | `specs/figure-2-horizontal-v2.json` | `specs/plot-defaults.json` |

`project.json` 的 `selected_variant` 均为 `polished`，两个 `source.type` 均为 `svg`。所选图 2 是横排布局；竖排及所有初版均保留，但不是当前活动源。

明确的来源链为：原样复制的 CSV → JSON 规格及共享默认值 → FigureFoundry 原生 SVG → `annotate` 添加 title/desc → `*-before-polish.svg` → 仅文字和网格颜色精修 → 当前 SVG。`reproduce.py` 记录了所有步骤。最后一次样式修改未改变任何可见文字、数据图元坐标、节点结构、ID 或引用。

## 样式修改的核验

先将选中的 SVG 另存为新的版本，保持当前主源作为比较参考。例如只修改图 2 的样式后，使用文档接口：

```bash
python source/figurefoundry/scripts/figurefoundry.py revision figures/figure-2.svg figures/figure-2-next.svg --min-font-pt 7
python source/figurefoundry/scripts/figurefoundry.py audit figures/figure-2-next.svg --min-font-pt 7 --width-mm 180 --height-mm 90 --labels figures/figure-2-labels.json
```

然后用 Inkscape 按相同 DPI 导出并查看实际尺寸与放大预览。将新版本登记为新的具名变体，保留已有变体、`frozen_upstream` 和来源路径；用 `reports/project-index.json` 作基线，生成一个新项目报告。若版式真的调整，几何必然变化，不能将 `revision` 不通过解释为纯样式精修已经安全。此时结合独立数值检查、项目科学字段与来源哈希，再作新的视觉审阅。

本次实际执行过：只改样式通过；只移动一个数据点被拒绝；不允许标题改字时被拒绝；明确给出具体 text ID 时允许改标题且保留其余内容。可复现脚本为 `qa/check_edit_guard.py`。负例 SVG 只用于核验，不是交付图或候选结果。

## 修改可编辑文字

SVG 的文字是原生 `<text>`，不是描边字形。原生导出给文字的父 `<g>` 分配了 ID，文字元素本身通常没有 ID；文档中的 `--allow-text-id` 要求具体的 text/tspan ID。因此，本次在两个一次性试验副本中的同一标题文字节点上设置 `id="pilot-edit-title"`，再执行允许改字的比较。没有对正式主源作此试验性改字。

如果要使用这个允许改字的接口，应先对比较前后的同一个具体文字节点设置同样的稳定 ID，保存“开始编辑前”的基线副本，再进行改字；不能将父分组 ID 当成 text ID。实际试验图为 `qa/editability-text-and-shape-96dpi.png`，可看见标题和浅黄色页面背景两项修改。此项验证说明 XML 原生文字与图形能够被编辑并由 Inkscape 渲染，不代表已经逐一测试其他编辑器的往返保存行为。

## 更新真实数据时

从 CSV 和冻结 JSON 建立新的分析/作图变体，更新图注、统计定义和来源版本，重新生成几何。不要通过拖动数据点或柱高来更新数值。当前项目基线会检测数据哈希、已声明科学字段、锁定数量或冻结上游的变化；分析真的更新时需要明确建立新的基线并解释差异。

原样复制的运行时与依赖版本一起保留在 `source/`。重新构建时给出一个新的包内输出目录，例如 `python reproduce.py --outdir qa/rebuild-next`，不会覆盖这两个已经选定的 SVG。
