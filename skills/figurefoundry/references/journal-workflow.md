# 期刊要求与最终导出

目标是做出数据准确、版面清楚、可继续编辑的图源，并把它转换为目标刊物实际接收的投稿文件。**SVG 主源、投稿文件、预览图是三个不同用途的产物。** 技术审核通过表示所检查的项目满足约定，不表示期刊已接收或整篇论文满足所有政策。

相关入口：[科学完整性](scientific-integrity.md)、[图型选择](chart-selection.md)、[可选后端](optional-backends.md)。来源版本和冲突记录见仓库 docs/SOURCES.md、docs/CONFLICTS.md。

## 1. 先记录确切目标

从任务和现有项目中取得已有信息；只有缺失内容会改变科学含义或最后交付时才询问。没有明确期刊时可以先完成通用矢量稿，把期刊字段标记为待核实，不阻塞基础绘图。

| 字段 | 示例与用途 |
|---|---|
| target | 具体刊名；不能用 SCI、CNS、Nature-family 替代确切目标 |
| article_type | Research article、Review、Letter 等 |
| stage | 初投、修回、接收后生产；要求可能不同 |
| figure_role | 主图、Extended Data、Supplementary、Graphical abstract、TOC |
| final_size | 宽/高 mm，单栏或跨栏，最大高度及图注空间 |
| typography | 字体、最终字号、线宽、面板字母和特殊符号 |
| accepted_formats | 投稿系统实际接收的文件；另外保留 SVG 主源 |
| official_source | 原始 URL、页面标题、核查日期，适用条目 |
| unresolved | 不同官方页面冲突或尚未明确的事项 |

这些字段是人工检查记录的建议结构，不是保证所有字段都已成为 CLI 参数。当前命令和配置结构以 SKILL.md、README 及脚本 --help 为准。

## 2. 怎样查要求和处理冲突

优先看目标期刊当前作者指南与实际阶段的编辑部要求，再看适用的出版社制图指南。记录每个关键数值的出处；不能从相似期刊、论文截图或技能名字推断硬性规则。只有网站标题写着 Nature，仍不足以确定它是否适用于本次图件类型。

截至 **2026-10-20** 的入口核查：

| 官方资料 | 实际影响 |
|---|---|
| [Nature：构建和导出面板](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/) | 主图要求可编辑矢量层，plain SVG 在可接收列表内；该指南列出 89/183 mm 栏宽与 5–7 pt 文字。Extended Data 单列不同格式，不能套用主图规则 |
| [Nature：Formatting guide](https://www.nature.com/nature/for-authors/formatting-guide) | 标准图宽另列 90/180 mm。这个差异需要按确切刊物、阶段和适用指南解决，不能把两者取平均或选更顺眼的一个 |
| [IEEE：File formatting](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/) | 接收列表为 PS/EPS/PDF/PNG/TIFF 等，该页没有列 SVG；建议最终文字约 9–10 pt。继续保留 SVG 主源，另交符合目标要求的文件 |
| [Elsevier：Artwork overview](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-overview) | 通用入口推荐 EPS/PDF/TIFF/JPEG 等。SVG 主源可供编辑，实际上传格式再查目标刊物 Guide for Authors |

上表是有日期的说明，不是自动下载的实时合规数据库。下一次出图，尤其真正提交前，应重新查看目标页面。仓库的风格 preset 是规划默认值；当官方规则还未核实，应标记 provisional/unverified。

## 3. 先定毫米，再排版

以最终印刷宽度设计，先给轴标签、图例、色条和面板字母分配空间，再决定绘图区大小。字体应按最终页面检查，不能在很大的图上设小字体后等比缩小，最后仍声称字号合格。

常用单位换算：

```text
inches = millimetres / 25.4
points = millimetres × 72 / 25.4
effective_font_pt = source_font_pt × final_panel_width / source_panel_width
```

导出使用固定页面范围。Matplotlib 的 figsize 是输入尺寸；bbox_inches="tight" 可能改变实际页面宽高。如果有意裁切，就应重新读取导出文件的 width/height/viewBox 换算毫米，并重新检查字号。[Matplotlib savefig 文档](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)

紧凑布局来自合理的 margins、面板间距和共用图例。拥挤时先删重复标签、移动图例、重排面板或增加高度，避免缩小所有字。不同证据量的面板可以不等大，比较面板则应保持可比较的坐标和色标。

## 4. 字体和对象必须真的能改

严格 SVG 使用普通图元和 text/tspan。默认关闭文字转轮廓和外部 TeX 排版；数学符号要在实际导出后核对。简单的上下标可用可编辑文字组合，复杂公式应记录可能的文本碎片或路径，不能只因公式看起来正确就声称字符可编辑。

Matplotlib 的 svg.fonttype="none" 保留文字，但不自动把字体打包进 SVG；默认 path 保留字形外观却失去文字编辑。交接时记录具体字体名称和实际 fallback，检验希腊字母、负号、中文和上/下标。若期刊要求另一字体，换字体后重新检查排版。[Matplotlib 字体说明](https://matplotlib.org/stable/users/explain/text/fonts.html)

使用合法可用字体；本 Skill 不附带 Arial 等商业字体。字体缺失时选择本环境真正存在的替代字体并记录，不把静默替换当作原字体已安装。PDF 的字体嵌入与 SVG 的文字对象需要分别核验。

## 5. 保存完整交付链

| 产物 | 应包含什么 |
|---|---|
| SVG 主源 | 定量图元、文字、面板组、坐标与图例均保留；无整图截图、外部图片链接或品牌角标 |
| 原始数据与绘图数据 | 输入文件、清洗/聚合/变换记录、用于图中每个量的数据 |
| 绘图代码与配置 | 明确数据列、单位、种子、样式、图宽和导出设置；可重建 |
| 审核/来源记录 | 输入与输出 hash、软件版本、运行命令、数值检查、SVG 检查及实际查看记录 |
| 投稿文件 | 根据目标要求另存 PDF/EPS/TIFF 等；只有实际执行并检查的转换才报告完成 |
| 预览图与图注 | 便于审阅的 PNG/PDF；图注定义 n、中心、误差、条件及面板。预览不替代 SVG |

如果投稿格式需要 TIFF，先确定具体图件类别、最终物理尺寸、分辨率、颜色模式和透明度要求，再渲染。DPI 是位图采样密度；修改元数据或把位图包装进 SVG，不会产生可编辑曲线。纯矢量图元不靠“600 dpi”来证明清晰度。

真实显微图、照片和测量图像本身是像素数据，不能通过自动描摹变成仍忠实于实验的逐对象矢量图。严格全矢量任务可将其量化结果或明确标注的结构示意作为 SVG，原始图像另存为证据。若科学叙述必须包含原始图像，应明确指出这与全图无位图约定不兼容，不能以一个 image 标签冒充完成。

## 6. 交稿前看什么

机械审核检查 XML、文本、嵌入位图、对象引用、尺寸等实际支持的项目。另在最终宽度查看图件：标签有无截断，希腊字母和负号是否正确，色条方向是否一致，灰度下组别能否区分，显著性与样本量是否有可核对来源。放大图检查对象，缩到投稿尺寸检查阅读体验，两者都需要。

报告用准确措辞，例如“SVG 结构和 89 × 65 mm 尺寸检查通过；最终预览已查看；目标期刊规范待核实”。避免“完全合规”“保证可发表”“所有编辑器可编辑”等超出证据范围的结论。
