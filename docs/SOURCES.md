# 来源、固定版本与整合范围

核查日期：**2026-10-20（UTC）**。本次比较覆盖 **16 个相关 Skill 条目，分布于 12 个公开仓库**。这里的“整合”指统一可用的工作方法、独立实现必要功能、为专业后端保留清晰入口；不表示打包了这些仓库的全部文件，也不表示每个上游工作流都已在本环境运行。

FigureFoundry 的代码、配置与说明独立编写。未复制上游编辑器、模板集合、插图、图标库或成段实现。许可不明的候选仅记录一般方法与评估结论。运行依赖沿用各自许可，详见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 1. 固定版本

以下 SHA 来自各仓库默认分支的 **commit** 接口，不是单个文件的 blob SHA。所有后续路径均按此版本阅读；未来重新比较时应更新 SHA、核查日期和冲突记录。

| 仓库 / 来源编号 | 默认分支 | 核查提交 | 许可证据 |
|---|---|---|---|
| K-Dense-AI/scientific-agent-skills · S01–S05 | main | [`593377bb048752abb0152deab9fbb1083a6087df`](https://github.com/K-Dense-AI/scientific-agent-skills/commit/593377bb048752abb0152deab9fbb1083a6087df) | [根 LICENSE.md](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/LICENSE.md)：MIT；单个 Skill 的 license 字段还需分别看 |
| jing1312/nature-figure-skill · S06 | main | [`af778027c866e2e6b3432b946e44a4a2b4434d82`](https://github.com/jing1312/nature-figure-skill/commit/af778027c866e2e6b3432b946e44a4a2b4434d82) | [LICENSE](https://github.com/jing1312/nature-figure-skill/blob/af778027c866e2e6b3432b946e44a4a2b4434d82/LICENSE)：MIT，分别保留 Yuan Yizhe 与 jing1312 署名 |
| xiao-yuling/sci-figure · S07 | main | [`a44fbcae2de59cfdefb016a0eab86e66e0ba8555`](https://github.com/xiao-yuling/sci-figure/commit/a44fbcae2de59cfdefb016a0eab86e66e0ba8555) | [LICENSE](https://github.com/xiao-yuling/sci-figure/blob/a44fbcae2de59cfdefb016a0eab86e66e0ba8555/LICENSE)：MIT |
| Yilin399/science-plotting-skill · S08 | main | [`9f9234aef7c117e0d079a1b07f84b29cf086e4ba`](https://github.com/Yilin399/science-plotting-skill/commit/9f9234aef7c117e0d079a1b07f84b29cf086e4ba) | [LICENSE](https://github.com/Yilin399/science-plotting-skill/blob/9f9234aef7c117e0d079a1b07f84b29cf086e4ba/LICENSE)：MIT，© G15 |
| sai-tv/academic-figures · S09 | master | [`2a2159053f48156c3ad521d8dfcc7e4c22b33e43`](https://github.com/sai-tv/academic-figures/commit/2a2159053f48156c3ad521d8dfcc7e4c22b33e43) | [LICENSE](https://github.com/sai-tv/academic-figures/blob/2a2159053f48156c3ad521d8dfcc7e4c22b33e43/LICENSE)：MIT |
| qhy991/Scientific-Figure-Design · S10 | main | [`d88f87dad2952af3ee450873c67e95be5ae44e71`](https://github.com/qhy991/Scientific-Figure-Design/commit/d88f87dad2952af3ee450873c67e95be5ae44e71) | [LICENSE](https://github.com/qhy991/Scientific-Figure-Design/blob/d88f87dad2952af3ee450873c67e95be5ae44e71/LICENSE)：原创内容 MIT；图标另有 ISC/MIT 条款。API 的 NOASSERTION 不能替代阅读正文 |
| TingxiYu/academic-figure-skill · S11 | main | [`1df9940dd01ac939f072b12fe28d6353b79b90f9`](https://github.com/TingxiYu/academic-figure-skill/commit/1df9940dd01ac939f072b12fe28d6353b79b90f9) | [LICENSE](https://github.com/TingxiYu/academic-figure-skill/blob/1df9940dd01ac939f072b12fe28d6353b79b90f9/LICENSE)：Apache-2.0；README 目录注释中的 MIT 与该文件不一致 |
| PM-Shawn/tikz-scientific-figures · S12 | main | [`0f0918c84db0b715bed476b1f607cd6e72cd35d4`](https://github.com/PM-Shawn/tikz-scientific-figures/commit/0f0918c84db0b715bed476b1f607cd6e72cd35d4) | 根目录未发现许可文件；[README License 段](https://github.com/PM-Shawn/tikz-scientific-figures/blob/0f0918c84db0b715bed476b1f607cd6e72cd35d4/README.md)只指向内置 Method Draw 的独立许可 |
| jasonwujch/scientific-visualization · S13 | master | [`1470ec5f77198e59d3d22d026ff2ff33275aabc2`](https://github.com/jasonwujch/scientific-visualization/commit/1470ec5f77198e59d3d22d026ff2ff33275aabc2) | 固定提交的完整文件树未发现 LICENSE/COPYING；API license 为空；仅作方法比较 |
| 1111asas/scientific-plotting · S14 | main | [`d5dbf14c488f080c27e63c6ed4dce24cd9614442`](https://github.com/1111asas/scientific-plotting/commit/d5dbf14c488f080c27e63c6ed4dce24cd9614442) | 固定提交的完整文件树未发现 LICENSE/COPYING；API license 为空；仅作方法比较 |
| FFFxueGawaine/sci-paper-plot-skill · S15 | main | [`3404a006ed79695a20f6b31656b209b99a161f32`](https://github.com/FFFxueGawaine/sci-paper-plot-skill/commit/3404a006ed79695a20f6b31656b209b99a161f32) | 固定提交的完整文件树未发现 LICENSE/COPYING；API license 为空；仅作方法比较 |
| zlsjtj/FigureCraft · S16 | main | [`2c360b012bd5d12e8ba7933153ab804ccec1c183`](https://github.com/zlsjtj/FigureCraft/commit/2c360b012bd5d12e8ba7933153ab804ccec1c183) | [LICENSE](https://github.com/zlsjtj/FigureCraft/blob/2c360b012bd5d12e8ba7933153ab804ccec1c183/LICENSE)：原创部分 MIT；vendor/nature-figure 保留独立 LICENSE/NOTICE |

## 2. 能力怎样进入 FigureFoundry

状态用语：**保留方法**表示进入本 Skill 的工作流或说明；**独立实现**表示本仓库自行编写对应模块；**可选路由**表示提供专业后端指引，不等于内置执行能力；**排除**表示与本项目目标冲突或没有适当复制许可。

| ID | 已阅读的 Skill 入口 | 保留与整合 | 取舍 |
|---|---|---|---|
| S01 | [K-Dense scientific-visualization](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-visualization/SKILL.md) | 保留数据来源、误差定义、缺失值、语义配色、版面审核与逐次导出记录；独立实现 SVG 主文件和审核管线 | 其导出器已能保留 SVG 文本与固定页面尺寸，但默认格式是 PDF/PNG；本项目显式要求 SVG。期刊配置仅作有日期的规划输入 |
| S02 | [K-Dense matplotlib](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/matplotlib/SKILL.md) | 保留面向对象绘图、坐标/图例/误差棒控制、GridSpec 组合、数据与布局分离 | 通用性能建议中的 rasterized=True 不进入纯矢量交付；Skill 元数据指向 Matplotlib 自身许可 |
| S03 | [K-Dense seaborn](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/seaborn/SKILL.md) | 保留长表、分组/分面、分布与统计图选择、独立采样单位和自动估计注意事项 | Seaborn 作为可选前端；自动 bootstrap 不能代替实验设计。元数据声明 BSD-3-Clause |
| S04 | [K-Dense venue-templates](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/venue-templates/SKILL.md) | 保留期刊/年份/文章类型/投稿阶段定位、官方来源与核查日期、模板适用范围记录 | 不复制与绘图无关的论文、海报、基金模板；没有把通用 scaffold 当作官方模板 |
| S05 | [K-Dense scientific-schematics](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-schematics/SKILL.md) | 保留关系先行、结构草图、层次、箭头、科学内容核对及视觉复核方法；用原生 SVG 几何独立实现简明示意图 | 固定版本明确只产出 PNG；排除其图像生成 API 和位图作为最终 SVG 图源的做法，不继承付费服务依赖 |
| S06 | [jing1312 nature-figure](https://github.com/jing1312/nature-figure-skill/blob/af778027c866e2e6b3432b946e44a4a2b4434d82/skills/nature-figure/SKILL.md) | 保留 Figure Contract、证据分工、整篇语义配色、独立图件、统计与 ML 复现记录；R 进入可选路由 | 不复制 FigureForge 编辑器或图谱；默认 Python，无需为后端选择阻塞常规任务；热图和紧边界导出改由本项目契约控制 |
| S07 | [xiao-yuling sci-figure](https://github.com/xiao-yuling/sci-figure/blob/a44fbcae2de59cfdefb016a0eab86e66e0ba8555/skill.md) | 保留中英科研工作流、Python/R 思路、单栏物理尺寸、图源/图注/预览联动 | 四边框、Arial 是风格选项；不宣称 SCI 通用规则。原入口为小写 skill.md，本项目使用标准 SKILL.md |
| S08 | [Yilin399 science-plotting](https://github.com/Yilin399/science-plotting-skill/blob/9f9234aef7c117e0d079a1b07f84b29cf086e4ba/skills/science-plotting/SKILL.md) | 保留表格驱动的趋势、散点、柱状、分布图，原始点及明确 SD/SEM；独立实现精简可复现路径 | Science-like 为审美描述；不等同 Science 投稿认证。拟合、缺失处理与误差须依据数据声明，不能只采用视觉默认值 |
| S09 | [sai-tv academic-figures](https://github.com/sai-tv/academic-figures/blob/2a2159053f48156c3ad521d8dfcc7e4c22b33e43/SKILL.md) | 保留 SVG 原生图元、可编辑文字、语义分组、布局变体、图形摘要的信息组织 | 上游数据区域明确是占位区；本项目只将真实绘图 SVG 接入正式组合图，布局示例继续标注示例 |
| S10 | [qhy991 Scientific-Figure-Design](https://github.com/qhy991/Scientific-Figure-Design/blob/d88f87dad2952af3ee450873c67e95be5ae44e71/SKILL.md) | 保留单一科研问题、实体/关系/边界、语义色、反馈环路的状态和更新逻辑；Draw.io 为可选来源 | 不复制图标目录；原生 SVG 独立实现基础几何，避免把 SVG 图标包进 image 元素。复杂 Draw.io 编辑器工作流未内置 |
| S11 | [TingxiYu academic-figure-skill](https://github.com/TingxiYu/academic-figure-skill/blob/1df9940dd01ac939f072b12fe28d6353b79b90f9/SKILL.md) | 保留科学问题驱动的图型选择、多阶段 QA、统计报告、ML 基线/种子/分割说明 | 排除 PNG 面板拼装和按显著性/效应大小拒绝绘制的门槛；保留零效应、低相关、阴性结果。专业图谱进入知识路由，未复制其生产脚本 |
| S12 | [PM-Shawn tikz-scientific-figures](https://github.com/PM-Shawn/tikz-scientific-figures/blob/0f0918c84db0b715bed476b1f607cd6e72cd35d4/SKILL.md) | 保留 .tex + 数据可重建、数学/电路/几何专业路由及源文件修改方法 | 当前导出脚本使用 --no-fonts，文字成为轮廓，不能通过本项目严格文字编辑契约；不复制脚本或内置 Method Draw |
| S13 | [jasonwujch scientific-visualization](https://github.com/jasonwujch/scientific-visualization/blob/1470ec5f77198e59d3d22d026ff2ff33275aabc2/SKILL.md) | 比较多套审美 preset、灰度冗余编码与期刊尺寸规划；采用一般方法自行设计风格 | 无明确复制许可；不复制 preset/exporter。排除只检查宽高就标注 COMPLIANT 的判断 |
| S14 | [1111asas scientific-plotting](https://github.com/1111asas/scientific-plotting/blob/d5dbf14c488f080c27e63c6ed4dce24cd9614442/scientific-plotting/SKILL.md) | 保留“数据—脚本—图件—说明”及来源表的想法；独立实现 XML 内容审核 | 无明确复制许可；不复制模板。其按扩展名识别 vector candidate 的检查不足以证明 SVG 可编辑 |
| S15 | [FFFxueGawaine sci-paper-plot-skill](https://github.com/FFFxueGawaine/sci-paper-plot-skill/blob/3404a006ed79695a20f6b31656b209b99a161f32/SKILL.md) | 保留中英文调图术语、轴/图例/线型/布局分项修改、工程与动态系统图型入口 | 无明确复制许可；不复制交互向导、MSSP 风格文件或脚本；PNG 默认导出和需要反复确认的向导不进入主流程 |
| S16 | [zlsjtj FigureCraft](https://github.com/zlsjtj/FigureCraft/blob/2c360b012bd5d12e8ba7933153ab804ccec1c183/SKILL.md) | 保留科学对象和关系约束、语义配色、整体/局部对应、技术/科学/视觉分项审阅、修改范围和哈希记录 | 不复制场景引擎、案例或 vendor 内容；曲面位图加矢量标签的混合例图不作为纯 SVG 模板 |

S16 的实际入口文件为 [SKILL.md](https://github.com/zlsjtj/FigureCraft/blob/2c360b012bd5d12e8ba7933153ab804ccec1c183/SKILL.md)，内部名称为 scientific-figure-studio。仓库名、Skill 名和程序能力分别记录，避免以后扩展时混淆。

## 3. 冲突判断所读的实现证据

这是源码核查记录，不是声称已执行全部上游仓库。候选行为的本地对照测试与本项目回归证据另见 [CONFLICTS.md](CONFLICTS.md)。

| 证据文件 | 可核对的事实 | 本项目对应决策 |
|---|---|---|
| [K-Dense figure_export.py](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-visualization/scripts/figure_export.py) | truetype 模式设 svg.fonttype=none；默认 bbox_inches=None；默认格式 pdf/png；明确区分矢量容器与内部位图 | 文本节点、固定尺寸、显式 SVG；导出后仍检查内容 |
| [nature-figure qa-contract.md](https://github.com/jing1312/nature-figure-skill/blob/af778027c866e2e6b3432b946e44a4a2b4434d82/skills/nature-figure/references/qa-contract.md) 与 [api.md](https://github.com/jing1312/nature-figure-skill/blob/af778027c866e2e6b3432b946e44a4a2b4434d82/skills/nature-figure/references/api.md) | QA 示例有 tight bbox；heatmap helper 用 imshow；finalize helper 本身可以接受不裁切的边界 | 按实际调用比较，不能把整套上游一概说成“只会位图/只会裁切” |
| [sci-figure heatmap_example.py](https://github.com/xiao-yuling/sci-figure/blob/a44fbcae2de59cfdefb016a0eab86e66e0ba8555/examples/python/heatmap_example.py) | imshow 绘制热图，图库调用输出 PNG | 独立实现矢量网格和可编辑色条 |
| [science-plotting plot_science_stat.py](https://github.com/Yilin399/science-plotting-skill/blob/9f9234aef7c117e0d079a1b07f84b29cf086e4ba/skills/science-plotting/scripts/plot_science_stat.py) | SVG 字体设 none；有 SD/SEM 与表格读取逻辑；样本不足时返回零误差 | 保留明确统计类型；本项目将不足以估计的不确定性记为不可估计，而非确定为零 |
| [academic-figure-skill Step 5 / Step 5.5](https://github.com/TingxiYu/academic-figure-skill/blob/1df9940dd01ac939f072b12fe28d6353b79b90f9/SKILL.md) | 要求 PNG 载入组合，并对每个数据面板施加显著数、AUC 分离、相关/方差/组间差等阈值 | 排除这两条路径；数值合法性与“结果是否显著”分开 |
| [TikZ export_svg.sh](https://github.com/PM-Shawn/tikz-scientific-figures/blob/0f0918c84db0b715bed476b1f607cd6e72cd35d4/scripts/export_svg.sh) | dvisvgm 调用带 --no-fonts | 可编辑 .tex 与可编辑 SVG 文字是不同能力，分别交付和报告 |
| [jasonwujch figure_export.py](https://github.com/jasonwujch/scientific-visualization/blob/1470ec5f77198e59d3d22d026ff2ff33275aabc2/scripts/figure_export.py) | 默认 tight；对矢量格式把 DPI 限到 300；尺寸检测的 compliant 只取宽高 | 不采用；严格 SVG 主要查对象与文字，不用 DPI 或尺寸替代全部验收 |
| [1111asas audit_figure.py](https://github.com/1111asas/scientific-plotting/blob/d5dbf14c488f080c27e63c6ed4dce24cd9614442/scientific-plotting/scripts/audit_figure.py) 与 [plot_template.py](https://github.com/1111asas/scientific-plotting/blob/d5dbf14c488f080c27e63c6ed4dce24cd9614442/scientific-plotting/scripts/plot_template.py) | 审核把 pdf/svg/eps 后缀记为 vector candidate；模板默认 PNG/PDF | 必须解析 SVG，拒绝伪装成 SVG 的整图截图 |
| [FFFxueGawaine scimplstyle_mssp.py](https://github.com/FFFxueGawaine/sci-paper-plot-skill/blob/3404a006ed79695a20f6b31656b209b99a161f32/scripts/scimplstyle_mssp.py) 与 [mssp.mplstyle](https://github.com/FFFxueGawaine/sci-paper-plot-skill/blob/3404a006ed79695a20f6b31656b209b99a161f32/mplstyles/mssp.mplstyle) | 默认 PNG；tight bbox；这些文件没有 svg.fonttype 设置 | 不采用导出实现，自行设计明确的 SVG 输出契约 |
| [FigureCraft README](https://github.com/zlsjtj/FigureCraft/blob/2c360b012bd5d12e8ba7933153ab804ccec1c183/README.md) 与 [quality-and-acceptance.md](https://github.com/zlsjtj/FigureCraft/blob/2c360b012bd5d12e8ba7933153ab804ccec1c183/references/quality-and-acceptance.md) | 曲面示例明确披露混合位图；审阅区分自动项和人工项 | 继承审阅边界的思路，排除混合位图最终图件 |

## 4. 权威资料优先于二手风格名称

以下资料在核查日阅读。真正投稿时重新查看目标期刊的官方要求；固定的研究记录不代表未来页面不会变化。

| 资料 | 用于哪些判断 |
|---|---|
| [Nature figure panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/) 与 [Nature formatting guide](https://www.nature.com/nature/for-authors/formatting-guide) | 文字可编辑、主图 plain SVG、最终尺寸；两份指南分别列 89/183 mm 和 90/180 mm，必须记录适用页面/阶段，不能默默混用 |
| [IEEE graphics file formatting](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/file-formatting/) | 投稿格式、字体嵌入与字号；SVG 不在该页接收列表中，因此保留 SVG 主源并按要求另导出 |
| [Elsevier artwork overview](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-overview) | 出版社通用图件格式和字体入口；具体期刊 Guide for Authors 仍须核实 |
| [Matplotlib SVG fonts](https://matplotlib.org/stable/users/explain/text/fonts.html) | path 与 none 的编辑/字体可用性取舍 |
| [Matplotlib rasterization](https://matplotlib.org/stable/gallery/misc/rasterization_demo.html) 与 [pcolormesh](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.pcolormesh.html) | SVG/PDF 内可含位图；矩阵网格可用原生集合表示 |
| [Seaborn error bars](https://seaborn.pydata.org/tutorial/error_bars.html) | 数据离散程度与估计不确定性的区别 |
| [Plotly static export](https://plotly.com/python/static-image-export/) | WebGL 图层的位图导出限制 |
| [svglite](https://svglite.r-lib.org/) 与 [dvisvgm manual](https://dvisvgm.de/Manpage/) | R 的 SVG 文本设备与 TikZ 导出取舍 |

## 5. 下次加入来源时

新增 S17 等稳定编号，补齐仓库、确切入口、commit SHA、许可正文、读取日期和能力去向。每项冲突都添加可重现输入、比较标准、实际运行环境与输出。没有运行的后端写“可选指导 / 未在本次验证”，不借用上游 README 的 PASS 作为本仓库测试结果。修改代码后再更新 README 能力表和测试报告；保留旧决定被替换的理由。
