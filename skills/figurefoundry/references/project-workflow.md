# 全论文图集、候选方案与主源交接

把同一研究的图放在一个项目合同中：每张图拥有自己的科学问题、数据来源、图注、替代文本和可编辑源，同时使用同一份语义样式。`ff_project.py` 负责记录与检查；绘图仍由 `plot`、`diagram`、`compose` 或项目已有分析脚本完成。

## 1. 图集的组织方式

| 科学角色 | 适合表达的内容 | 输出组织 |
|---|---|---|
| `overview` | 研究设计、方法总览、实验链路 | 简短文字、分组、明确阅读顺序 |
| `main-result` | 主结果与基线比较 | 主要定量面板、单位和误差定义 |
| `ablation` | 消融、组件贡献 | 相同尺度、相同方法编码 |
| `robustness` | 变化条件、独立重复、敏感性 | 分面、分布或共享尺度的多图 |
| `efficiency` | 质量—成本、时间、资源 | Pareto、散点或曲线 |
| `mechanism` | 因果假说、对象与过程 | 实体、类型化关系、整体与局部 |
| `graphical-abstract` / `toc` | 输入→方法→结果的一眼概览 | 独立目标尺寸，少量短标签 |
| `supplement` / `diagnostic` | 细节、诊断、补充证据 | 独立图号、完整来源与图注 |

先为每张图写一句它要回答的问题，再写 `claim`。对于多个面板，另外在设计记录写明各面板问题、数据基础、视觉锚点与阅读顺序。以结果的重要程度决定面积：主结果可跨两行，辅助验证使用较小面板。使用 `panel.grid` 表达真实跨行跨列布局，使用 `compose` 组合独立 SVG。

## 2. 项目默认样式

在项目中建立 `plot-defaults.json`，图件 JSON 用 `"defaults": "plot-defaults.json"` 引用。相对路径从图件 JSON 所在目录解析。运行 `plot` 时自动合并：**具名样式 → 项目默认值 → 当前图显式设置 → 当前面板显式设置**。

```json
{
  "version": 1,
  "theme": "engineering",
  "figure": {"axis_font_pt": 8, "tick_font_pt": 7, "min_font_pt": 6},
  "palette": {
    "Baseline": {"color": "#666A73", "marker": "o", "linestyle": "--"},
    "Proposed": {"color": "#0072B2", "marker": "s", "linestyle": "-"}
  },
  "panel_defaults": {"linewidth": 1.2, "markersize": 3}
}
```

样式选择：`minimal` 是清晰的无衬线基底；`engineering` 使用全框与紧凑刻度；`classic` 使用衬线和全框；`warm` 使用较柔和的线与点比例；`compact` 区分轴、刻度、图例的字号，并居中显示面板字母。配色由研究中的方法角色定义。主题控制外观，期刊的实际尺寸和字体值放入 `figure`。

`ff_style.resolve_plot_style()` 返回合并后的规范及 `style_provenance`，包含默认文件的 SHA256、合并次序和样式标识。更换数据或物理版式而保持同一风格时，样式标识保持一致。数据列、统计估计、独立单位、拟合模型分别在面板内声明。

## 3. 项目合同的最小结构

```json
{
  "version": 1,
  "project_id": "dose-response-study",
  "question": "处理是否改变响应轨迹？",
  "style": {
    "palette": {
      "Baseline": {"color": "#666A73", "marker": "o", "linestyle": "--"},
      "Proposed": {"color": "#0072B2", "marker": "s", "linestyle": "-"}
    },
    "text_color": "#222222",
    "background": "#FFFFFF"
  },
  "figures": [{
    "id": "fig1",
    "role": "main-result",
    "question": "各组响应随剂量如何变化？",
    "claim": "由实际结果填写结论",
    "caption": "由实际数据填写组别、独立样本、中心估计和区间定义。",
    "alt_text": "按阅读顺序描述曲线、比较对象和主要变化。",
    "evidence_files": ["data.csv"],
    "units": {"dose": "mg", "response": "a.u."},
    "statistics": {"unit": "subject", "estimator": "mean", "interval": "95% t CI"},
    "quantities": {"independent_subjects": 12},
    "entities": [],
    "relations": [],
    "variants": [{
      "id": "balanced",
      "source": {"type": "json", "path": "figure.json"},
      "svg": "figures/figure.svg",
      "expected_labels": ["Dose (mg)", "Response (a.u.)"],
      "rationale": "适合比较各组曲线并保留足够图例空间"
    }],
    "selected_variant": "balanced"
  }]
}
```

执行：

```bash
python <skill-dir>/scripts/figurefoundry.py project --spec project.json \
  --out release/project-index.json --notes-dir release/notes
```

