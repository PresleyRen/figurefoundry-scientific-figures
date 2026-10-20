# FigureFoundry v1.0.0 验证报告

验证日期：2026-10-20（UTC）。本报告区分**自动行为测试、实际 SVG 渲染、独立任务
试用和未执行范围**。上游源码比较不等于执行所有上游项目。最终源文件以发布 tag 为准。

## 1. 自动测试结果

**96 项 unittest 测试方法全部通过；0 失败、0 错误、0 跳过。** 最终本地运行
33.244 秒。详细用例名、时间和实际环境见 [test-results.json](test-results.json)。
其中 16 个原生图型是在一个测试方法下分别执行的 subtests，没有把它们虚增为
额外测试方法数量。

| 测试文件 | 方法数 | 实际验证内容 |
|---|---:|---|
| `test_svg_audit.py` | 25 | 真 SVG 文字/路径/位图反例；DTD/实体、脚本/事件、外链、引用/循环、有限几何、变换字号、完整标签与隐藏文字 |
| `test_diagrams.py` | 12 | 五种节点、中文/XML 标签保留、换行、反馈、组合引用/CSS 隔离、比例、最终字号、无效输入 |
| `test_plot_engine.py` | 22 | 手算统计语义、缺失断点、阈值曲线、Pareto、16 类真实 SVG 导出、来源哈希和合法阴性结果 |
| `test_conflicts.py` | 8 | 实际导出 A/B：转曲、位图热图、色条、紧裁切、现存 usetex、必需标签、DPI 和必需 SVG |
| `test_cli_and_data.py` | 24 | 五种实际数据格式、哈希/列检查、子进程 CLI、能力路径、期刊记录、对数轴有效/无效输入 |
| `test_diagram_cli_contract.py` | 3 | 省略 label、spec/CLI 字号优先级、非法字号、组与边的字号传播 |
| `test_final_contracts.py` | 2 | 对数轴限值不得静默修正；多行文字、单元格标注、面板字母和色条标签清单 |

运行命令：

```bash
python tools/run_checks.py --report docs/test-results.json
python tools/check_package.py
python examples/generate_examples.py
```

Skill Creator 的 `quick_validate.py skills/figurefoundry` 也已实际运行，结果
`Skill is valid!`。仓库自己的包检查用于 CI 和独立安装环境，核查 frontmatter、
版本、Python 语法、能力路径及本地文档链接。

### 统计答案不是照抄实现

- `[1,3,5]` 的均值为 3，样本 SD 为 2，SEM 为 `2/√3`；CI 使用已知
  `t(.975,df=2)=4.302652729…`，与独立计算核对。
- 技术重复 `[0,0,0,0,10,20]` 按三名独立受试者归并后均值为 10，不能按六行
  计算成 5。重复单位未声明组内处理时必须报错。
- n=1 时不确定性不可估计，不能假装误差为 0；n>1 且实际完全相同时 SD=0 有效。
- 排序 `P,N,P,N` 的 ROC AUC=0.75、AP=5/6；全分数并列时 AUC=0.5；反向完美
  排序 AUC=0 仍正常绘图。阈值并列顺序不改变曲线。
- 原始与汇总折线中的缺失点保留断口；Pareto 重复的同一前沿点不被误判为互相支配。
- 全非显著火山图、零组间效应与低相关有效输入均不触发人为美化门槛。

## 2. 实际导出与可见成图

发布示例由固定 seed=1729 的明确合成数据生成。数据生成/图注定义见
[examples/README.md](../examples/README.md)。实际读取最终 SVG 得到：

| 文件 | 最终 mm | text | path | image | 最小实际 pt |
|---|---|---:|---:|---:|---:|
| [benchmark.svg](../examples/outputs/benchmark.svg) | 180×135 | 84 | 357 | 0 | 7.0 |
| [line.svg](../examples/outputs/line.svg) | 90×60 | 17 | 46 | 0 | 7.5 |
| [distribution.svg](../examples/outputs/distribution.svg) | 90×60 | 11 | 32 | 0 | 8.0 |
| [diagram.svg](../examples/outputs/diagram.svg) | 180×85 | 10 | 9 | 0 | 7.0 |
| [composition.svg](../examples/outputs/composition.svg) | 190×160 | 41 | 87 | 0 | 7.0 |

浮点尺寸按声明容差 max(0.1 mm,0.1%) 比较。路径是合法几何、线条、箱体和色条；
不把 path 数量误当作文字是否转曲。图件的预期文字与真实 text/tspan 清单同时检查。

实际使用 Inkscape 命令行渲染 SVG，并查看全图及密集区域。检查了轴/图例单位、
面板间距、颜色/标记一致性、曲线/CI、矩阵数字、色条、标签和流程箭头。发现 SVG
阅读器对连续色条单元格的细缝后，给相邻矢量单元设置 face 边色并重新生成；保持
矢量，没有用位图掩盖。默认 SVG 不添加平台标识或水印。

## 3. 独立任务试用

两项试用使用独立、未继承开发历史的执行者，只提供主 Skill 路径、研究任务及原始
输入，不提供内部预期解法。开发者随后复核其产物和具体问题。

### P1：陌生 CSV → 双面板重复测量图

输入 24 行，Control/Treatment 各三名独立 subject，每名在四个时间点测量。请求
左侧均值/95%CI、右侧末次时间点分布，不做假设检验。执行者自行检查独立单位、
创建末次数据表、写源规格、生成图与图注并执行验证。

