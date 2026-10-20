# FigureFoundry v1.1.0 验证报告

验证日期：**2026-10-20（UTC）**。本轮保存的自动回归记录为 **190 项 unittest 测试方法通过，0 失败、0 错误、0 跳过**，耗时 **50.929 秒**，完成时间 **08:16:10 UTC**。完整用例、运行时间及环境见 [test-results.json](test-results.json)。

本报告对应 v1.1.0 的代码、来源覆盖和图集工作流。此前 v1.0.0 的 96 项方法及两项独立试用保存在 [v1.0.0 历史报告](https://github.com/PresleyRen/figurefoundry-scientific-figures/blob/v1.0.0/docs/TEST_REPORT.md)，历史计数不与本轮相加。

## 1. 自动回归与模块覆盖

方法数取自本轮结果中的实际成功用例名称。16 种原生图、5 类样式、5 种颜色归一化和 4 类 Seaborn 图在方法内使用 subtests，计入所在方法。

| 测试模块 | 方法数 | 实际验证内容 |
|---|---:|---|
| [test_cli_and_data.py](../tests/test_cli_and_data.py) | 24 | CSV/TSV/JSON/JSONL/XLSX、重复表头、缺失值与哈希；CLI 输入/退出码；能力定位；期刊记录和对数轴输入 |
| [test_conflicts.py](../tests/test_conflicts.py) | 8 | live text/转曲、原生网格/位图热图、独立色条、tight bbox、已有 usetex、完整标签及 DPI 的实际导出对照 |
| [test_coverage_navigation.py](../tests/test_coverage_navigation.py) | 6 | 逐特点入口、实现/说明/测试的空目标和扩展指针、稳定 ID、来源筛选和中英专业检索 |
| [test_diagram_cli_contract.py](../tests/test_diagram_cli_contract.py) | 3 | 默认节点标签、spec/CLI 字号优先级、最小字号传播及无效输入 |
| [test_diagrams.py](../tests/test_diagrams.py) | 12 | 五类节点、反馈与路径、中英文/长标签、SVG 拼版、引用隔离、比例与最终字号 |
| [test_final_contracts.py](../tests/test_final_contracts.py) | 2 | 对数轴限值、多行/单元格/面板/色条的完整标签清单 |
| [test_plot_engine.py](../tests/test_plot_engine.py) | 22 | 独立单位、SD/SEM/tCI/Bootstrap、缺失断口、ROC/PR 并列分数、Pareto、16 图型真实 SVG 导出和阴性结果 |
| [test_plot_feature_coverage.py](../tests/test_plot_feature_coverage.py) | 30 | 宽表、独立点叠加、OLS/密度拟合、共享语义样式、5 种 norm、5 类主题、跨行跨列版式和可见文字清单 |
| [test_reaudit_conflicts.py](../tests/test_reaudit_conflicts.py) | 8 | 转曲源图被面板字母掩盖、跨面板借标签、拼版后字号、真实数据/机制组合及原值保留 |
| [test_reference_intake.py](../tests/test_reference_intake.py) | 17 | 本地 HTML 图/子图/上下文、相对 URL、alt 状态、脚本忽略；benchmark 来源、方法、单位、变换与不确定性 |
| [test_seaborn_recipes.py](../tests/test_seaborn_recipes.py) | 6 | 四类 grid 真实导出、色条/标题布局、密度显示、聚类成员/标准化记录、明确缺失决策及加权均值 |
| [test_spatial_choice.py](../tests/test_spatial_choice.py) | 2 | 同值 2D/3D 导出及可编辑标签，公共二维比例与透视投影比例的真实比较 |
| [test_style_inventory.py](../tests/test_style_inventory.py) | 6 | 项目默认值优先级/身份/哈希、跨图一致性；Python/Notebook 行号和单元定位，不执行输入源码 |
| [test_svg_audit.py](../tests/test_svg_audit.py) | 25 | XML、真实文字/几何、栅格、主动内容、外链、ID/引用/循环、有限几何、缩放字号和隐藏文字 |
| [test_workflow_features.py](../tests/test_workflow_features.py) | 19 | 配色数值、alt/title/desc、指定文字精修、实体/数量、项目快照、候选选源和冻结源继承 |
| **合计** | **190** | **0 失败、0 错误、0 跳过** |

复现入口：

```bash
python tools/run_checks.py --report docs/test-results.json
python tools/check_package.py
python examples/generate_examples.py
python examples/custom_seaborn.py --out build/seaborn-check
```

包索引包含 **16 个来源、103 个特点、41 个能力和 26 条专业路线**。导航测试逐项核对特点的实现、参考文件、互补来源、测试与扩展目标，并验证缺失指针能准确定位到具体特点。

## 2. 数值答案和冲突取舍

### 2.1 可独立核算的数值

| 案例 | 实算答案与检查效果 | 证据 |
|---|---|---|
| 独立样本 `[1,3,5]` | 均值 3，样本 SD 2，SEM `2/√3`；95% CI 使用 `t(.975,df=2)=4.302652729…` | [统计用例](../tests/test_plot_engine.py) |
| 不均衡技术重复 | 按独立运行归约后的组均值为 4、3；直接按测量行平均会得到 3.2、2.2。正确 n=3、SD=2、SEM≈1.154701 | [重审观测记录](evidence/reaudit/conflict-review.json) |
| OLS：x=`[0,1,2,3]`，y=`[1,2,2,5]` | 斜率 1.2、截距 0.7、SSE=1.8、SST=9、R²=0.8；图内方程与原始坐标拟合一致 | [拟合用例](../tests/test_plot_feature_coverage.py) |
| 正态/对数正态密度 | `[-1,0,1]` 的正态 MLE 为 μ=0、σ=`√(2/3)`；`[e⁻¹,1,e]` 的对数正态 log-mean=0、shape=`√(2/3)`、loc=0。密度曲线与解析式逐点比较 | [密度用例](../tests/test_plot_feature_coverage.py) |
| 显式权重 `[1,2,0]` 作用于 `[1,10,100]` | 加权均值 7；总权重与零权重行单独记录 | [权重用例](../tests/test_seaborn_recipes.py) |
| 阴性与反向结果 | 零斜率、零相关、AUC=AP=0.5、火山图 0/3 显著、森林图效应 −2/−1 均按原值成图；反向分类器 AUC=0 仍可绘制 | [重审记录](evidence/reaudit/conflict-review.json)、[ROC/PR 用例](../tests/test_plot_engine.py) |
| 缺失点及矩阵 | 5 行折线保留 4 个观测与 1 个缺失，实际 SVG 为两段路径；矩阵保留 0、−2、3 与空缺单元 | [重审观测记录](evidence/reaudit/conflict-review.json) |
| 灰度与对比度 | 黑/白相对亮度为 0/1，文字对比度 21，CIE L* 为 0/100，ΔL=100 | [配色实测](evidence/reaudit/conflict-review.json) |

五种 norm 另外测试了已知输入值的映射和跨图同值同色。宽表只使用明确选择的 `y_columns`；不把主体 ID 或其他数字列自动变成测量曲线。

### 2.2 原 CF-01–CF-16 的重审

原始规则与来源见 [CONFLICTS.md](CONFLICTS.md)。实际重现、修复前后结果及成图观察见 [conflict-review.json](evidence/reaudit/conflict-review.json)；CF-06 后续完成的专门对照见 [spatial-choice/review.json](evidence/reaudit/spatial-choice/review.json)。

| 冲突 | 本版采用的行为 | 本次证据 |
|---|---|---|
| CF-01 文字转曲 | 每个源面板先检查 live text 和完整标签，再拼版 | 转曲源不再因新增一个 `a` 而通过；另一面板的文字也不能补齐本面板缺失标签 |
| CF-02 热图/色条栅格化 | 原生 mesh 与矢量色条 | imshow 和独立栅格色条反例；含 0/负值/缺失单元的真实组合图 |
| CF-03 tight 导出与最终尺寸 | 固定毫米画布，在最终位置检查字号 | tight 对照；183×75 mm 拼版；放大后约 11.339 pt 可用，缩小至约 2.835 pt 时按 6 pt 阈值拒绝 |
| CF-04 静态期刊预设 | 保存候选要求、投稿阶段和明确的冲突处理 | 89/183 与 90/180 mm 候选均保留，未解决冲突时失败；本地检查覆盖记录字段 |
| CF-05 边框风格 | 保留可选风格，按具体图选择 | 同数据、坐标、标签和 SEM 的简洁轴/全框轴实际 A/B；两版数值不变，已看 Inkscape 预览 |
| CF-06 装饰性 3D | 单响应组间比较采用共同二维比例；真实空间问题保留专业三维路线 | 同数据 2D/3D 实际 SVG/PNG 对照、投影测量及人工预览，详见下一节 |
| CF-07 占位面板 | 定量面板关联真实输入文件和统计摘要 | CSV SHA→统计→SVG SHA→拼版源 SHA；机制图与定量区域的目的分别记录 |
| CF-08 显著性门槛 | 合法阴性、零效应及负效应正常绘制 | 零斜率/相关、AUC=AP=0.5、全非显著火山图和负效应森林图 |
| CF-09 误差与独立 n | 先按声明的独立单位归约 | 不均衡技术重复、tCI/SD/SEM、singleton 及固定 seed Bootstrap |
| CF-10 静默数据变换 | 缺失保留、变换显式、来源文件不变 | 缺失折线两段、全部实际点保留、矩阵空缺不变成零、原文件哈希不变 |
| CF-11 后缀代替内容审核 | 检查实际 XML、文字、引用、图元与尺寸 | 栅格/主动内容/隐藏文字/无效引用反例，以及真实拼版审核 |
| CF-12 PNG 拼版 | 合并 SVG 图元并隔离引用 | 同 ID 源、路径 d 保留、逐面板标签、最终缩放字号和标准示例重建 |
| CF-13 反复确认后端 | 新 CSV 默认 Python，已有项目延续原工具 | Skill 流程核对；本版独立图集完成 Python 路线和交接 |
| CF-14 编辑性 | 图形与文字分别保留，并实际试改 | 指定文字/线条修改后 XML 比较及 Inkscape 渲染；原稿 SHA 不变 |
| CF-15 AI 角标 | 生成图不添加品牌角标，科学文字保持 | `AI/ML` 标签保留，实际可见文字来自原标签和请求的面板字母 |
| CF-16 外部后端状态 | 按原生、配方、工作流、外部接入登记 | registry/doctor/导航检查；本轮外部 R/TikZ/Draw.io/Plotly 状态见第 6 节 |

### 2.3 CF-06：同一实验量的二维与透视图

专门夹具使用同一组 **Synthetic 数值 12、15、14**、相同组标签和单位，画布均为 **120×90 mm**。两份 SVG 都通过文字/图元审核，各有 **13 个 text、0 个 image**；实际预览均已查看。

二维图的三个“屏幕高度/响应单位”均约为 **13.385827 px/unit**，相对极差为 0。透视三维图分别约为 **8.100315、8.309092、8.445599 px/unit**，相对极差约 **4.168%**。这是该相机视角的几何投影差异。由于本例仅有组别和一个响应量，选择二维共同基线进行比较；真实空间坐标、曲面或器件几何继续使用对应三维路线。

输入、两版 SVG/PNG、画布、相机参数、图源哈希与逐图观察保存在 [空间对照目录](evidence/reaudit/spatial-choice/)。两项专门测试已计入本轮总数。

### 2.4 v1.1.0 新增的 CF-17–CF-26

| 冲突 | 保留的行为与实际验证 |
|---|---|
| CF-17 数据首次出现顺序改变样式 | 显式角色颜色/点形/线型跨逆序、缺组、柱/线图保持一致 |
| CF-18 原始测量点与独立单位点混用 | 原始点叠加与柱高/SEM 使用同一组归约后的独立单位值 |
| CF-19 计数直方混叠密度或平移对数正态 | 明确密度单位与正数支持域，保留 MLE 参数及无效输入反例 |
| CF-20 自动挑选全部数字列 | 测量列显式选择，保留 ID、缺失和列顺序 |
| CF-21 等格/空占位轴覆盖主面板 | 先分配跨行跨列范围；三面板产生三个实际 Axes，并验证层级几何 |
| CF-22 改色扩大成改科学文字或几何 | 只允许具体 text/tspan 的指定修改，未选单位尾文、空格及路径保持 |
| CF-23 精修后覆盖、取消冻结或路径别名 | 主源交接保留已观测 SHA；旧锁、路径别名和跨图选源冲突均有反例 |
| CF-24 隐藏刻度误入必需标签 | 在最终尺寸绘制后收集真正可见的 Axis/Axes 文字，四类 Seaborn 共同导出 |
| CF-25 HTML 图件和脚本内容混为证据 | 构造论文 HTML 夹具验证嵌套子图、图注、alt、上下文、相对 URL；脚本/隐藏模板忽略 |
| CF-26 文献读图值缺少来源 | DOI/URL、图表号、单位、数字化方法、变换和不确定性逐字段验证 |

详细用例指针见 [新增冲突记录](CONFLICTS.md#5-v110-新增比较保留哪种行为怎样验证)。其中项目与编辑比较的早期失败及修复也保存在 [重审证据](evidence/reaudit/conflict-review.json)：包括 `tspan` 尾文单位、祖先分组扩大文字许可、alt 元数据引用、快照别名和冻结文件身份。

## 3. 实际导出与成图审阅

### 3.1 发布示例的 SVG 指标

以下数值直接取自仓库当前示例的 `svg_audit.metrics`；输入与标题均标明 **Synthetic**。表中的字号是最终 SVG 几何换算后的最小值。

| 示例 SVG | 最终 mm | text | path | image | 最小 pt | 对应 manifest |
|---|---|---:|---:|---:|---:|---|
| [benchmark](../examples/outputs/benchmark.svg) | 180×135 | 84 | 357 | 0 | 7.0 | [记录](../examples/outputs/benchmark.manifest.json) |
| [asymmetric](../examples/outputs/asymmetric.svg) | 183×125 | 49 | 81 | 0 | 7.5 | [记录](../examples/outputs/asymmetric.manifest.json) |
| [line](../examples/outputs/line.svg) | 90×60 | 17 | 46 | 0 | 7.5 | [记录](../examples/outputs/line.manifest.json) |
| [distribution](../examples/outputs/distribution.svg) | 90×60 | 11 | 32 | 0 | 8.0 | [记录](../examples/outputs/distribution.manifest.json) |
| [Seaborn facet](../examples/outputs/seaborn/facet.svg) | 180×78 | 20 | 11 | 0 | 7.0 | [记录](../examples/outputs/seaborn/facet.manifest.json) |
| [Seaborn pair](../examples/outputs/seaborn/pair.svg) | 160×150 | 24 | 26 | 0 | 7.0 | [记录](../examples/outputs/seaborn/pair.manifest.json) |
| [Seaborn joint](../examples/outputs/seaborn/joint.svg) | 120×120 | 17 | 63 | 0 | 7.0 | [记录](../examples/outputs/seaborn/joint.manifest.json) |
| [Seaborn cluster](../examples/outputs/seaborn/cluster.svg) | 165×203 | 58 | 455 | 0 | 7.0 | [记录](../examples/outputs/seaborn/cluster.manifest.json) |

尺寸按声明容差 `max(0.1 mm, 0.1%)` 比较。图形路径与真实 `text/tspan` 标签同时检查，所有表列示例的结构审核均通过。

### 3.2 实际视觉观察

本轮重审使用 **Inkscape 1.2.2** 渲染并查看简洁/全框轴对照、真实数据拼版、六面板阴性结果、热图与机制组合，以及指定文字/线条修改后的对照图。观察记录确认矩阵 0/负值/空缺、色条标签、组别、误差和箭头均可见；编辑对照保持几何与未选标签。

Seaborn 的四类图已重新导出，并实际查看全部最终 PNG。初次预览发现 clustermap 的色条/标签覆盖行树和首列，标题穿过列树，且初始较小画布使单位标签隔行显示。修复后直接在最终 **165×203 mm** 画布上创建网格，为色条和标题预留独立空间；色条与热图、行树、列树均不重叠，标题距列树约 **8.638 mm**，**48 个单位标签和 144 个数值单元**完整保留。列 z-score（ddof=1）、average linkage、Euclidean distance 和 −2～2 色阶范围保持不变。

PairGrid 的对角密度图改为按变量确定展示纵轴，同一变量内各方法仍共用尺度，标题与图例位置也已调整；共同分箱、密度定义、三组散点关系中的全部 48 个观测及语义样式保持不变。FacetGrid 和 JointGrid 的最终预览标签、图例与边际位置清楚。两项新增布局回归和六项 Seaborn 方法已单独通过；修改前后观察、数值约束及最终 8 个 SVG/PNG 文件哈希见 [seaborn-visual-review.json](evidence/reaudit/seaborn-visual-review.json)。

CF-06 的两版成图已有带资产 SHA 的完整审阅记录。P3 独立图集另外查看了最终尺寸、放大和灰度预览，见下一节。视觉记录按具体文件和版本组织。

## 4. 独立使用与完整图集交接

### 4.1 本版 P3：两张方法比较图与候选版本

本版独立试用产物保存在 [pilot-v11/README.md](evidence/pilot-v11/README.md)。任务使用 **126 行学习数据与 18 行终点数据**，三个方法、各六次独立运行、七个时间点；无缺失、无排除。21 个 group×epoch 均值顶点、18 个终点和三根柱高均与独立 Python 标准库计算核对；两种布局候选也检查了实际 SVG 坐标。[独立数据核验](evidence/pilot-v11/qa/independent-data-check.json) 保存 **694 条具体检查**，这些检查不另计入前述 unittest 方法数。

| 方法 | 终点均值 (%) | 样本 SD（百分点） | 独立运行 n |
|---|---:|---:|---:|
| Baseline | 57.881333 | 0.866006 | 6 |
| Context | 69.476167 | 1.252156 | 6 |
| Proposed | 79.047500 | 1.307871 | 6 |

两张最终图分别为 **180×85 mm** 和 **180×90 mm**，含 **24/33 个可见文字元素、52/34 个 path、0 个 image**，最小字号均约 **7.5 pt**。图 2 实际比较 180×90 mm 横排与 180×130 mm 竖排，选中横排并保留另一候选。版本、理由及最终尺寸/灰度观察见 [图集说明](evidence/pilot-v11/README.md)。

项目实际生成图注、alt text、图集索引，选中 `polished` SVG 作为主源，并冻结上游 JSON、共享样式与相关源文件。JSON 源阶段的语义样式检查、SVG 精修 `revision` 和最终视觉观察相互补充。

冻结的试用运行时与最终发布代码逐文件比较，14 个脚本中有 13 个字节一致；唯一变化是本任务未调用的 Seaborn 配方布局。P3 使用的 plot、annotate、revision、audit、project 路线保留相同代码；Seaborn 最终版另有本轮六方法与四份成图验证。[代码对应记录](evidence/reaudit/pilot-runtime-comparison.json)

### 4.2 重建和编辑试验

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 两图独立重建 | 最终 SVG 与渲染 PNG 均逐字节一致，尺寸及最小字号一致 | [尺寸与重建](evidence/pilot-v11/qa/reproduction-and-size-report.json) |
| PDF 内容比较 | PDF 文件 SHA 不同；解压后页面内容、资源和非日期元数据一致，CreationDate 单独排除比较 | [PDF 对象比较](evidence/pilot-v11/qa/pdf-metadata-comparison.json) |
| 文字与图形实际编辑 | 在副本中修改具体 `text` 标题和原生背景 `path` 填色，Inkscape 渲染返回 0；正式 SVG SHA 不变 | [编辑与误改拦截](evidence/pilot-v11/qa/editability-and-guard-report.json) |
| 未授权修改的反例 | 未允许的文字修改 exit 2；指定 text ID 后 exit 0；单独移动一个数据点 exit 2 | [编辑与误改拦截](evidence/pilot-v11/qa/editability-and-guard-report.json) |
| 主源交接与冻结复核 | 图集建立基线、SVG 主源交接、冻结基线再核对均保留相应报告 | [P3 项目索引](evidence/pilot-v11/reports/project-index.json) |

PDF 的原始字节探针和后续对象比较均保留在 P3 QA 目录中，最终结论采用已成功解压和解析的对象比较。实际编辑方式为原生 XML 修改与 Inkscape 渲染。

v1.0.0 的 P1 重复测量图、P2 流程变体和编辑试验是历史独立使用证据，见 [历史报告](https://github.com/PresleyRen/figurefoundry-scientific-figures/blob/v1.0.0/docs/TEST_REPORT.md)；本版新增试用及交接说明统一见 [FORWARD_TESTS.md](FORWARD_TESTS.md)。

## 5. 整个 Skill 文件夹的可移植性

[portable-skill.json](evidence/reaudit/portable-skill.json) 记录了将 **仅 `skills/figurefoundry` 文件夹**复制到新的临时目录、从仓库外调用的实际结果：

| 调用 | 结果 |
|---|---|
| `coverage` 来源特点查询 | exit 0，命中 1 项 |
| `atlas` 专业路线查询 | exit 0，命中 1 项 |
| `diagram` 原生示意 | exit 0，审核通过 |
| `plot` 数据图 | exit 0，审核通过 |
| 技能内 `ff_seaborn` 的 joint 配方 | exit 0，审核通过 |

输入示例在调用时使用明确的绝对路径；实现和知识索引来自复制后的 Skill。此项验证整体文件夹可独立调用，使用的是同一已安装依赖的 Python 环境。

## 6. 四种执行模式与环境

| 模式 | 当前落点 | 本轮实际执行范围 |
|---|---|---|
| `native` 原生模块 | 16 类图、统计/导出/审核、示意/拼版、共享样式、图集、精修、参考摄取和源码定位 | 对应自动模块、实际示例、原生 SVG 编辑及 P3 图集已运行 |
| `recipe` 可执行配方 | Seaborn 四类 grid、显式加权均值、自定义绘图共同出口 | 四类实际导出、权重解析答案及 portable joint 已运行；其他专用源码按具体任务接入 |
| `workflow` Agent 工作流 | 科学选图、参考语料审阅、图注/候选/主源交接、期刊记录和 26 条专业路线 | P3 图集与候选审阅已执行；HTML 摄取使用明确构造夹具；专业图谱验证检索、字段和接入指针 |
| `external-adapter` 外部接入 | R/ggplot2、TikZ、Draw.io、Plotly 等既有项目 | 本轮保留源码与 SVG 出口的接入说明及依赖状态；没有运行这些完整外部工具链 |

本轮自动测试环境：

| 组件 | 版本 |
|---|---|
| 操作系统 / Python | Linux / 3.12.14 |
| Matplotlib | 3.10.8 |
| NumPy | 2.3.5 |
| pandas | 2.2.3 |
| SciPy | 1.17.0 |
| openpyxl | 3.1.5 |
| Seaborn | 0.13.2 |
| 实际预览渲染器 | Inkscape 1.2.2 |

SVG 审核覆盖文件结构、完整预期文字、原生图元、尺寸与有效字号；视觉判断采用具体成图记录。投稿格式与期刊要求由项目的期刊记录确认。远程 CI 状态以对应发布提交的 Actions 记录为准。
