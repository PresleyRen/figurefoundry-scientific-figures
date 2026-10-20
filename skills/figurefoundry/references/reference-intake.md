# 文献参考图与 benchmark 来源

把已保存的论文 HTML 转成可检查的参考图资料表，再从其中提取适合当前论文的科学表达方法。参考图资产、图注、正文证据和后续设计判断分别有明确字段，方便追溯和复用。

## 目录

1. [完整使用路径](#完整使用路径)
2. [HTML 导入](#html-导入)
3. [Manifest 结构](#manifest-结构)
4. [科学关系与语义样式审查](#科学关系与语义样式审查)
5. [文献 benchmark 登记](#文献-benchmark-登记)
6. [扩展位置与测试](#扩展位置与测试)

## 完整使用路径

1. 用当前可用的浏览检索工具找到用户要求的相关论文，保存用于本项目的论文 HTML，并记录原始论文页面 URL。优先保存保留原始 figure、caption 与 asset 路径的 HTML。
2. 运行 HTML 导入，得到逐论文参考图 manifest。保留原 HTML，manifest 会记录其 SHA-256。
3. 根据图注、正文上下文和实际查看的图像，填写科学问题、实体关系、面板角色、语义配色与可复用设计特点。
4. 如要将文献曲线或表格作为 benchmark，建立单独的来源记录，填写图表定位、单位、读图方法、变换与不确定性。
5. 将选定的科学表达方法写入本项目图件合同；将 benchmark 数值表交给正常数据读取和绘图流程。参考图资料表保留对应论文和图号。

论文检索、实际图像查看与设计判断由 Agent 工作流完成；本模块提供可重复的本地 HTML 解析和登记检查。模块读取本地 HTML，不访问网络，不执行其中的 JavaScript，不自动下载图像。

## HTML 导入

~~~bash
python <skill-dir>/scripts/figurefoundry.py references \
  --html references/paper.html \
  --source-url https://example.org/articles/paper.html \
  --context-blocks 2 \
  --out references/paper-figures.json
~~~

以上 URL 是演示地址，使用时替换为保存 HTML 对应的论文页面。

Python 接口：

~~~python
from ff_reference import extract_figures

manifest = extract_figures(
    "references/paper.html",
    "https://example.org/articles/paper.html",
    context_blocks=2,
    include_ungrouped=False,
    encoding="utf-8",
)
~~~

| 参数 | 作用 |
|---|---|
| html_path / --html | 已保存的论文 HTML；仅读取 |
| source_url / --source-url | 完整 HTTP(S) 论文 HTML 页面 URL；相对图片路径以此和有效 base href 解析 |
| context_blocks / --context-blocks | 每张图前后分别保留的段落或标题数量，默认 2；0 表示只保留图件本身 |
| include_ungrouped / --include-ungrouped | 将 figure 容器之外的 img 也纳入资料表；默认关闭，避免把普通页面图片混入论文图件 |
| encoding | Python 接口的文件解码设置，默认 UTF-8 |

识别的结构包括原生 figure/figcaption、常见 ltx_figure/ltx_caption、figure-caption 以及 role="figure" 容器。外层 figure 作为一个记录；其中嵌套的 figure 作为子图，保留各自图注和图片 ID。普通图像来源支持 src、data-src 和常见 srcset / picture 候选。相对路径、绝对路径和协议相对 URL 都会解析为可追踪的 HTTP(S) 地址。

脚本、样式、模板、noscript、导航、页脚和显式隐藏元素不参与图件或正文证据提取。正文上下文保留 p、标题和常见 ltx_para，排除图注并去掉 ltx_para 包裹 p 产生的重复。

## Manifest 结构

~~~text
reference-figure-manifest
├── source
│   ├── file + sha256 + encoding
│   ├── url + asset_base_url + retrieval
│   └── metadata: title, authors, doi, canonical_url
├── figures[]
│   ├── id + dom_id + source_url + kind
│   ├── label + caption
│   ├── images[]: id, source_raw, source_url, srcset, alt, alt_status
│   ├── subfigures[]: id, parent_id, caption, image_ids
│   ├── context: before[], after[]
│   ├── inline_svg_present + issues[]
│   └── review: observations, inferences, decisions, checks[]
└── summary + warnings
~~~

| 字段 | 阅读与使用方式 |
|---|---|
| source.sha256 | 与原 HTML 的字节一致；用于识别本次实际读取的来源版本 |
| source.metadata | HTML 明示的书目信息；正文标题作为备用标题 |
| id | 本次文件内稳定的序号 ID；同文件、同参数重复解析结果相同 |
| dom_id | 原始 HTML 元素 ID；与论文页面锚点对应 |
| caption | 属于该外层图的图注；子图图注分别保留，不重复拼入主图图注 |
| images.source_raw / source_url | 保存的原路径与解析后的资产地址；图片未在导入期间下载 |
| alt_status | present、empty、missing 三种状态；原文缺失时保留缺失状态 |
| subfigures.image_ids | 关联外层图中已记录的图片，不重复保存图片记录 |
| context.before / after | 就近正文原文、标签类型和 DOM ID；与图注分开，便于检查证据 |
| inline_svg_present | 标识图中出现内联 SVG；没有 img 时仍保留图件记录供查看 |
| issues | 缺少图注、缺 alt、无法形成 HTTP(S) 资产 URL等可操作问题 |
| summary | 外层图、总记录、图片、alt 状态、未解析图片及容器外图片的计数 |

图片 URL 是根据输入 HTML 的路径计算的来源地址。若浏览器保存过程把路径改成了本地资源目录，应保留 source_raw 并根据原始页面补回正确来源，或重新保存原始 HTML。实际查看图像后再作颜色、几何与视觉语言判断；标题和图注本身不能证明图像中全部细节。

## 科学关系与语义样式审查

每张参考图得到一份独立 review 模板。所有审查项初始为 pending，提取器只保存证据，不自动把关系判断标成通过。

在 observations 中写图注、正文或实际图面直接支持的观察，并指明 image ID、DOM ID 或来源片段。在 inferences 中写从证据推断的设计意图及依据。在 decisions 中写本项目将采用的表达方法和调整原因。

| 审查 ID | 需要记录的内容 | 作用 |
|---|---|---|
| scientific-question | 问题、主张、读者、五秒内应看懂的内容 | 图件叙事有明确焦点 |
| panel-role | 方法、结果、对照、理论界限、定性证据分别在哪个面板 | 选择合适图种并组织阅读顺序 |
| entities-and-counts | 对象 ID、归属、整体与局部对应、数量、单位、分母 | 几何美化保持科学身份与数量一致 |
| relations | 边的起点/终点及流向、更新、影响、因果或比较含义 | 连线与实验关系一一对应 |
| agent-update | 可变对象、冻结内容、更新前后、更新信号/算子/频率、持久性、接受/拒绝和稳定性证据 | Agent 学习/记忆/进化过程表达准确 |
| semantic-style | 方法/基线/理论界限/状态的颜色、marker、线型以及跨图一致性 | 颜色与符号帮助识别同一科学角色 |
| layout-and-readability | 视觉锚点、阅读顺序、实际尺寸、灰度和相关色觉预览 | 确认布局在论文中仍能读清 |
| transferable-design | 原始观察、设计推断、本项目采用的具体做法 | 将参考论文转成可复用方法 |

不适用的项目可填写 not-applicable 并说明原因。需要实际图像查看才能回答的项目保持 pending，直到有对应查看记录。该模板也可通过 reference_review_template() 单独生成。

如要制作多论文 contact sheet，先按用户任务取得所需参考图文件，保留 manifest 中的论文/图件/图片 ID，再用现有排版工具生成带来源标签的预览。此模块的现成输出是资料表，不附加图片下载或联系表渲染。

## 文献 benchmark 登记

数字化曲线和直接引用的文献表格使用显式 origin。下面是构造的字段示例，DOI 与数值单位仅用于说明 schema：

~~~json
{
  "id": "literature-curve-01",
  "origin": "digitized-literature",
  "source": {
    "doi": "10.1234/example",
    "url": "https://example.org/articles/paper",
    "figure": "Figure 3b"
  },
  "units": {"time": "ms", "response": "mV"},
  "digitization": {
    "method": "Calibrate axes, then select curve points",
    "tool": "Name of the digitization tool",
    "tool_version": "Recorded version"
  },
  "transformations": [
    {
      "operation": "unit_conversion",
      "details": "Multiply source seconds by 1000 to report milliseconds"
    }
  ],
  "uncertainty": {
    "status": "unknown",
    "description": "Reading uncertainty has not been estimated"
  }
}
~~~

运行完整性检查：

~~~bash
python <skill-dir>/scripts/figurefoundry.py benchmark-source \
  --record references/literature-curve-01.json \
  --out references/literature-curve-01.review.json
~~~

也可以直接调用 validate_benchmark_record(record)，返回 passed、errors、warnings、record、normalized_source。检查不修改输入对象。

| 字段 | 契约 |
|---|---|
| id | 非空稳定标识，用于连接参考资料与数据表 |
| origin | digitized-literature 或 reported-literature；本研究数据沿用原始数据 manifest |
| source.doi / url | 至少一个有效格式的 DOI 或完整 HTTP(S) URL；声明的另一项也检查格式 |
| source.figure / table | 至少一个图或表定位，如 Figure 3b 或 Table 2, row B |
| units | 至少一个变量→单位映射；无量纲量明确写 dimensionless |
| digitization.method | digitized-literature 必填；reported-literature 可直接记录表格来源，无需构造读图过程 |
| transformations | 数组，逐项说明操作与参数；没有变换时显式写 [] |
| uncertainty.status | estimated、reported、unknown 或 not-applicable |
| uncertainty.description | 说明估计方法、文献报告、未知原因或不适用原因 |
| uncertainty.value / unit | 可选定量误差；数值需非负有限且有单位；unknown 状态不同时声明数字误差 |
| data.file / sha256 | 可选数据表链接；提供时要求文件名与完整 SHA-256 |

变换记录应覆盖实际采用的单位换算、归一化、插值、平滑、坐标逆变换和图中取点。来源检查只验证这些字段的完整性与一致性，未代替人工阅读原文。unknown 可通过字段检查，同时保留提示，输出图注继续采用相同描述。

## 扩展位置与测试

| 扩展目标 | 定位 |
|---|---|
| 新论文 HTML 容器/图注结构 | ff_reference.py 的 _is_figure / _is_caption；增加对应真实形态 HTML fixture |
| 新资产字段或响应式图片规则 | _image_record / _srcset |
| 新书目信息 | extract_figures 的 metadata 读取 |
| 新实验语义/Agent 机制审查项 | _REVIEW_ITEMS；使用稳定审查 ID |
| 新 benchmark 来源字段 | validate_benchmark_record；字段含义与此表同步 |
| 回归入口 | tests/test_reference_intake.py |

~~~bash
python -m unittest discover -s tests -p 'test_reference_intake.py' -v
~~~

测试文件使用明确标记的构造 HTML fixture，覆盖 arXiv/ar5iv 常见结构、嵌套子图、相对 URL、base/srcset、空/缺失/中文 alt、正文归属、脚本忽略、来源文件不变、禁用 socket 时的本地执行以及 benchmark 字段与不确定性检查。

方法来源：[S10 Scientific-Figure-Design](https://github.com/qhy991/Scientific-Figure-Design/blob/d88f87dad2952af3ee450873c67e95be5ae44e71/SKILL.md) 的参考图资料/语义审查与 [S14 scientific-plotting](https://github.com/1111asas/scientific-plotting/blob/d5dbf14c488f080c27e63c6ed4dce24cd9614442/scientific-plotting/SKILL.md) 的文献 benchmark 记录方法。脚本为 FigureFoundry 独立实现。

