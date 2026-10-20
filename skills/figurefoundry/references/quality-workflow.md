# 配色、替代文本与 SVG 精修检查

## 1. 配色分析

`palette` 从明确的 sRGB 十六进制颜色计算相对亮度、文字与背景对比度、组间灰度区别，并列出点形、线型、纹理等冗余编码。

```json
{
  "palette": {
    "Baseline": {"color": "#666A73", "marker": "o", "linestyle": "--"},
    "Proposed": {"color": "#0072B2", "marker": "s", "linestyle": "-"}
  },
  "background": "#FFFFFF",
  "text_color": "#222222",
  "minimum_text_contrast": 4.5,
  "pair_review_ratio": 1.5
}
```

```bash
python <skill-dir>/scripts/figurefoundry.py palette --spec palette.json
```

线性化 sRGB 的相对亮度为 `0.2126 R + 0.7152 G + 0.0722 B`；对比度用 `(较亮 Y + 0.05)/(较暗 Y + 0.05)`。公式与一般文字的参考对比度来自 [W3C WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)。工具的 `passed` 对应用户声明的文字/背景阈值。灰度组间比值的 `pair_review_ratio` 是可调设计参数，CIE L* 与 `delta_L` 是明度描述指标。

组间对比不充足时，优先增加可见的点形、线型或直接标签，再调整色相和明度。全套图沿用相同角色编码。在缩略图、灰度或色觉模拟预览中，检查曲线、面积、符号和标签是否仍容易匹配；把实际审阅记录与文件版本对应。测量对比度与运行完整色觉模型是不同步骤。

## 2. 可编辑 SVG 内的标题和替代文本

```bash
python <skill-dir>/scripts/figurefoundry.py annotate figure.svg \
  --title "Dose response" \
  --description "Two groups are compared over the observed doses; points show independent subjects." \
  --out figure-described.svg
```

新 SVG 增加根级 `title`、`desc`、ARIA 对应关系，原来的图元和可编辑标签保留。文本应描述图形的阅读顺序、对象和数据关系，具体数值与结论由真实数据和图注提供。描述文字与图内 `<text>` 标签分别处理。

## 3. 样式精修的内容比较

```bash
python <skill-dir>/scripts/figurefoundry.py revision original.svg polished.svg
python <skill-dir>/scripts/figurefoundry.py revision original.svg relabelled.svg \
  --allow-text-id axis-dose
```

比较器接受颜色、线条等展示属性的变化，核对节点结构、几何、ID/引用和未授权的文字。允许修改的标签需要指定具体 text/tspan 的稳定 ID。两份 SVG 都先通过结构和字号检查。用新路径保存修改后的版本，并保留原文件哈希。

`revision` 适合验证仅改样式的任务。真正调整版式会改变几何，应使用项目的科学字段/来源基线保持内容一致，再进行实际尺寸的视觉复核。它不根据几何推断统计关系或科学真伪。

## 4. 自定义 Seaborn 图的共同出口

可复用配方位于技能内 `scripts/ff_seaborn.py`，仓库的 `examples/custom_seaborn.py` 提供演示入口：

| 配方 | 作用 | 共享的导出行为 |
|---|---|---|
| `facet` / FacetGrid | 分条件比较，固定方法颜色和点形 | 固定物理画布、完整轴/图例标签 |
| `pair` / PairGrid | 多变量两两关系与分布 | 共同分箱、真实点、原生文字 |
| `joint` / JointGrid | 主关系配合边际分布 | 散点与直方图分别保留图元 |
| `cluster` / clustermap | 显式标准化的聚类热图 | 保存变换、距离/连接方法和行顺序，网格及色条为矢量 |

执行 `python <skill-dir>/scripts/ff_seaborn.py --synthetic-demo --out figures/seaborn` 可生成标明 Synthetic 的示例；用 `--data experimental.csv` 读取含 unit、method、condition、dose、response、signal 的实验表。替换为真实数据时保留语义字段和缺失值处理记录，再调用共同的 `export_figure`。配方先设定最终物理尺寸、绘制画布，然后提取真正显示的文字；隐藏边际轴和不显示的刻度不会成为伪造的必需标签。

接口依据：[FacetGrid](https://seaborn.pydata.org/generated/seaborn.FacetGrid.html)、[PairGrid](https://seaborn.pydata.org/generated/seaborn.PairGrid.html)、[JointGrid](https://seaborn.pydata.org/generated/seaborn.JointGrid.html)、[clustermap](https://seaborn.pydata.org/generated/seaborn.clustermap.html)。

## 5. 视觉审阅记录

按文件和版本记录具体观察：科学对象与关系、数据/单位/区间、标签与层级、最终尺寸、灰度表现、字体、箭头和包含关系。提出明确修改，例如“将右侧图例移至下方，保留数据范围”，并保留修改前后图。选定版本记录到项目合同中，结构审计记录到导出 manifest 中。

## 6. 显式权重的自定义分析配方

`ff_seaborn.weighted_summary(values, weights, weight_definition=...)` 计算声明权重的均值，报告总权重、输入行数和正权重行数。零权重保留在来源记录中；负权重、非有限权重和零总权重产生明确输入错误。置信区间由研究使用的权重模型决定，在独立分析脚本中给出。此配方的解析测试使用数值 [1, 10, 100] 和权重 [1, 2, 0]，均值为 7。