得到带来源哈希、变体选择和 SVG 审核的 JSON，以及 `FIGURE_INDEX.md`、`CAPTIONS.md`、`ALT_TEXT.md`。`source.type` 可选 `json`、`python`、`r`、`tex`、`svg`、`drawio`、`plotly`。尚在设计中的候选可以先记录源文件，在渲染后补 `svg` 与完整 `expected_labels`。

## 4. 两至三个候选，科学内容保持一致

为需要比较的图建立具名候选，例如 `balanced`、`hero`、`schematic-led`。让布局和样式分别有具体理由：主结果面积、读者视线、图例空间、整体与局部的对照。候选使用同一数据、同一科学问题和同一计数。

按相同物理宽度渲染候选，同时查看实际尺寸、放大和灰度预览。在设计记录中逐项填写：读者首先看到什么、比较是否容易、标签是否清楚、箭头含义是否明确。将最合适的版本写入 `selected_variant`，保留其他源文件用于后续选择。

修改前后检查：

```bash
python <skill-dir>/scripts/figurefoundry.py project --spec project-v2.json \
  --baseline release/project-index.json --out release/project-index-v2.json
```

比较内容包括项目问题、各图科学字段、实体和关系、锁定数值、证据文件 SHA。实际分析有更新时，建立新的分析版本和新基线，明确记录更新结果。

## 5. 整体、局部和锁定数量

`entities` 中的对象具有稳定 `id` 与 `label`。局部视图引用同一对象的 `parent`，关系用 `source`、`target`、`kind` 表达。例如一块传感器与其局部层结构应共享实体关系，而不是在局部图另造一个身份。

可使用 `representation: "whole" | "part" | "detail"` 表达整体、组成部分与细节；`part` / `detail` 对应已声明父对象。`quantity_ref` 引用 `quantities` 中的锁定值，显式 `quantity` 与引用值一起出现时相等。单纯示例对象、完整枚举、代表性对象加汇总等不同表示方式，应在图注和设计记录中写清楚实际计数方式。

Agent / RAG / 反馈图额外填写：更新的是哪个对象、使用哪个信号、什么算子执行更新、更新频率、哪些内容保留、哪些内容冻结、接受或拒绝的判据。用类型化关系区分数据流、控制流、更新、对照和假设关系。可参考 [参考图件审查记录](reference-intake.md)。

## 6. 手工编辑 SVG 后的主源交接

在 Inkscape 等编辑器精修之后，把选定变体的 `source` 指向实际可继续编辑的 SVG，原有 Python/JSON/TikZ 源列入 `frozen_upstream`：

```json
{
  "id": "polished",
  "source": {
    "type": "svg",
    "path": "figures/figure-polished.svg",
    "frozen_upstream": ["figure.tex"]
  },
  "svg": "figures/figure-polished.svg",
  "expected_labels": ["Dose", "Response"],
  "rationale": "在最终物理尺寸下完成标签和间距精修"
}
```

重新运行项目检查并保存基线。此后的修订可检测冻结源内容和冻结关系的变化。导出新版本时使用新文件名，使选定的人工修改保留可追溯身份。数据更新需要重算时，从原始分析源建立新变体，再比较与选定版本的内容和排版。

## 7. 图形摘要、TOC 和提交交接

图形摘要单独写 `role=graphical-abstract`，TOC 写 `role=toc`。使用输入、核心方法、主要输出的明确方向；通常不需要面板字母。先核对目标期刊该类图的尺寸和文字要求，再在缩略显示尺寸查看短标签是否仍能辨认。

交接记录包括所选源、SVG、与该版本一致的 PDF/PNG、来源哈希、图注、替代文本、正文引用与放置位置。可将 `FIGURE_INDEX.md` 的图号与手稿中的引用逐一核对，随后把最终文件清单交给手稿工作流。

## 8. 美化已有脚本或 Notebook

```bash
python <skill-dir>/scripts/figurefoundry.py inventory analysis.py notebook.ipynb
```

输出绘图布局、坐标/图例/样式和导出调用所在文件、行号、Notebook 代码单元位置。先找到实际生效的参数和出口，再修改字体、线宽、点形、图例位置、网格与色条；保留已确认的数据变换和统计计算。以源码记录为依据重新导出，并把新版加入项目合同。

| 想改的效果 | 优先修改的位置 | 验证方式 |
|---|---|---|
| 全论文方法颜色、点形、线型一致 | `plot-defaults.json` 的 `palette` | `project` 的样式检查及乱序分组测试 |
| 字号与实际列宽匹配 | `figure` 的尺寸和各角色字号 | `audit` + 实际尺寸预览 |
| 一张主图、若干辅助面板 | `panel.grid`、行列比例或 `compose` | 版式占位测试 + 预览 |
| 改色后数值与关系保持一致 | 主源和项目科学字段 | `revision` + 项目基线比较 |
| 精修 SVG 后继续迭代 | `selected_variant` 与 `source` | 冻结上游源的 SHA 比较 |
