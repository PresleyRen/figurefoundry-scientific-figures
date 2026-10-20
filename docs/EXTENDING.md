# 扩展 FigureFoundry：从能力编号定位

## 三层索引，先定位再修改

| 想找什么 | 索引文件 | 命令 |
|---|---|---|
| 某个来源 Skill 的具体特点、与谁互补、怎样继续补 | `assets/source-coverage.json` | `coverage --source S08` 或 `coverage --query 主源` |
| 已有模块、说明与测试 | `assets/capabilities.json` | `capabilities --query 灰度` |
| 专业实验图的字段和接入方法 | `assets/specialty-routes.json` | `atlas --query 相图` |

上述路径相对 `skills/figurefoundry/`。`Sxx-Fxx` 表示来源特点，`FF-*` 表示可复用能力，
`SP-*` 表示专业任务路线。一个能力可以补足多个来源的短板，一个专业任务可以组合几个能力。
`coverage` 的每条结果直接返回 `extension.target` 和 `extension.how`，作为下一次修改的起点。

### 常见扩展落点

| 模块 | 负责内容 | 扩充时的关键验证 |
|---|---|---|
| `ff_data.py` / `ff_plots.py` | 表格、独立单位、估计、图型、拟合、GridSpec、norm | 手算答案、合法阴性、源值不变、真实 SVG |
| `ff_style.py` | 具名样式、项目默认值、合并优先级 | 相同风格不同数据的 identity；字段实际生效 |
| `ff_project.py` | 图集、实体/数量、候选、共享角色、冻结主源 | snapshot 独立副本、路径身份、来源 SHA、选中版本 |
| `ff_quality.py` | 对比度、CIE L*、SVG 描述、样式编辑差分 | 解析端点、tspan 单位与空格、几何保持 |
| `ff_reference.py` | 论文 HTML 图件和文献 benchmark 来源 | 嵌套归属、原文上下文、相对 URL、缺失信息 |
| `ff_inventory.py` | Python/Notebook 布局与导出位置 | 真实行号/单元、动态表达式保持、输入不执行 |
| `ff_seaborn.py` | 分面、Pair/Joint/Cluster 和显式权重配方 | 隐藏 Axis、共同分箱、行数、矢量色条和文字 |
| `ff_diagram.py` / `ff_compose.py` | 科学关系和原生拼版 | 逐源标签、引用隔离、最终缩放字号 |

修改索引后运行 `python tools/render_coverage.py` 重建 [COVERAGE.md](COVERAGE.md)。
包校验会检查固定来源 URL、特点/能力编号、实现与测试路径、互补来源及扩展目标；
`test_coverage_navigation.py` 用真实中英查询和失效路径反例验证这些入口。

能力索引为 `skills/figurefoundry/assets/capabilities.json`。`module` 与 `reference`
相对技能目录，`tests` 相对仓库根目录。每个 FF 编号固定代表一个能力；重构可改路径，
不要把旧编号赋给不相关能力。检索：

```bash
python skills/figurefoundry/scripts/figurefoundry.py capabilities --query bootstrap
python skills/figurefoundry/scripts/figurefoundry.py capabilities --query FF-SVG-01
```

## 1. 新增原生数据图

先阅读 `references/chart-selection.md` 与 `plot-spec.md`，确定图回答的科学问题。
在 `scripts/ff_plots.py` 新增 handler，签名为 `(ax, dataframe, panel, palette, report)`。
仅用原生、非 rasterized Matplotlib 图元；由共享 exporter 完成输出与审核。
把处理器加入 `HANDLERS`、图型加入 `PLOT_KINDS`，并增加新的 `FF-PLOT-*` 注册项。

`report` 保存源数值/统计/变换定义，警告放在 `report['warnings']`。不要私自删除异常点、
填补缺失值或改变实验指标。自定义带文字的艺术对象必须进入预期标签清单。新图需要：

1. 一个手算可核对的最小输入与一组合法阴性结果。
2. 一个确实无效的输入，用明确错误阻止错误科学解释。
3. 生成 SVG 后核对数值、文字、无位图、尺寸和来源 hash。
4. 在最终尺寸下实际看图；没有渲染器时记录未完成视觉复核。
5. 更新参数文档、示例、能力状态和测试记录。

不要只写“函数返回成功”或把实现中的同一计算复制到断言里。置信区间、分类曲线、
聚合等须用独立已知答案验证。改变共享模块时运行相关回归，再运行完整包测试。

## 2. 新增专业后端

将其放入独立模块或 `references/optional-backends.md`，避免增加主 Skill 的加载体积。
最初状态设为 `optional-not-runtime-tested`。记录运行依赖、许可证、输入协议、原始
源文件、版本和输出格式。用含真实标签、标记、裁剪、色条的代表例图验证原生对象。

新后端必须通过 CF-01/02/03/11/12/14：文字不是轮廓、无位图、尺寸一致、引用有效、
可拼版、缩后字号可读。不能让每个后端自己绕过公共 SVG 审核。通过后把状态改为明确
的已测试路线，并记录实际支持的版本/图型；不是“安装了就支持全部”。

## 3. 新增期刊 profile

查确切期刊、文章类型和投稿阶段的官方页面，记录 URL、日期、尺寸、字号、格式与
未决项。保留 SVG 主源，另产出该刊接受的 PDF/EPS/TIFF 等副本；不要假定所有刊都
接受 SVG。模板的名字或审美相似不能成为合规证据。

来源冲突时记录 `conflicting_sources` 和 `resolution`，说明最终采用的页面为何适用。
不能静默覆盖成一个所谓“Nature 通用宽度”。用 `journal --profile` 检查记录结构，
最终仍由人或有浏览能力的 Agent 实查来源。

## 4. 新增参考 Skill

在 `docs/SOURCES.md` 加 S17 等来源编号、仓库、实际入口、commit SHA、许可正文及
核查日。将有用能力归入既有 FF 模块；对新的冲突在 `docs/CONFLICTS.md` 新增 CF
编号。先比较可观察行为，再决定保留何种实现。许可不清楚时只参考一般方法，不能
直接复制整套代码/素材。

在 `source-coverage.json` 为该来源逐特点建立 `S17-F01` 等记录，标明 `native`、
`recipe`、`workflow` 或 `external-adapter`。每项填写相关 FF 能力、实现文件、参考页、
测试、互补来源与下一步扩展位置。可复用旧模块时直接关联，不另建一份矛盾的规则。
新的专业关键词写入 `specialty-routes.json`，配套 atlas 的问题、输入与方法说明。

## 5. 发布回归

```bash
python tools/check_package.py
python tools/run_checks.py --report docs/test-results.json
python examples/generate_examples.py
python examples/custom_seaborn.py --out build/seaborn-check
```

复核 `docs/TEST_REPORT.md` 与当前代码的实际差异，写明自动、人工、独立试用和未跑
范围。新增源或专业后端要有新情境的独立试用，不只重放作者已经熟悉的例子。更新
`VERSION`（CLI/exporter）、`agents/openai.yaml`（若界面行为改变）、能力注册表、
CHANGELOG、依赖版本和发布说明，再提交可核对的 Git commit 和版本 tag。

提交前核对所有数据都是允许公开的示例。技能安装与发布分别验证，不把成功上传 Git
等同于已经在所有 Agent 的 Skills 列表中自动安装。
