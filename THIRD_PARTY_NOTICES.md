# Third-party notices / 来源与许可说明

## 本仓库的原创范围

FigureFoundry 的入口说明、规则整合、配置、渲染/组合/审核实现以及测试由本项目独立编写。其许可证见根目录 LICENSE。来源仓库用来比较工作方法和发现需要修正的冲突，**没有把上游 Skill 包、编辑器、图标目录、示例插画或绘图脚本直接纳入本仓库**。完整固定版本与能力去向见 [docs/SOURCES.md](docs/SOURCES.md)。

本文件记录可核对的来源与许可信息，不把本仓库许可证扩展到第三方作品。若后续贡献者引入第三方代码、图标、字体或模板，须记录具体文件、版本、权利人、许可证全文及必要 NOTICE；不能仅凭公开可下载或 GitHub 上可见判断可以复制。

## 评估来源的权利人与许可

核查日期为 2026-10-20；下表对应 SOURCES.md 中固定的 commit，而不是今后默认分支的内容。

| 来源 | 所读许可文件或声明 | 本仓库处理 |
|---|---|---|
| K-Dense-AI/scientific-agent-skills | 根 LICENSE.md：MIT，© 2025 K-Dense Inc.；README 要求另看各 Skill 的 license 字段 | 记录方法与来源。scientific-visualization、venue-templates、scientific-schematics 声明 MIT；matplotlib 指向 Matplotlib 许可；seaborn 声明 BSD-3-Clause。没有假定根 MIT 覆盖所有上游依赖 |
| jing1312/nature-figure-skill | MIT；© 2026 Yuan Yizhe（nature-* 内容），© 2026 jing1312（FigureForge 编辑器、模板与文档） | 引用方法与源入口；未复制 FigureForge 或 Yuan1z0825/nature-skills 内容 |
| xiao-yuling/sci-figure | MIT；© 2026 sci-figure contributors | 独立实现对应方法 |
| Yilin399/science-plotting-skill | MIT；© 2026 G15 | 独立实现表格驱动绘图路径 |
| sai-tv/academic-figures | MIT；© 2026 sai-tv | 独立实现原生 SVG 与语义分组 |
| qhy991/Scientific-Figure-Design | MIT；© 2026 qhy991 and contributors；内置第三方图标保留独立 ISC/MIT 许可与商标限制 | 未复制任何图标、品牌资产或上游 Draw.io 实现 |
| TingxiYu/academic-figure-skill | LICENSE 为 Apache License 2.0；README 末尾标注 © 2025 Academic Figure Skill | 参考图型和审阅方法；未复制生产脚本、模板或文档 |
| PM-Shawn/tikz-scientific-figures | 没有发现整个仓库的明确许可授予；README 仅说明 Method Draw 保留其自身许可 | 只记录 TikZ 工作流的一般技术思路与接口选择；未复制脚本及 Method Draw |
| jasonwujch/scientific-visualization | 固定文件树无 LICENSE/COPYING，API license 为空 | 只记录方法比较；未复制代码、样式或文档 |
| 1111asas/scientific-plotting | 固定文件树无 LICENSE/COPYING，API license 为空 | 只记录方法比较；独立实现来源记录和审核 |
| FFFxueGawaine/sci-paper-plot-skill | 固定文件树无 LICENSE/COPYING，API license 为空 | 未复制交互向导、MSSP 样式、模板或代码 |
| zlsjtj/FigureCraft | 原创部分 MIT，© 2026 Jeff Li (zlsjtj)；vendor/nature-figure 有其独立 LICENSE/NOTICE | 未复制场景代码、案例图或 vendor 文件 |

“未发现明确许可”描述本次固定版本的检查结果，不主张上游永远不能被使用。需要复制时，应先取得适当授权或找到明确适用的许可证；本项目当前路径不依赖复制。

## 软件依赖与可选工具

Matplotlib、NumPy、SciPy、pandas 等通过运行环境的正常软件包安装机制使用；依赖代码没有被复制进本 Skill。Seaborn、R/ggplot2/svglite、Plotly/Kaleido、TikZ/PGFPlots/dvisvgm、Draw.io/Inkscape 是说明中可能出现的可选工具，各自遵循自身许可证和安装要求。列出工具不代表本次安装、运行或认证了该工具。

查阅入口：[Matplotlib license](https://matplotlib.org/stable/project/license.html)、[NumPy license](https://numpy.org/doc/stable/license.html)、[SciPy license](https://github.com/scipy/scipy/blob/main/LICENSE.txt)、[pandas license](https://github.com/pandas-dev/pandas/blob/main/LICENSE)、[Seaborn license](https://github.com/mwaskom/seaborn/blob/master/LICENSE.md)、[svglite](https://svglite.r-lib.org/)、[Plotly.py](https://github.com/plotly/plotly.py)、[PGF/TikZ](https://github.com/pgf-tikz/pgf)、[dvisvgm](https://dvisvgm.de/)。安装发布时应以实际使用的软件版本及随包许可证为准。

## 字体、图件与标识

本项目不打包商业字体、第三方图标库、期刊商标或实验图片。SVG 保留文字对象时，观看和编辑环境需要拥有对应字体；名称出现在配置中不代表已授予字体复制/嵌入权利。

FigureFoundry 不自动在生成图上添加平台标志、品牌水印或 AI 角标。图件仍应保留正确的科学标注，来源、软件版本、数据转换和必要的工具使用说明另行记录。这个输出约定不授权移除他人作品的署名或许可证，也不表示期刊要求的使用披露可以省略。

Nature、Science、Cell、IEEE、Elsevier 等名称仅用于描述目标刊物或查找官方投稿规则，不代表这些机构推荐、审核或认可本项目。
