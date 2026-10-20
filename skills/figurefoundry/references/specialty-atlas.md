# 专业图谱与领域路由

按实验问题和已有数据选择绘图入口。这里覆盖 S11 的专业图谱/中英关键词、S12 的领域矢量几何和 S15 的工程动力学图型，并接入本项目的数据、统计、SVG 导出与拼版能力。

## 目录

- 路由总览：下面的中英关键词表
- 专业条目：按稳定 SP ID 定位所需数据、接入方式与复核重点
- 四种接入方法：原生 N、自定义 Matplotlib P、自定义 SVG V、外部后端 E
- 扩展清单与方法来源

## 路由总览

**原生**表示 FigureFoundry 已有绘图命令；**已有坐标/分析输出**表示原生渲染器消费这些数值；**custom** 表示在项目中编写对应图源，再接统一 SVG 导出；**外部**表示沿用用户的 R/TikZ 等环境并记录实际运行情况。表中相关 FF ID 用于定位复用模块，不代表每个专业图型都有独立现成命令。

| 稳定 ID | 专业图型与检索词 | 路由 |
|---|---|---|
| [SP-SURVIVAL](#sp-survival) | 生存与删失；生存曲线 / Kaplan-Meier / KM / 删失 / censoring | custom Matplotlib；或外部 R survival/survminer；已有 HR/CI 可接原生 forest。 |
| [SP-RAINCLOUD](#sp-raincloud) | 雨云、山脊与密度分布；雨云图 / raincloud / 半小提琴 / half violin / 山脊图 | 原生 box/violin/hist/ecdf 可做常规对照；半小提琴+箱线+点和 ridgeline 走 custom Matplotlib/Seaborn 或外部 R。 |
| [SP-ENRICHMENT](#sp-enrichment) | 富集、GSEA 与通路；富集图 / 通路富集 / GO / KEGG / GSEA | custom Matplotlib 气泡/排序条/运行富集曲线；已有 R 分析沿用 ggplot2/领域包。 |
| [SP-GWAS](#sp-gwas) | Manhattan、QQ 与 MA；Manhattan / 曼哈顿图 / GWAS / 基因组关联 / QQ图 | custom Matplotlib/外部 R；已有 logFC 与 p 值的火山图可直接用原生 volcano。 |
| [SP-EMBEDDING](#sp-embedding) | PCA、RDA、UMAP 与轨迹；PCA / 主成分 / RDA / 冗余分析 / UMAP | 已有二维坐标可原生 scatter；loading/ellipse/RDA triplot/轨迹用 custom Matplotlib 或外部 R；嵌入计算属于分析脚本。 |
| [SP-EXPRESSION](#sp-expression) | 标记基因、表达和单细胞摘要；标记基因 / marker gene / 基因点图 / gene dot plot / 表达比例 | custom Matplotlib 气泡图/外部 R；原生 heatmap 可展示一个明确数值通道。 |
| [SP-HEATMAP](#sp-heatmap) | 聚类、多注释、密度与三维热图；聚类热图 / clustered heatmap / ComplexHeatmap / dendrogram / 树状图 | 普通长表热图原生 heatmap；树状图/多层注释/密度/3D 走 custom Matplotlib 或外部 R ComplexHeatmap。 |
| [SP-SET-FLOW](#sp-set-flow) | 集合交集、Sankey 与网络流；UpSet / 集合交集 / intersection / 桑基图 / Sankey | UpSet/按流量缩放的 Sankey 走 custom Matplotlib 或外部 R；简单关系图可原生 diagram。 |
| [SP-CORRELATION](#sp-correlation) | 相关、Mantel、边际与成对探索；相关矩阵 / correlation / Mantel / 环境因子 / pairplot | 普通相关矩阵原生 correlation；pairplot、边际密度、Mantel 连线及残差组合走 custom Matplotlib/Seaborn 或外部 R。 |
| [SP-PAIRED](#sp-paired) | 配对、变化量与 superplot；配对图 / paired / before after / 前后对比 / superplot | 基础原始点/区间可原生；成对连线、差值图、Bland–Altman 走 custom Matplotlib。 |
| [SP-MODEL-EVAL](#sp-model-eval) | 模型评估、消融与解释；消融 / ablation / benchmark / 模型对比 / ROC | bar/ROC/PR/confusion/forest/Pareto 原生；校准、水平排序、多轴雷达和专门解释图走 custom Matplotlib。 |
| [SP-TIME-RESPONSE](#sp-time-response) | 时域响应、验证与局部放大；时域响应 / time history / 响应对比 / validation / 收敛曲线 | 普通时序与分组区间原生 line；共享轴、inset、带连接标记的局部放大走 custom Matplotlib。 |
| [SP-SPECTRUM-FRF](#sp-spectrum-frf) | 频谱、功率谱与频响；频谱 / spectrum / FFT / PSD / 功率谱 | 已有一维谱值可原生 line；FFT/PSD/FRF 估计和幅相组合、stem 谐波图走 custom Python/Matplotlib。 |
| [SP-TIME-FREQUENCY](#sp-time-frequency) | 时频、频率热图与参数场；时频图 / spectrogram / STFT / wavelet / 小波 | 已有规则数值网格可原生 heatmap；非均匀网格和复杂轴/色条用 custom Matplotlib pcolormesh/contour。 |
| [SP-PHASE-POINCARE](#sp-phase-poincare) | 相图与 Poincaré 截面；相图 / phase portrait / phase plot / Poincare / Poincaré | 已有二维点可原生 scatter；有序相轨迹、箭头和 Poincaré 组合走 custom Matplotlib。 |
| [SP-BIFURCATION-BASIN](#sp-bifurcation-basin) | 分岔与吸引域；分岔图 / bifurcation / 吸引域 / basin of attraction / 稳定性 | 已计算分岔点可原生 scatter；分支/方向/吸引域组合走 custom Matplotlib；动力学求解在分析脚本中。 |
| [SP-FIELD-SURFACE](#sp-field-surface) | 向量场、等高线与三维表面；向量场 / 矢量场 / vector field / quiver / streamplot | 规则标量矩阵可原生 heatmap；quiver/streamplot/contour/surface/wireframe 用 custom Matplotlib；几何场示意可用外部 TikZ。 |
| [SP-CIRCUIT](#sp-circuit) | 电路与信号连接；电路图 / circuit / circuitikz / 电阻 / 电容 | 标准电气符号优先自定义 SVG 或外部 circuitikz；原生 diagram 适合高层功能框图。 |
| [SP-FORCE-GEOMETRY](#sp-force-geometry) | 受力、机构与几何；受力图 / free body / force diagram / 力学 / 机构 | 简单关系用原生 diagram；精确几何、角度和尺寸标注用自定义 SVG/Matplotlib patches 或外部 TikZ。 |
| [SP-CHEMISTRY](#sp-chemistry) | 分子、反应、能垒与晶格；化学结构 / molecule / molecular structure / 分子结构 / 反应式 | 自定义原生 SVG 或外部 TikZ/化学绘图工具；定量能量曲线可由原生 line 或 custom Matplotlib 绘制。 |
| [SP-BIOLOGY](#sp-biology) | 细胞、通路、基因与质粒；生物结构 / cell / 细胞 / signaling pathway / 信号通路 | 通路/机制关系可原生 diagram；基因/质粒精确几何用自定义 SVG/外部 TikZ；定量数据用原生图再拼版。 |
| [SP-HARDWARE](#sp-hardware) | 硬件层次、阵列、层叠与局部放大；硬件 / hardware / 阵列 / array / crossbar | 高层框图可原生 diagram；重复阵列、层叠/剖面与精确几何由自定义 SVG/Matplotlib patches 或外部 TikZ。 |
| [SP-CS-MATH](#sp-cs-math) | 系统、自动机、树图与数学关系；神经网络 / neural network / 系统架构 / architecture / 自动机 | 基础节点/反馈可原生 diagram；领域符号、状态自环、时间尺度及复杂数学几何用自定义 SVG/外部 TikZ。 |
| [SP-PHYSICS](#sp-physics) | 光路、场论与物理示意；光路图 / ray optics / 光学 / optics / Feynman | 自定义 SVG 或外部 TikZ 领域几何；定量曲线使用原生或 custom 数据图。 |
| [SP-LAYOUT](#sp-layout) | 非对称多面板、摘要和方法主图；多面板 / multi panel / 拼版 / hero panel / 非对称 | 原生 SVG compose + diagram；特殊跨面板共享轴/insets 用 custom Matplotlib；图形摘要采用专门工作流。 |
| [SP-REPORTING-FLOW](#sp-reporting-flow) | CONSORT / PRISMA；受试者流程 / 文献筛选 / records / reports / studies | 原生 diagram + 项目 quantities；按具体研究核对分支单位和计数 |

## 专业条目

### SP-SURVIVAL

**生存与删失**

- 检索词：生存曲线、Kaplan-Meier、KM、删失、censoring、风险表、survival、hazard ratio。
- 实验问题：处理组的事件发生时间和随访风险如何变化？
- 所需数据：subject_id、duration、event_observed、group；明确时间单位、删失编码；风险表需要相同时间点的在险人数。
- 绘图入口：custom Matplotlib；或外部 R survival/survminer；已有 HR/CI 可接原生 forest。
- 接入步骤：从已有生存分析输出取阶梯曲线、区间、删失标记和风险表。用 Matplotlib step / error bands 与表格面板排版；R 项目保留模型与 R 源，导出 SVG 后进入统一审核。
- 复核重点：曲线阶梯、删失状态、事件定义、风险集与区间方法一致；普通折线插值不代替生存估计。
- 相关能力：FF-CUSTOM-01、FF-PLOT-12、FF-OPTION-R、FF-COMPOSE-01；此条为需求补充，复用统一统计图与外部分析接入方法。

### SP-RAINCLOUD

**雨云、山脊与密度分布**

- 检索词：雨云图、raincloud、半小提琴、half violin、山脊图、ridge plot、ridgeline、KDE、核密度、密度估计。
- 实验问题：各组完整分布、典型范围和实际重复点有什么异同？
- 所需数据：long-form group、value、independent_unit；配对设计附 pair_id；记录密度带宽和支持区间。
- 绘图入口：原生 box/violin/hist/ecdf 可做常规对照；半小提琴+箱线+点和 ridgeline 走 custom Matplotlib/Seaborn 或外部 R。
- 接入步骤：先选原生分布图是否足够；需要雨云时在同轴组合半密度、箱线/区间和原始点。每个图层使用同一分组顺序、统计单位和数值尺度。
- 复核重点：带宽、截断和抖动只服务表达；保留点数和原数值；灰度下仍能区分组。
- 相关能力：FF-PLOT-04、FF-PLOT-05、FF-PLOT-06、FF-PLOT-07、FF-CUSTOM-01、FF-OPTION-R；方法来源：S11、S13、S15。

### SP-ENRICHMENT

**富集、GSEA 与通路**

- 检索词：富集图、通路富集、GO、KEGG、GSEA、enrichment、gene set enrichment、dotplot、GeneRatio。
- 实验问题：哪些预先定义的功能集或通路与已完成的分析结果关联？
- 所需数据：term_id、term_name、gene_count、GeneRatio/背景总数、effect/NES、p_adjust；GSEA 曲线还需排名、running score 与命中位置。
- 绘图入口：custom Matplotlib 气泡/排序条/运行富集曲线；已有 R 分析沿用 ggplot2/领域包。
- 接入步骤：读取明确的上游分析表；展示预先声明的排序/筛选与完整结果文件；用面积编码基因数、颜色编码指定统计量，分别建立图例。
- 复核重点：GeneRatio 分母、背景集合和多重校正来源写清；不要将输入基因数和背景数混用。
- 相关能力：FF-CUSTOM-01、FF-OPTION-R、FF-EXPORT-01；此条为需求补充，复用专业表格图与外部分析接入方法。

### SP-GWAS

**Manhattan、QQ 与 MA**

- 检索词：Manhattan、曼哈顿图、GWAS、基因组关联、QQ图、Q-Q、MA图、mean average。
- 实验问题：基因组位置或平均表达如何对应已计算的关联/差异统计量？
- 所需数据：Manhattan：chromosome、position、variant_id、p/p_adjust；QQ：完整检验 p 值及处理规则；MA：mean expression、log fold change。
- 绘图入口：custom Matplotlib/外部 R；已有 logFC 与 p 值的火山图可直接用原生 volcano。
- 接入步骤：构造有说明的染色体顺序和累计位置；阈值来自既有分析；QQ 使用声明的期望分位数；MA 与 volcano 根据横轴科学问题选择。
- 复核重点：零/缺失 p 值处理可追溯，染色体间距不改变基因组坐标；所有检验与显示子集区分。
- 相关能力：FF-CUSTOM-01、FF-PLOT-15、FF-OPTION-R；此条为需求补充，与 S11 的差异表达图谱互补。

### SP-EMBEDDING

**PCA、RDA、UMAP 与轨迹**

- 检索词：PCA、主成分、RDA、冗余分析、UMAP、t-SNE、tsne、embedding、降维、流形、manifold、pseudotime、拟时序、单细胞轨迹。
- 实验问题：样本结构、已计算的嵌入或沿定义轨迹的状态如何分布？
- 所需数据：sample_id、已有坐标、group；PCA 附解释方差和必要 loading；RDA 附响应/环境矩阵和物种向量；轨迹附已有 pseudotime/branch；记录分析参数与种子。
- 绘图入口：已有二维坐标可原生 scatter；loading/ellipse/RDA triplot/轨迹用 custom Matplotlib 或外部 R；嵌入计算属于分析脚本。
- 接入步骤：保留现有模型与坐标，按 sample_id 连接注释；需要箭头/轨迹时增加独立图层；在 manifest 保存模型参数、分析版本和变换。
- 复核重点：原生 scatter 只绘制已有坐标；未经数据支持的簇、因果路径和置信椭圆不由美化生成。
- 相关能力：FF-PLOT-03、FF-CUSTOM-01、FF-OPTION-R；方法来源：S11、S13、S15。

### SP-EXPRESSION

**标记基因、表达和单细胞摘要**

- 检索词：标记基因、marker gene、基因点图、gene dot plot、表达比例、gene expression、单细胞、single cell、bubble scatter。
- 实验问题：不同细胞群或条件的表达强度和检测比例如何比较？
- 所需数据：gene、cell_group、mean expression、fraction expressing、样本/细胞分母；必要时附患者/样本层级。
- 绘图入口：custom Matplotlib 气泡图/外部 R；原生 heatmap 可展示一个明确数值通道。
- 接入步骤：先确定聚合单位，再用颜色表示已声明强度、面积表示比例；保持分母与基因/群顺序；多面板共享角色样式。
- 复核重点：细胞数不自动当作生物重复数；比例分母和表达归一化写清。
- 相关能力：FF-PLOT-08、FF-CUSTOM-01、FF-OPTION-R、FF-STATS-01；方法来源：S11。

### SP-HEATMAP

**聚类、多注释、密度与三维热图**

- 检索词：聚类热图、clustered heatmap、ComplexHeatmap、dendrogram、树状图、densityHeatmap、密度热图、3D热图、3D heatmap、frequency heatmap。
- 实验问题：矩阵模式、样本聚类或分布摘要如何对应实验分组和注释？
- 所需数据：数值矩阵、行列 ID/注释、单位、聚类距离/连接方法和明确排序；密度热图附密度估计；三维高度需独立变量含义。
- 绘图入口：普通长表热图原生 heatmap；树状图/多层注释/密度/3D 走 custom Matplotlib 或外部 R ComplexHeatmap。
- 接入步骤：将排序与分析结果固定后画矩阵；聚类树与矩阵使用同一索引；颜色条保持纯矢量；3D 视图另配便于比较的二维视图。
- 复核重点：色标共享范围、缺失值和归一化定义一致；3D 高度含义与颜色含义明确。
- 相关能力：FF-PLOT-08、FF-CUSTOM-01、FF-OPTION-R、FF-SVG-01；方法来源：S11、S13、S15。

### SP-SET-FLOW

**集合交集、Sankey 与网络流**

- 检索词：UpSet、集合交集、intersection、桑基图、Sankey、流量图、alluvial、network、网络。
- 实验问题：集合重叠、状态流量或明确网络关系怎样组织？
- 所需数据：集合成员 ID/布尔表；流图 source、target、value、unit、stage；一般网络需明确 edge type/direction。
- 绘图入口：UpSet/按流量缩放的 Sankey 走 custom Matplotlib 或外部 R；简单关系图可原生 diagram。
- 接入步骤：由原始成员表计算交集或读取已分析流量；图中每段宽度映射同一单位；关系型节点图不自动当作流量图。
- 复核重点：交集是独占还是包含需说明；流量总量和流入/流出差额按实验含义核对。
- 相关能力：FF-DIAGRAM-01、FF-CUSTOM-01、FF-OPTION-R；方法来源：S11。

### SP-CORRELATION

**相关、Mantel、边际与成对探索**

- 检索词：相关矩阵、correlation、Mantel、环境因子、pairplot、ggpairs、边际密度、marginal density、残差、residual。
- 实验问题：变量关系、距离矩阵关联或拟合残差中有什么结构？
- 所需数据：变量矩阵和观测 ID；Mantel 附距离定义、置换设置和已有结果；残差附预测/实际值与模型定义。
- 绘图入口：普通相关矩阵原生 correlation；pairplot、边际密度、Mantel 连线及残差组合走 custom Matplotlib/Seaborn 或外部 R。
- 接入步骤：选择与研究问题对应的相关/残差量；原生 correlation 展示基础矩阵；额外密度/连接/分面通过独立绘图脚本组合。
- 复核重点：相关类型、缺失处理、重复测量与多重比较来源明确；不设最低相关系数来挑“好看”的结果。
- 相关能力：FF-PLOT-16、FF-PLOT-03、FF-CUSTOM-01、FF-OPTION-R；方法来源：S11、S13、S15。

### SP-PAIRED

**配对、变化量与 superplot**

- 检索词：配对图、paired、before after、前后对比、superplot、生物重复、技术重复、Bland-Altman、一致性。
- 实验问题：同一实验单位前后怎样变化，或两种测量方法是否一致？
- 所需数据：pair_id/subject_id、condition、value；superplot 另附 biological_unit/technical_replicate；一致性图需同对象的两种测量。
- 绘图入口：基础原始点/区间可原生；成对连线、差值图、Bland–Altman 走 custom Matplotlib。
- 接入步骤：按真实配对 ID 对齐数据；明确变化量或方法差值定义；连接配对点，另画独立单位层级的汇总区间。
- 复核重点：配对关系来自标识，不按行顺序假配对；技术重复不增加独立实验 n。
- 相关能力：FF-STATS-01、FF-PLOT-04、FF-CUSTOM-01；方法来源：S11、S13。

### SP-MODEL-EVAL

**模型评估、消融与解释**

- 检索词：消融、ablation、benchmark、模型对比、ROC、PR、calibration、校准曲线、特征重要性、feature importance、radar、雷达图。
- 实验问题：方法性能、阈值取舍、概率校准或组成模块的贡献如何比较？
- 所需数据：方法、数据分割、种子/折、指标；分类曲线有逐样本标签/得分；校准含分箱定义；重要性有分析方法与不确定性。
- 绘图入口：bar/ROC/PR/confusion/forest/Pareto 原生；校准、水平排序、多轴雷达和专门解释图走 custom Matplotlib。
- 接入步骤：用同评价口径组织输入；对已有指标画原生面板；校准/重要性由相应分析输出驱动；多指标优先可比较尺度与直接标签。
- 复核重点：保留随机水平或负结果；概率校准和区分度分别解释；雷达每轴方向、范围和单位显式。
- 相关能力：FF-PLOT-02、FF-PLOT-09、FF-PLOT-10、FF-PLOT-11、FF-PLOT-12、FF-PLOT-13、FF-CUSTOM-01；方法来源：S11、S15。

### SP-TIME-RESPONSE

**时域响应、验证与局部放大**

- 检索词：时域响应、time history、响应对比、validation、收敛曲线、learning curve、局部放大、inset、误差带、confidence band。
- 实验问题：实验、仿真或不同方法的响应和局部偏差如何随时间变化？
- 所需数据：time、response、method、run/subject；单位、采样时间和不确定性；局部区间/放大范围显式。
- 绘图入口：普通时序与分组区间原生 line；共享轴、inset、带连接标记的局部放大走 custom Matplotlib。
- 接入步骤：先画同时间基础的主图；用清楚的 inset 框和连接标记突出预先指定局部；多视图复用同一数据表和角色样式。
- 复核重点：保留时间缺口；局部放大显示实际坐标范围；数据处理与美化参数分开。
- 相关能力：FF-PLOT-01、FF-STATS-01、FF-CUSTOM-01、FF-COMPOSE-01；方法来源：S11、S15。

### SP-SPECTRUM-FRF

**频谱、功率谱与频响**

- 检索词：频谱、spectrum、FFT、PSD、功率谱、频响、FRF、frequency response、Bode、伯德图、谐波、harmonic。
- 实验问题：信号频率成分、功率分布或输入到输出的频率响应如何变化？
- 所需数据：已有 frequency、amplitude/PSD/FRF、phase；或原始输入/输出时序、采样率、窗口/段长、缩放规则、相位定义。
- 绘图入口：已有一维谱值可原生 line；FFT/PSD/FRF 估计和幅相组合、stem 谐波图走 custom Python/Matplotlib。
- 接入步骤：沿用现有信号分析；把计算参数和导出数值表保存；为幅值、功率密度、dB 或相位各自标清单位，再组织单图或共享频率的面板。
- 复核重点：幅值谱与功率谱单位不同；单/双边谱、窗函数和 dB 参考量有记录。
- 相关能力：FF-PLOT-01、FF-CUSTOM-01、FF-COMPOSE-01；方法来源：S15。

### SP-TIME-FREQUENCY

**时频、频率热图与参数场**

- 检索词：时频图、spectrogram、STFT、wavelet、小波、time frequency、频率热图、frequency map。
- 实验问题：频率能量或响应模式怎样随时间或扫描参数改变？
- 所需数据：时间/参数坐标、频率坐标、幅值或功率矩阵；STFT/小波参数、采样率、色标单位和参考量。
- 绘图入口：已有规则数值网格可原生 heatmap；非均匀网格和复杂轴/色条用 custom Matplotlib pcolormesh/contour。
- 接入步骤：从分析结果读取矩阵与轴坐标；选择矢量网格和共同色标；对色条显式关闭栅格化，记录窗口/边界策略。
- 复核重点：色块几何对应真正坐标单元；时间与频率分辨率来自分析设置。
- 相关能力：FF-PLOT-08、FF-CUSTOM-01、FF-SVG-01；方法来源：S11、S15。

### SP-PHASE-POINCARE

**相图与 Poincaré 截面**

- 检索词：相图、phase portrait、phase plot、Poincare、Poincaré、庞加莱、状态空间、state space。
- 实验问题：系统状态轨迹和按明确定义截面采样后的结构是什么？
- 所需数据：同步状态坐标 x、dx/dt 或 x/y，时间顺序；Poincaré 另附截面、穿越方向、采样/驱动相位和瞬态剔除规则。
- 绘图入口：已有二维点可原生 scatter；有序相轨迹、箭头和 Poincaré 组合走 custom Matplotlib。
- 接入步骤：从已记录的动力学分析输出取轨迹和截面点；以正确时间顺序连线；轨迹和截面标记分别图层，必要时配时域图。
- 复核重点：不能按 x 大小重排相轨迹；截面点来自定义，不以视觉密度抽点代替。
- 相关能力：FF-PLOT-03、FF-CUSTOM-01、FF-COMPOSE-01；方法来源：S15。

### SP-BIFURCATION-BASIN

**分岔与吸引域**

- 检索词：分岔图、bifurcation、吸引域、basin of attraction、稳定性、stability、参数扫描、parameter sweep。
- 实验问题：参数或初值如何对应稳定状态、周期变化和吸引子类别？
- 所需数据：参数值、状态采样、瞬态长度、正/反向扫描和初值；吸引域含初值网格、分类标签、积分与判定设置。
- 绘图入口：已计算分岔点可原生 scatter；分支/方向/吸引域组合走 custom Matplotlib；动力学求解在分析脚本中。
- 接入步骤：读取带参数/初值身份的模拟输出；分开画不同扫描方向或稳定性类别；将积分容差、采样窗口和分类判据写入 provenance。
- 复核重点：留住多稳态与未收敛分类；着色表达明确类别，不以“更平滑”重分类。
- 相关能力：FF-PLOT-03、FF-PLOT-08、FF-CUSTOM-01；方法来源：S15。

### SP-FIELD-SURFACE

**向量场、等高线与三维表面**

- 检索词：向量场、矢量场、vector field、quiver、streamplot、流线、等高线、contour、响应面、surface、wireframe、三维曲面。
- 实验问题：空间或参数场中的幅度、方向和表面形态怎样关联？
- 所需数据：坐标网格 X/Y(/Z)、标量或向量分量 U/V(/W)、单位；插值/网格来源、轴比例和矢量缩放。
- 绘图入口：规则标量矩阵可原生 heatmap；quiver/streamplot/contour/surface/wireframe 用 custom Matplotlib；几何场示意可用外部 TikZ。
- 接入步骤：保留完整坐标和向量单位；设置具有物理意义的箭头比例/参考箭头；用轮廓或线框表达三维，需要时加二维切片。
- 复核重点：区分真实场采样与示意箭头；图例明确归一化和缩放，颜色条保持矢量。
- 相关能力：FF-PLOT-08、FF-CUSTOM-01、FF-OPTION-TIKZ、FF-SVG-01；方法来源：S12、S15。

### SP-CIRCUIT

**电路与信号连接**

- 检索词：电路图、circuit、circuitikz、电阻、电容、运放、运算放大器、netlist、电气。
- 实验问题：电路元件、节点、电源及信号路径如何连接？
- 所需数据：元件 ID/类型/参数与单位、端口/netlist、接地、电流/电压参考方向、必要布局约束。
- 绘图入口：标准电气符号优先自定义 SVG 或外部 circuitikz；原生 diagram 适合高层功能框图。
- 接入步骤：先核对连接拓扑和端口，再布局符号；保留各元件可编辑 ID、文字与连线；TikZ 路线保存 .tex+参数并实际编译检查。
- 复核重点：交叉线与电连接节点有区别；端口、电源极性和元件数不随美化改变。
- 相关能力：FF-DIAGRAM-01、FF-OPTION-TIKZ、FF-SVG-01；方法来源：S12。

### SP-FORCE-GEOMETRY

**受力、机构与几何**

- 检索词：受力图、free body、force diagram、力学、机构、mechanism、几何示意、geometry、尺寸标注。
- 实验问题：对象几何、坐标、约束和作用力如何对应模型？
- 所需数据：对象身份/尺寸、参考系、接触/连接、力/力矩的施加点和方向、符号约定；示意比例单独说明。
- 绘图入口：简单关系用原生 diagram；精确几何、角度和尺寸标注用自定义 SVG/Matplotlib patches 或外部 TikZ。
- 接入步骤：定义坐标系与结构约束，先生成几何，再加受力/尺寸层；将共点、平行、层次和数量保存为合同约束。
- 复核重点：力的施加点、方向和作用对象不被排版移动改变；数值量与示意长度的关系明确。
- 相关能力：FF-DIAGRAM-01、FF-CUSTOM-01、FF-OPTION-TIKZ；方法来源：S12、S15。

### SP-CHEMISTRY

**分子、反应、能垒与晶格**

- 检索词：化学结构、molecule、molecular structure、分子结构、反应式、reaction、能垒、energy profile、晶格、lattice。
- 实验问题：结构、反应关系或已计算能量路径如何表达？
- 所需数据：明确结构/键级/电荷/立体信息、反应物/产物与条件；能量图需反应坐标与能量单位；晶格需晶胞与基矢。
- 绘图入口：自定义原生 SVG 或外部 TikZ/化学绘图工具；定量能量曲线可由原生 line 或 custom Matplotlib 绘制。
- 接入步骤：复用用户现有结构源；保留原子/键与条件标识；示意反应箭头和定量能量面板分工；交付结构源、可编辑 SVG 和导出命令。
- 复核重点：键级、电荷、立体关系和化学计量保持；能量曲线不为好看编造过渡态。
- 相关能力：FF-PLOT-01、FF-DIAGRAM-01、FF-CUSTOM-01、FF-OPTION-TIKZ；方法来源：S12。

### SP-BIOLOGY

**细胞、通路、基因与质粒**

- 检索词：生物结构、cell、细胞、signaling pathway、信号通路、gene map、基因图谱、plasmid、质粒、组织示意。
- 实验问题：生物对象的组成、方向、定位和证据支持的相互作用是什么？
- 所需数据：实体/定位/归属、关系类型/方向、gene/plasmid 坐标/方向/长度；实际成像保持独立原图和采集信息。
- 绘图入口：通路/机制关系可原生 diagram；基因/质粒精确几何用自定义 SVG/外部 TikZ；定量数据用原生图再拼版。
- 接入步骤：区分生物实体、物理区域和实验观测；按合同生成矢量几何；保持整体与局部 ID；基因/质粒用实际坐标生成段长和方向。
- 复核重点：示意实体计数和真实丰度区分；显微图源作为图像证据保留，不用矢量示意替换测量原图。
- 相关能力：FF-DIAGRAM-01、FF-COMPOSE-01、FF-OPTION-TIKZ；方法来源：S12、S16。

### SP-HARDWARE

**硬件层次、阵列、层叠与局部放大**

- 检索词：硬件、hardware、阵列、array、crossbar、交叉阵列、层叠、layer stack、剖面、cutaway、局部放大、whole detail、ownership。
- 实验问题：器件组成、层次归属、阵列计数与局部结构怎样对应？
- 所需数据：component_id、parent_id、layer/order、rows/columns/count、连接/端口、尺寸和状态；整体/局部使用同一逻辑 ID。
- 绘图入口：高层框图可原生 diagram；重复阵列、层叠/剖面与精确几何由自定义 SVG/Matplotlib patches 或外部 TikZ。
- 接入步骤：将逻辑对象和几何实例分开；程序生成重复组件并核对计数；放大图引用原对象 ID；层次边界和总线按语义绘制。
- 复核重点：绘制代表样本时同时登记真实总数与表示方式；层序、所有权、端口和锁定数字保持。
- 相关能力：FF-DIAGRAM-01、FF-COMPOSE-01、FF-CUSTOM-01、FF-OPTION-TIKZ；方法来源：S12、S16。

### SP-CS-MATH

**系统、自动机、树图与数学关系**

- 检索词：神经网络、neural network、系统架构、architecture、自动机、automaton、finite state、UML、ER图、Gantt、甘特、树图、tree、交换图、commutative diagram、Venn、数轴。
- 实验问题：计算对象的层次、状态变化、类型关系或数学映射是什么？
- 所需数据：稳定 node/edge ID、类型、方向、端口和分组；状态机含条件/转移；Gantt 含起止时间；数学关系含原始符号表达。
- 绘图入口：基础节点/反馈可原生 diagram；领域符号、状态自环、时间尺度及复杂数学几何用自定义 SVG/外部 TikZ。
- 接入步骤：先建立实体和关系合同，再按相同含义映射形状/线型；高级符号保留可编辑文字；时间图按实际日期或时长计算位置。
- 复核重点：一般框图不是自动满足 UML/ER 等领域语义；自环和条件转移按实际拓扑绘制；数学文字在最终 SVG 中检查编辑性。
- 相关能力：FF-DIAGRAM-01、FF-OPTION-TIKZ、FF-SVG-01；方法来源：S11、S12、S16。

### SP-PHYSICS

**光路、场论与物理示意**

- 检索词：光路图、ray optics、光学、optics、Feynman、费曼图、物理示意、physics schematic。
- 实验问题：射线、光学元件、粒子关系或物理过程如何按领域符号呈现？
- 所需数据：元件/粒子 ID、方向、介质/几何、连接、符号约定与关键量；真实定量数据另存。
- 绘图入口：自定义 SVG 或外部 TikZ 领域几何；定量曲线使用原生或 custom 数据图。
- 接入步骤：先核对领域对象和方向，再组合元件、路径、标签；保存参数化源和最终尺寸预览；有定量对照时作为独立数据面板。
- 复核重点：图形符号与科学约定对应；装饰箭头不增加不存在的相互作用。
- 相关能力：FF-DIAGRAM-01、FF-CUSTOM-01、FF-OPTION-TIKZ；方法来源：S12。

### SP-LAYOUT

**非对称多面板、摘要和方法主图**

- 检索词：多面板、multi panel、拼版、hero panel、非对称、asymmetric、graphical abstract、图形摘要、TOC、方法主图、schematic led。
- 实验问题：哪些面板共同回答同一问题，主叙事和辅助证据如何分配？
- 所需数据：每面板 question/role/data basis、原生 SVG、阅读顺序、最终尺寸、图注、标签与允许变化。
- 绘图入口：原生 SVG compose + diagram；特殊跨面板共享轴/insets 用 custom Matplotlib；图形摘要采用专门工作流。
- 接入步骤：按科学角色列面板清单；先出灰度几何骨架，再制作同内容的布局/样式候选；选中版本导出 SVG、预览和说明。
- 复核重点：数据面板 SVG 保留子元素；比较候选时同物理尺寸，标签/实体/边与锁定数值保持。
- 相关能力：FF-COMPOSE-01、FF-DIAGRAM-01、FF-CUSTOM-01；方法来源：S09、S11、S16。

### SP-REPORTING-FLOW

**CONSORT / PRISMA 的分支流程与计数**

- 检索词：CONSORT、PRISMA、招募流程、受试者流程、纳排流程、文献筛选、records、reports、studies、participant flow。
- 实验问题：受试者或文献证据经过哪些阶段，各阶段进入、退出和最终纳入的数量如何对应？
- 所需数据：阶段、稳定节点 ID、计数、计数单位、排除原因、分支关系及明细记录；PRISMA 还需 record→report→study 映射，CONSORT 按研究组记录参与者及分析口径。
- 绘图入口：原生 diagram 或自定义 SVG；project 的 quantities 保存数字，entities 的 quantity_ref 绑定节点计数，units 保存计数单位；复杂模板可沿用外部矢量编辑源。
- 接入步骤：先从实际登记/筛选表汇总每个阶段；核对同单位、互斥分支的加减关系；从项目 quantities 生成文字；审核来源、数字和边后渲染；把变体与基线关联。
- 复核重点：分支守恒只用于同单位和明确定义的互斥分类。record 是检索条目，report 是某研究的报告文件，study 是研究；多个 report 可以对应同一 study，应按映射分别计数。CONSORT 的停止干预、失访和排除分析按实际口径分别表达。
- 相关能力：FF-DIAGRAM-01、FF-PROJECT-01、FF-REVISION-01；该条为需求补充的领域工作流，方法依据见下面的官方来源。

以下是用于说明核对方式的**构造计数示例**：

~~~python
q = {
    "identified_records": 100, "duplicates_records": 20, "other_removed_records": 5,
    "screened_records": 75, "excluded_records": 60,
    "sought_reports": 15, "not_retrieved_reports": 3,
    "assessed_reports": 12, "excluded_reports": 4, "included_reports": 8,
    "included_studies": 6,
}
assert q["identified_records"] - q["duplicates_records"] - q["other_removed_records"] == q["screened_records"]
assert q["sought_reports"] - q["not_retrieved_reports"] == q["assessed_reports"]
assert q["assessed_reports"] - q["excluded_reports"] == q["included_reports"]
# Derive included_studies from the actual report-to-study map, not from
# an arithmetic subtraction of report counts.
~~~

这里的断言作为项目分析/核对脚本；project 保存、引用并比较 quantities，不自动推导完整的 CONSORT/PRISMA 研究流程。

按项目所用版本和研究设计读取 [PRISMA 官方流程图](https://www.prisma-statement.org/prisma-2020-flow-diagram)、[PRISMA 2020 的术语解释](https://pmc.ncbi.nlm.nih.gov/articles/PMC8005925/) 和 [CONSORT 2025 participant flow 的说明](https://www.consort-spirit.org/item-22a-randomized)。PRISMA 官方提供新综述/更新综述及检索来源不同的模板；CONSORT 流程按具体试验结构调整。此处记录的是绘图接入与计数核对流程。

## 四种接入方法

### N：使用原生图件命令

1. 先把已有分析输出组织为 plot-spec.md 对应的列。原始输入保留；中间表明确记录分析方法、单位和来源。
2. 在每个 panel 设置图种、列名和组别，使用项目的样式与角色映射。
3. 运行 plot，检查 manifest 的数值/来源信息与 SVG 标签，查看实际尺寸预览。
4. 多个已完成 SVG 用 compose 拼版。原生列名与选项以 plot-spec.md 为准；本表不添加未实现的 kind。

~~~bash
python <skill-dir>/scripts/figurefoundry.py plot --spec figure.json --out figures/result
~~~

### P：自定义 Matplotlib/Seaborn 科学图

1. 保留项目已有分析，或在明确的分析段生成需要的坐标/统计表。将数据处理与美化参数分开。
2. 根据条目建立领域图层：例如生存阶梯、雨云密度/点、Poincaré 截面、向量场或富集点图。
3. 将尺寸、字体层级、线宽、marker、图例、色条、网格和 inset 参数集中，复用项目语义样式。
4. 把完成的 Figure 交给 ff_export.export_figure。若使用 Seaborn figure-level 对象，传入它的 Matplotlib Figure。
5. 验证关键标签、坐标、数量和图层；检查灰度、实际尺寸和所需色觉预览。

~~~python
from ff_export import export_figure

# fig is the real Matplotlib Figure constructed from the project's analysis.
manifest = export_figure(
    fig,
    "figures/specialty",
    width_mm=180,
    height_mm=110,
    min_font_pt=6,
    expected_labels=["Time (s)", "Response (mV)"],
    provenance={"analysis": "analysis.py", "data_sha256": "actual input hash"},
)
~~~

文字使用普通可编辑文本；数学符号优先选择实际字体支持的 Unicode 标签，或用专门图源保留语义和文字编辑方案。所有数据 artist 与 colorbar 保持非栅格化。最终源文件、数据、参数和实际导出命令随图保存。

### V：自定义原生 SVG 几何

1. 从图件合同读取实体、关系、归属、数量、尺寸、文字和冻结值。
2. 为每个实体赋稳定 group ID；用 path/rect/ellipse/text 等原生元素生成可编辑几何。重复阵列通过参数循环生成，数量与合同核对。
3. 科学关系先决定连线和端口，布局再决定转折位置。整体与局部使用相同逻辑身份引用。
4. 输出完整 SVG 尺寸和 viewBox；记录完整关键标签；执行 audit，再查看实际尺寸预览。
5. 手工修改后更新图源/版本记录，保留选中 SVG 与可复现源的对应关系。

~~~bash
python <skill-dir>/scripts/figurefoundry.py audit figures/geometry.svg \
  --labels labels.json \
  --min-font-pt 6
~~~

具体命令参数以 figurefoundry.py audit --help 和 svg-contract.md 为准。基础节点图可直接调用 diagram；更复杂的力学、晶格、器件阵列或生物坐标图使用项目自定义几何源。

### E：延续外部 R / TikZ / 专业矢量工具

1. 读取 optional-backends.md，检查项目现有环境、文件格式和分析脚本。
2. R 保留 .R + 数据 + 分析输出；TikZ 保留 .tex、参数块、外部 CSV 及本次实际编译命令；专业编辑器保留原生编辑源。
3. 在当前项目中实际生成 SVG 和预览，记录工具版本与使用的字体。
4. 对导出的 SVG 使用相同的结构/标签/物理尺寸审核。检查文字是否仍为文字、密集层/色条是否仍为矢量，再做拼版或投稿格式转换。
5. 保存本次已执行的环境/命令/结果。此图谱不把依赖名称或安装检测写成成功运行的证明。

本图谱提供领域路由与接入步骤。R/TikZ/专业编辑器的工具链需在所用项目环境中按上述流程实际验证；本文件不宣称这些外部后端已在当前发布中完成运行测试。

## 扩展与快速定位

| 发现的不足 | 修改位置 | 需要补的证据 |
|---|---|---|
| 用户中英说法命不中图型 | 对应 SP 条目的 keywords 与 specialty 路由索引 | 一个真实措辞能命中正确 SP ID 的查询测试 |
| 能命中，但所需数据不明确 | 对应 SP 的所需数据/实验问题 | 最小输入表和字段含义 |
| 只有 custom 指引，希望成为原生命令 | 新领域脚本 + CLI/能力登记；SP 路由改为实际实现类别 | 已知数值答案、合法阴性/缺失输入、SVG 契约测试及实际预览 |
| 现成图不适配某期刊版式 | 项目样式、journal profile 与对应 source script | 实际 mm/字体/标签/图例的审核和预览 |
| 同一科学角色跨图发生漂移 | 项目 role mapping 与 style 引用 | 不同绘制/输入顺序下颜色、marker、线型保持一致 |
| 图件修改改变数量或结构 | 项目 contract 与 revision 记录 | style-only 修改通过；科学字段变更能被明确指出 |
| 需要新的 R/TikZ 后端 | optional-backends.md 的适用入口和实际适配模块 | 当前环境的真实编译/导出、SVG 审核及图源交付 |
| 需要追溯参考论文或数字化 benchmark | reference-intake.md / ff_reference.py | HTML 来源 SHA、图件证据和 benchmark 字段检查 |

一个 SP ID 保持稳定，可以随实现成熟从 custom 路由升级为原生。新增能力时保留实验问题、输入契约、方法来源、执行状态、代码落点和测试入口的对应关系，避免只增加图名。

## 方法来源

- [S11 的专业图型目录](https://github.com/TingxiYu/academic-figure-skill/blob/1df9940dd01ac939f072b12fe28d6353b79b90f9/references/directory-map.md)：中英检索词、语义匹配、复杂矩阵、单细胞和多种图件组合。
- [S12 的 TikZ 领域路由](https://github.com/PM-Shawn/tikz-scientific-figures/blob/0f0918c84db0b715bed476b1f607cd6e72cd35d4/SKILL.md)：电路、力学几何、生物、CS、化学、物理和数学的可复现矢量源。
- [S15 的中文图型表](https://github.com/FFFxueGawaine/sci-paper-plot-skill/blob/3404a006ed79695a20f6b31656b209b99a161f32/references/plot-type-map.zh-CN.md) 与 [通用图型 catalog](https://github.com/FFFxueGawaine/sci-paper-plot-skill/blob/3404a006ed79695a20f6b31656b209b99a161f32/references/common-plot-types-catalog.md)：时域/频域、FRF、时频、相图、Poincaré、分岔、吸引域、向量场及模型评估。
- S09/S13/S16 的构图、统计图和语义几何方法与以上路线互补；固定来源入口见仓库 docs/SOURCES.md。

本表统一来源方法和用户专业绘图需求。每条路线按本项目的数据与 SVG 契约完成具体图件。

