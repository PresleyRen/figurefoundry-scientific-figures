# 可选后端、编辑器与能力边界

主流程是 Python 数值绘图与原生 SVG 示意/组合。已有研究项目使用 R、LaTeX 或其他工具时，可以沿用其分析输出；本文件保留专业路线，**不把指导性示例写成已安装、已运行或已验证的能力**。

本次发布对 R/svglite、TikZ/dvisvgm、Plotly/Kaleido、Draw.io 的完整外部工作流没有执行验收。Inkscape 命令行渲染原生 SVG，以及修改 SVG 节点后的重渲染已用于验证；未验证其全部 GUI 编辑功能。若后续执行新后端，应把真实版本、命令、图件和审核结果写进测试报告，再升级能力状态。当前范围以仓库 README 与 docs/TEST_REPORT.md 为准。

## 1. 快速路由

| 工具/路径 | 适用情况 | 进入严格 SVG 流程前的条件 |
|---|---|---|
| Matplotlib 主流程 | 16 类内置数据图、可控排版、常规科学图件 | 使用统一导出器和审核；实际测试范围见报告 |
| 原生 SVG | 流程、机制简图、多面板组合 | 图元/文字存在、对象引用正确、物理尺寸和面板缩放可核对 |
| Seaborn | 长表统计图、分组/分面、分布原型 | 明确估计与误差；导出后检查无图像节点、可编辑标签和尺寸。未包含任意 Seaborn 图型的自动适配器 |
| R/ggplot2/svglite | 既有 R 分析、专业组学和统计生态 | 显式选择 SVG 文本设备；关闭 raster 层，色条/复杂热图也检查；保留 .R 和数据 |
| Plotly/Kaleido | 探索性交互、需要 HTML 的另一路输出 | 静态稿用 SVG 可导出的图层，避免 WebGL 位图；静态标签不能依赖 hover |
| TikZ/PGFPlots | 数学排版、几何、电路、LaTeX 源码 | .tex 可重建与 SVG 字符可编辑分别检查；默认轮廓导出不满足严格字符编辑 |
| Draw.io | 复杂节点/连接器人工编辑与已有 .drawio 源 | 导出普通 SVG；排除 foreignObject、嵌入 image、外链；必要时独立重建原生图元 |
| Inkscape/Illustrator | 编辑已有矢量源、交稿微调与另存格式 | 保留主源、记录编辑内容，重新审核文本/大小/图元，避免展平/文字转曲 |

运行环境可以先检查：

```bash
python <skill-dir>/scripts/figurefoundry.py doctor
```

doctor 报告它实际检测到的项目，不等于已经对所有可选工具完成端到端测试。

## 2. R：保留文字的 SVG 路线

[svglite](https://svglite.r-lib.org/) 是 R 的 SVG 设备，设计用于较易编辑的文字和图元。它不会使使用 rasterGrob、raster=TRUE 或类似位图层的图自动变成全矢量。ggplot2/复杂热图输出中，图例、色条和插图也应一起检查。

以下只是未在本次运行的最小指导示例；需要用户项目中真实存在 source.csv 的 x/y 列：

```r
library(ggplot2)
library(svglite)

d <- read.csv("source.csv")
p <- ggplot(d, aes(x = x, y = y)) +
  geom_point(size = 1.2) +
  theme_classic(base_size = 7)

svglite("figure.svg", width = 89 / 25.4, height = 65 / 25.4)
print(p)
dev.off()
```

导出后使用同一审核命令：

```bash
python <skill-dir>/scripts/figurefoundry.py audit figure.svg --min-font-pt 6
```

简单 XML 审核不替代 R 统计正确性、字体可用性或版面复核。复杂专业图若需额外适配器，先保留 .R、输入表和导出设置，不能仅拿 PNG 面板交给组合器。

## 3. Plotly：交互稿与静态稿分别做

Plotly 的部分 WebGL 图层在 SVG/PDF 导出中包含位图。例如 scattergl、scatter3d、surface 等不能因文件后缀是 SVG 就认定满足纯矢量要求。二维散点可显式用非 WebGL 图层；实际输出仍需审核。[Plotly 静态导出官方说明](https://plotly.com/python/static-image-export/)

交互稿保留 hover、缩放和筛选，另交 HTML；静态稿必须拥有完整轴标签、单位、图例和说明。不能把 hover 里的样本量当作静态图已经标明，也不能将浏览器截图包装成 SVG。Kaleido 和浏览器运行依赖应以本机实际安装及当前文档为准，本发布没有执行此路径。

## 4. TikZ：源码编辑和字符编辑分别报告

TikZ/PGFPlots 对数学、几何和专业符号很有价值，保留 .tex 和数据可重建。审计来源中的 export_svg.sh 使用 dvisvgm --pdf --no-fonts；该选项把文字转换为轮廓。其 SVG 仍可缩放和编辑路径，但不能满足用户想直接改文字的要求。[dvisvgm 手册](https://dvisvgm.de/Manpage/)

不能简单删除 --no-fonts 就宣称所有编辑器可用：不同字体表示和渲染器仍有兼容性差异。完整流程应编译一个含实际公式、希腊字母和文字的代表样例，检查导出结果的文字节点，并在目标编辑环境查看；必要时以可编辑 text/tspan 重建标签。没有做到时，明确交付“可编辑 .tex + 矢量 PDF/路径 SVG”，并注明不符合严格文字 SVG 主源约定。

## 5. Draw.io 与图标

有些 SVG 将图标作为 image 元素嵌入，即使 image 内容本身是 SVG，用户也无法像普通子图元一样直接逐对象修改。Draw.io 的富文本还可能通过 foreignObject 表示。严格模式把这类表示视为需要重建/转换的输入，不悄悄放宽审核。

自绘简单原生几何通常足以表达科学对象。需要第三方图标时先核对来源与许可，并保留署名要求；不得通过删标志或删除许可文本来满足“无水印”。本项目未带入上游的图标库或编辑器。

## 6. 自定义后端的接入合同

后端至少提供原始/绘图数据、重建源、准确版本、输出 SVG 和解释性图注。SVG 不含整图或局部位图、外部资源与脚本；文字可核对；根尺寸可转换为毫米；面板组合后仍可编辑。XML/引用审核与实际视觉复核都通过后，才可列入已验证能力。

失败时保留审核证据并修正生成源，避免对成图盲目删除所有 image 或 path：这会直接删掉实验内容。未安装的后端报告未运行，安装成功后仍要执行代表性输出和反例测试。公共审核器是共同出口，不能由每个后端自己把自己的结果宣布为通过。