结果为 **180×90 mm、36 个 text、57 个 path、0 个 image，最小约 7.5 pt**。
八个 group×time 单元用独立解析 Student-t 公式核对，全部 n=3；没有误把重复时间
行当成更多独立个体。完整重建及源模块快照比较见 [独立试用证据](FORWARD_TESTS.md)。
最终冻结版代码复跑单独记录，不把开发中间状态当作最终版本。

执行者在独立副本中修改真实 SVG 的 Time 标签、Control 曲线颜色及线宽，并用
Inkscape 重渲染；原稿 hash 不变。成图全彩、灰度和小尺寸视图均实际查看。

### P2：实验流程 → 宽窄变体与可编辑性试改

请求 Specimen→Preparation→Assay→Analysis→Result 主路径，质控从 Assay 接收信息
并反馈 Preparation，数据库只向 Analysis 提供对照。独立完成 180×80 mm 和
120×94 mm 两版，**均保留七节点/七有向边，八个完整可见标签，0 个 image**。

文字与颜色试改为 Result→Output、结果椭圆紫色→绿色，所有路径属性不变，PNG
变化局限于目标椭圆区域，原稿 SHA-256 不变。证据见
[editability-test.json](evidence/pilot-diagram/editability-test.json)。执行者发现数据库
圆柱顶部与标签偏近，实际加高后重新生成、审核与查看；这项布局问题没有伪装成
静态程序可以自动判断。

**试改范围是原生 XML 修改＋Inkscape 渲染**。本报告没有声称完成全部 GUI 拖拽
或所有 SVG 编辑器的兼容性测试。两项均未给定具体期刊，因此明确标为 planning
profile，未宣称期刊认证。

## 4. 冲突决策落实

定义和上游证据在 [CONFLICTS.md](CONFLICTS.md)。下表区分实际自动验证与人工判断：

| CF | 执行状态 | 证据/保留原因 |
|---|---|---|
| 01 文字转曲 | 自动通过 | 同图 path-font 反例失败，live text 与完整标签通过 |
| 02 位图热图/色条 | 自动通过＋渲染复核 | imshow 反例；独立色条 rasterization 反例；原生 mesh 通过 |
| 03 tight 尺寸 | 自动通过 | 原始 tight 输出尺寸改变；共享 exporter 输出目标 mm |
| 04 期刊 preset | 记录检查通过＋官方源码核对 | 缺来源/日期发警告；未解决的冲突失败；未做自动期刊认证 |
| 05 边框审美 | 人工设计决定 | 保留参数，默认简洁边框；不是对所有审美做自动最优排名 |
| 06 装饰 3D | 人工设计决定＋原生约束 | 定量图使用 2D；数据库圆柱仅作语义示意；未证明所有 3D 场景 |
| 07 占位面板 | 自动通过＋来源复核 | 发布定量面板来自随附数据/摘要；组合保留真实标签和对象 |
| 08 显著性门槛 | 自动通过 | 阴性/零效应/反向分类回归可绘制 |
| 09 误差和独立 n | 自动通过 | 手算 tCI/SD/SEM 与技术重复归并 |
| 10 静默数据处理 | 自动通过 | 缺失断口、计数、hash、原数据不变；汇总定义记录 |
| 11 后缀验矢量 | 自动通过 | 真实 XML、隐藏文字、位图/主动内容/引用反例 |
| 12 PNG 拼版 | 自动通过＋渲染复核 | 双源同 ID/CSS 隔离、实际 SVG 三面板和缩后字号 |
| 13 强制后端确认 | 独立试用通过 | 普通 CSV 直接完成 Python 路线，没有无必要的后端提问 |
| 14 编辑性概念 | 自动通过＋实际试改 | 完整文字清单、native 图元、可见试改与原稿 hash |
| 15 无 AI 角标 | 代码/示例检查通过 | 无主动加标；真实 AI 字样保留；Creator/source 记录没有被伪删 |
| 16 外部后端冒充 | 文档/依赖检查通过 | native、custom-source、optional-not-runtime-tested 明确分级 |

## 5. 测试发现并修复的问题

开发阶段保留了会失败的反例，并据此修复：整数 x 因行类型转换丢点；误将视图外
tick 字符加入必需清单；遗漏色条/面板等标签；无效 JSON 类型泄露 AttributeError；
CSV/TSV 重复表头被 pandas 自动重命名；期刊 URL 类型无校验；对数轴限值被
Matplotlib 静默忽略；默认节点标签和 CLI/spec 字号不一致；高最低字号没有传给
组/边标签。最终回归覆盖这些问题，没有通过删除反例来取得全绿结果。

## 6. 环境与实际边界

Linux、Python 3.12.14、Matplotlib 3.10.8、NumPy 2.3.5、pandas 2.2.3、SciPy 1.17.0、
openpyxl 3.1.5。Inkscape 可用并实际执行；部分只读字体缓存/最近文件目录产生
非阻断警告，渲染返回 0 且图已查看。没有为消除警告修改受保护的系统目录。

Rscript、dvisvgm、dot 未提供本次验证所需完整后端。R/svglite、TikZ、Plotly/Kaleido、
Draw.io 全流程未运行；Seaborn 为可选自定义前端，未覆盖所有图型。中文/XML 字符
保留通过结构测试，英文示例已目视检查；没有把中文跨字体/跨编辑器兼容性写成通过。

不能由本测试证明：期刊接收、科学真实性、所有字体存在、所有布局无重叠、所有
第三方 SVG 特性、复杂依赖测量模型的统计适用性、所有编辑器的交互行为。
GitHub CI 运行状态以实际 Actions 页面为准，本地验证与远程 CI 分开记录。
