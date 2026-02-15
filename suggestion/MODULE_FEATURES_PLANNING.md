# Ginkgo各模块功能点详细规划

> 基于差距分析的功能模块规划文档
> 创建时间：2026-02-09

## 目录

- [一、回测模块功能规划](#一回测模块功能规划)
- [二、研究模块功能规划](#二研究模块功能规划)
- [三、策略验证模块功能规划](#三策略验证模块功能规划)
- [四、模拟盘模块功能规划](#四模拟盘模块功能规划)
- [五、实盘交易模块功能规划](#五实盘交易模块功能规划)
- [六、前端UI模块功能规划](#六前端ui模块功能规划)

---

## 一、回测模块功能规划

### 1.1 核心功能点（P0）

#### F1.1 回测结果可视化
**功能描述**：展示回测结果的图表和指标

**子功能点**：
- [ ] **F1.1.1** 净值曲线图
  - 显示策略净值随时间变化
  - 支持对比基准指数
  - 支持多策略对比
  - 技术要点：ECharts line chart，数据降采样

- [ ] **F1.1.2** 回撤曲线图
  - 显示策略回撤情况
  - 标记最大回撤点
  - 技术要点：area chart，负值处理

- [ ] **F1.1.3** 收益分布图
  - 日收益率分布直方图
  - 正态分布拟合对比
  - 技术要点：histogram，KDE曲线

- [ ] **F1.1.4** 仓位变化图
  - 持仓市值随时间变化
  - 现金占比变化
  - 技术要点：stacked area chart

- [ ] **F1.1.5** 绩效指标仪表盘
  - 总收益率、年化收益率
  - 夏普比率、最大回撤
  - 胜率、盈亏比
  - 技术要点：卡片布局，指标计算

#### F1.2 交易记录详情
**功能描述**：展示回测过程中的所有交易记录

**子功能点**：
- [ ] **F1.2.1** 订单记录表格
  - 订单编号、股票代码、方向
  - 下单时间、订单价格、订单数量
  - 订单状态、成交数量
  - 技术要点：虚拟滚动，导出CSV

- [ ] **F1.2.2** 成交记录表格
  - 成交编号、股票代码
  - 成交时间、成交价格、成交数量
  - 手续费、滑点
  - 技术要点：分页，筛选

- [ ] **F1.2.3** 持仓历史查询
  - 按时间查询历史持仓
  - 持仓成本、市值、盈亏
  - 技术要点：时间轴控件

- [ ] **F1.2.4** 交易统计
  - 交易次数、平均持仓天数
  - 单笔最大盈利/亏损
  - 技术要点：聚合统计

#### F1.3 分析器数据展示
**功能描述**：展示各类分析器的时序数据

**子功能点**：
- [ ] **F1.3.1** 通用时序图表
  - 支持任意分析器数据展示
  - 多分析器对比
  - 技术要点：动态图表，数据适配

- [ ] **F1.3.2** 自定义分析器配置
  - 选择要启用的分析器
  - 配置分析器参数
  - 技术要点：表单配置

### 1.2 扩展功能点（P1）

#### F1.4 回测报告导出
**功能描述**：生成并导出回测报告

**子功能点**：
- [ ] **F1.4.1** PDF报告生成
  - 包含所有图表和指标
  - 支持自定义封面和页眉
  - 技术要点：ReportLab/WeasyPrint

- [ ] **F1.4.2** Excel报告导出
  - 多sheet分别存放不同数据
  - 支持公式计算
  - 技术要点：openpyxl

- [ ] **F1.4.3** HTML报告
  - 交互式图表
  - 支持在线分享
  - 技术要点：Jinja2模板

- [ ] **F1.4.4** 报告模板管理
  - 保存自定义报告模板
  - 模板市场
  - 技术要点：模板引擎

#### F1.5 回测对比功能
**功能描述**：对比多个回测任务的结果

**子功能点**：
- [ ] **F1.5.1** 多回测选择
  - 批量选择回测任务
  - 保存对比方案
  - 技术要点：多选表格

- [ ] **F1.5.2** 指标对比表格
  - 并排展示关键指标
  - 高亮最优值
  - 技术要点：条件格式

- [ ] **F1.5.3** 曲线对比图
  - 同图展示多条净值曲线
  - 支持添加/删除曲线
  - 技术要点：多系列图表

- [ ] **F1.5.4** 对比报告生成
  - 生成对比分析报告
  - 差异显著性检验
  - 技术要点：统计检验

### 1.3 高级功能点（P2）

#### F1.6 回测配置模板
**功能描述**：保存和复用回测配置

**子功能点**：
- [ ] **F1.6.1** 模板创建
  - 保存当前配置为模板
  - 模板命名和分类
  - 技术要点：配置序列化

- [ ] **F1.6.2** 模板管理
  - 模板列表和搜索
  - 模板编辑和删除
  - 技术要点：CRUD

- [ ] **F1.6.3** 一键应用模板
  - 从模板创建回测
  - 模板参数微调
  - 技术要点：表单预填充

#### F1.7 实时日志查看
**功能描述**：查看回测过程的详细日志

**子功能点**：
- [ ] **F1.7.1** 实时日志流
  - SSE推送日志
  - 日志级别筛选
  - 技术要点：SSE，日志缓冲

- [ ] **F1.7.2** 日志搜索
  - 关键词搜索
  - 正则表达式搜索
  - 技术要点：全文搜索

- [ ] **F1.7.3** 日志下载
  - 下载完整日志文件
  - 按时间范围导出
  - 技术要点：文件流

### 1.4 API接口设计

```python
# /home/kaoru/Ginkgo/apiserver/api/backtests.py

# 结果相关
GET    /v1/backtests/{uuid}/result/summary          # 获取结果摘要
GET    /v1/backtests/{uuid}/result/charts           # 获取图表数据
GET    /v1/backtests/{uuid}/analyzers               # 获取分析器列表
GET    /v1/backtests/{uuid}/analyzers/{name}/data   # 获取分析器数据

# 交易记录
GET    /v1/backtests/{uuid}/orders                  # 获取订单记录
GET    /v1/backtests/{uuid}/fills                   # 获取成交记录
GET    /v1/backtests/{uuid}/positions               # 获取持仓历史
GET    /v1/backtests/{uuid}/trades/statistics       # 获取交易统计

# 报告导出
GET    /v1/backtests/{uuid}/report                  # 导出报告
       ?format=pdf|excel|html

# 对比功能
POST   /v1/backtests/compare                        # 创建对比任务
GET    /v1/backtests/compare/{session_id}           # 获取对比结果

# 模板管理
GET    /v1/backtests/templates                      # 获取模板列表
POST   /v1/backtests/templates                      # 创建模板
GET    /v1/backtests/templates/{id}                 # 获取模板详情
PUT    /v1/backtests/templates/{id}                 # 更新模板
DELETE /v1/backtests/templates/{id}                 # 删除模板

# 日志查看
GET    /v1/backtests/{uuid}/logs/stream             # SSE日志流
GET    /v1/backtests/{uuid}/logs                    # 获取历史日志
```

### 1.5 前端组件设计

```typescript
// /home/kaoru/Ginkgo/web-ui/src/views/Backtest/
├── BacktestDetail.vue              // 回测详情主页
├── BacktestReport.vue              // 报告页面
├── BacktestCompare.vue             // 对比页面
├── BacktestLogs.vue                // 日志页面
└── components/
    ├── ResultOverview.vue          // 结果概览
    ├── PerformanceMetrics.vue      // 绩效指标
    └── TemplateManager.vue         // 模板管理

// /home/kaoru/Ginkgo/web-ui/src/components/charts/backtest/
├── NetValueChart.vue               // 净值曲线
├── DrawdownChart.vue               // 回撤曲线
├── ReturnDistribution.vue          // 收益分布
├── PositionChart.vue               // 仓位变化
└── TradeMarker.vue                 // 交易标记
```

---

## 二、研究模块功能规划

### 2.1 核心功能点（P0）

#### F2.1 因子IC分析
**功能描述**：计算因子的IC、RankIC等有效性指标

**子功能点**：
- [ ] **F2.1.1** IC时序计算
  - 计算每日IC值
  - 支持多周期IC（1日/5日/10日/20日）
  - 技术要点：DataFrame相关性计算

- [ ] **F2.1.2** RankIC计算
  - 计算秩相关系数
  - 技术要点：scipy.stats.spearmanr

- [ ] **F2.1.3** IC统计指标
  - IC均值、IC标准差
  - ICIR（IC均值/IC标准差）
  - t统计量（IC显著性检验）
  - 技术要点：统计计算

- [ ] **F2.1.4** IC可视化
  - IC时序图
  - IC分布直方图
  - IC热力图（因子×周期）
  - 技术要点：ECharts热力图

#### F2.2 因子分层回测
**功能描述**：按因子值分档回测，检验因子单调性

**子功能点**：
- [ ] **F2.2.1** 分层设置
  - 选择分层数量（3/5/10层）
  - 选择分层方法（等权/等股/等值）
  - 技术要点：pandas.qcut/pandas.cut

- [ ] **F2.2.2** 分层回测执行
  - 每层独立回测
  - 计算各层收益
  - 技术要点：批量回测

- [ ] **F2.2.3** 分层结果展示
  - 各层净值曲线对比
  - 各层收益统计表格
  - 多空收益曲线（顶层-底层）
  - 技术要点：多系列图表

- [ ] **F2.2.4** 单调性检验
  - 计算单调性相关系数
  - 判断因子是否单调
  - 技术要点：相关性检验

#### F2.3 因子查看器
**功能描述**：查看和分析因子数据

**子功能点**：
- [ ] **F2.3.1** 因子列表
  - 显示所有可用因子
  - 因子分类（技术/基本面/量价）
  - 技术要点：表格展示

- [ ] **F2.3.2** 因子详情
  - 因子描述和计算公式
  - 因子统计特征（均值/标准度/偏度/峰度）
  - 技术要点：描述性统计

- [ ] **F2.3.3** 因子值查询
  - 按股票代码查询因子值
  - 按日期查询因子值
  - 技术要点：ClickHouse查询

- [ ] **F2.3.4** 因子分布可视化
  - 因子值分布直方图
  - 因子值随时间变化
  - 技术要点：图表展示

### 2.2 扩展功能点（P1）

#### F2.4 因子正交化
**功能描述**：去除因子间的多重共线性

**子功能点**：
- [ ] **F2.4.1** 相关性分析
  - 计算因子间相关系数矩阵
  - 识别高相关因子对
  - 技术要点：相关性矩阵

- [ ] **F2.4.2** 正交化方法
  - Gram-Schmidt正交化
  - 残差正交化（回归取残差）
  - PCA主成分提取
  - 技术要点：线性代数计算

- [ ] **F2.4.3** 正交化结果对比
  - 正交化前后IC对比
  - 正交化后因子独立性验证
  - 技术要点：对比分析

#### F2.5 因子衰减分析
**功能描述**：分析因子预测能力随持有期的衰减

**子功能点**：
- [ ] **F2.5.1** 衰减曲线计算
  - 计算不同持有期的IC值
  - 拟合衰减曲线
  - 技术要点：时间序列分析

- [ ] **F2.5.2** 半衰期计算
  - 计算因子半衰期
  - 预测因子有效期
  - 技术要点：曲线拟合

- [ ] **F2.5.3** 衰减可视化
  - IC衰减曲线图
  - 各因子衰减对比
  - 技术要点：折线图

#### F2.6 因子换手率分析
**功能描述**：评估因子组合的稳定性

**子功能点**：
- [ ] **F2.6.1** 换手率计算
  - 计算因子权重换手率
  - 计算个股换手率
  - 技术要点：换手率公式

- [ ] **F2.6.2** 换手率分析
  - 换手率时序图
  - 换手率与收益关系
  - 技术要点：相关性分析

- [ ] **F2.6.3** 换手率优化
  - 设置换手率约束
  - 优化因子权重
  - 技术要点：优化算法

#### F2.7 因子对比工具
**功能描述**：对比多个因子的有效性

**子功能点**：
- [ ] **F2.7.1** 因子IC对比
  - 多因子IC时序对比
  - IC统计指标对比表格
  - 技术要点：多系列图表

- [ ] **F2.7.2** 因子分层对比
  - 多因子分层收益对比
  - 多空收益对比
  - 技术要点：对比分析

- [ ] **F2.7.3** 因子综合评分
  - 综合IC、IR、单调性等指标
  - 因子打分排序
  - 技术要点：综合评分算法

### 2.3 高级功能点（P2）

#### F2.8 因子组合构建
**功能描述**：基于多个因子构建组合

**子功能点**：
- [ ] **F2.8.1** 因子选择
  - 选择组合使用的因子
  - 设置因子权重
  - 技术要点：多选控件

- [ ] **F2.8.2** 组合构建方法
  - 等权组合
  - IC加权组合
  - 风险平价组合
  - 技术要点：组合优化

- [ ] **F2.8.3** 组合回测
  - 基于因子组合进行回测
  - 评估组合效果
  - 技术要点：回测集成

- [ ] **F2.8.4** 组合优化
  - 优化因子权重
  - 约束条件设置
  - 技术要点：优化求解器

#### F2.9 因子挖掘
**功能描述**：自动发现新的有效因子

**子功能点**：
- [ ] **F2.9.1** 因子表达式生成
  - 基于基础因子组合生成表达式
  - 遗传编程生成因子
  - 技术要点：遗传算法

- [ ] **F2.9.2** 因子筛选
  - 自动计算IC等指标
  - 筛选有效因子
  - 技术要点：批量计算

- [ ] **F2.9.3** 因子去重
  - 识别相似因子
  - 保留最优因子
  - 技术要点：相似度计算

### 2.4 API接口设计

```python
# /home/kaoru/Ginkgo/apiserver/api/factor_analysis.py

# IC分析
POST   /v1/factors/analysis/ic                            # IC分析
GET    /v1/factors/{factor_name}/ic/summary              # IC摘要
GET    /v1/factors/{factor_name}/ic/timeseries           # IC时序数据

# 分层回测
POST   /v1/factors/analysis/layering                     # 分层回测
GET    /v1/factors/analysis/layering/{task_id}           # 获取分层结果

# 因子查询
GET    /v1/factors                                       # 因子列表
GET    /v1/factors/{factor_name}                         # 因子详情
GET    /v1/factors/{factor_name}/data                    # 因子数据
       ?code=xxx&date=xxx

# 正交化
POST   /v1/factors/orthogonalize                         # 因子正交化
GET    /v1/factors/correlation_matrix                    # 相关性矩阵

# 衰减分析
GET    /v1/factors/{factor_name}/decay                   # 衰减分析
       ?max_lag=20

# 换手率
GET    /v1/factors/{factor_name}/turnover                # 换手率分析

# 因子对比
POST   /v1/factors/compare                               # 因子对比

# 因子组合
POST   /v1/factors/portfolio/build                       # 构建因子组合
POST   /v1/factors/portfolio/optimize                    # 优化因子组合
```

### 2.5 前端组件设计

```typescript
// /home/kaoru/Ginkgo/web-ui/src/views/Research/
├── FactorViewer.vue                 // 因子查看器
├── ICAnalysis.vue                   // IC分析
├── LayeringBacktest.vue             // 分层回测
├── FactorComparison.vue             // 因子对比
├── FactorOrthogonalization.vue      // 因子正交化
├── FactorDecay.vue                  // 衰减分析
├── FactorTurnover.vue               // 换手率分析
├── PortfolioBuilder.vue             // 因子组合构建
└── FactorMiner.vue                  // 因子挖掘

// /home/kaoru/Ginkgo/web-ui/src/components/charts/factor/
├── FactorDistribution.vue           // 因子分布
├── ICTimeSeries.vue                 // IC时序图
├── ICHeatmap.vue                    // IC热力图
├── LayeringReturnChart.vue          // 分层收益图
├── DecayCurve.vue                   // 衰减曲线
└── CorrelationMatrix.vue            // 相关性矩阵
```

---

## 三、策略验证模块功能规划

### 3.1 核心功能点（P0）

#### F3.1 参数优化
**功能描述**：寻找策略最优参数

**子功能点**：
- [ ] **F3.1.1** 网格搜索
  - 设置参数网格
  - 遍历所有参数组合
  - 技术要点：itertools.product

- [ ] **F3.1.2** 优化结果展示
  - 参数组合与收益热力图
  - 最优参数组合高亮
  - 技术要点：热力图

- [ ] **F3.1.3** 参数敏感性分析
  - 单参数敏感性曲线
  - 参数交互效应分析
  - 技术要点：敏感性分析

#### F3.2 样本外测试
**功能描述**：验证策略的泛化能力

**子功能点**：
- [ ] **F3.2.1** 走步验证
  - 设置训练期和测试期长度
  - 滚动验证
  - 技术要点：时间序列分割

- [ ] **F3.2.2** 交叉验证
  - 时间序列交叉验证
  - K折验证
  - 技术要点：交叉验证

- [ ] **F3.2.3** 样本内外对比
  - 样本内外收益对比
  - 过拟合检测
  - 技术要点：对比分析

### 3.2 扩展功能点（P1）

#### F3.3 蒙特卡洛模拟
**功能描述**：评估策略的随机性

**子功能点**：
- [ ] **F3.3.1** 收益分布模拟
  - 自举法模拟收益分布
  - 置信区间计算
  - 技术要点：bootstrap

- [ ] **F3.3.2** 参数不确定性
  - 参数扰动模拟
  - 策略鲁棒性评估
  - 技术要点：蒙特卡洛模拟

- [ ] **F3.3.3** 极端情景模拟
  - 压力测试
  - 最坏情况分析
  - 技术要点：情景分析

#### F3.4 稳定性检验
**功能描述**：检验策略在不同市场环境下的表现

**子功能点**：
- [ ] **F3.4.1** 牛熊市表现对比
  - 识别牛熊市阶段
  - 对比不同市场表现
  - 技术要点：市场分类

- [ ] **F3.4.2** 滚动窗口分析
  - 滚动计算策略指标
  - 评估策略稳定性
  - 技术要点：滚动窗口

- [ ] **F3.4.3** 子周期分析
  - 按年/季度/月度分析
  - 识别策略失效期
  - 技术要点：子周期统计

### 3.3 API接口设计

```python
# /home/kaoru/Ginkgo/apiserver/api/validation.py

# 参数优化
POST   /v1/validation/optimization/grid                  # 网格搜索
POST   /v1/validation/optimization/genetic               # 遗传算法
POST   /v1/validation/optimization/bayesian              # 贝叶斯优化
GET    /v1/validation/optimization/{task_id}             # 获取优化结果

# 样本外测试
POST   /v1/validation/out-of-sample/walk-forward         # 走步验证
POST   /v1/validation/out-of-sample/cross-validation     # 交叉验证
GET    /v1/validation/out-of-sample/{task_id}/report     # 获取测试报告

# 蒙特卡洛
POST   /v1/validation/monte-carlo/bootstrap              # 自举模拟
POST   /v1/validation/monte-carlo/scenario               # 情景模拟
GET    /v1/validation/monte-carlo/{task_id}/distribution # 获取分布

# 稳定性检验
POST   /v1/validation/stability/rolling                  # 滚动窗口分析
POST   /v1/validation/stability/sub-period               # 子周期分析
GET    /v1/validation/stability/{task_id}/report         # 获取稳定性报告
```

---

## 四、模拟盘模块功能规划

### 4.1 核心功能点（P0）

#### F4.1 模拟账户管理
**功能描述**：管理模拟盘账户资金和持仓

**子功能点**：
- [ ] **F4.1.1** 账户创建
  - 设置初始资金
  - 设置账户类型（股票/期货/混合）
  - 技术要点：账户模型

- [ ] **F4.1.2** 资金管理
  - 可用资金查询
  - 冻结资金管理
  - 资金流水记录
  - 技术要点：资金流水

- [ ] **F4.1.3** 持仓管理
  - 实时持仓查询
  - 持仓成本计算
  - 持仓盈亏统计
  - 技术要点：持仓计算

#### F4.2 订单簿模拟
**功能描述**：模拟真实的订单簿撮合

**子功能点**：
- [ ] **F4.2.1** Level-2行情模拟
  - 维护买卖五档
  - 订单队列管理
  - 技术要点：订单簿数据结构

- [ ] **F4.2.2** 撮合算法
  - 价格优先、时间优先
  - 部分成交处理
  - 技术要点：撮合算法

- [ ] **F4.2.3** 滑点模型
  - 订单簿深度滑点
  - 大单冲击成本
  - 技术要点：滑点计算

#### F4.3 历史行情回放
**功能描述**：回放历史行情数据

**子功能点**：
- [ ] **F4.3.1** 回放控制
  - 开始/暂停/恢复
  - 回放速度控制
  - 技术要点：定时器控制

- [ ] **F4.3.2** 时间跳转
  - 跳转到指定日期
  - 快进/快退
  - 技术要点：数据索引

- [ ] **F4.3.3** 回放状态
  - 当前回放时间
  - 剩余数据量
  - 技术要点：状态管理

#### F4.4 交易限制模拟
**功能描述**：模拟真实交易的限制

**子功能点**：
- [ ] **F4.4.1** T+1限制
  - 当日买入次日才能卖出
  - 技术要点：T+1检查

- [ ] **F4.4.2** 涨跌停限制
  - 涨跌停价格计算
  - 涨跌停无法交易
  - 技术要点：涨跌停计算

- [ ] **F4.4.3** 交易时间限制
  - 仅在交易时间段接受订单
  - 技术要点：交易时间检查

### 4.2 扩展功能点（P1）

#### F4.5 模拟风控
**功能描述**：模拟盘的风控执行

**子功能点**：
- [ ] **F4.5.1** 实时风控检查
  - 仓位限制检查
  - 止损止盈检查
  - 技术要点：实时计算

- [ ] **F4.5.2** 风控日志
  - 风控触发记录
  - 风控操作日志
  - 技术要点：日志记录

- [ ] **F4.5.3** 风控统计
  - 风控触发次数
  - 风控效果评估
  - 技术要点：统计分析

#### F4.6 模拟报告
**功能描述**：生成模拟盘报告

**子功能点**：
- [ ] **F4.6.1** 每日报告
  - 每日收益汇总
  - 每日交易总结
  - 技术要点：日报生成

- [ ] **F4.6.2** 周报/月报
  - 阶段性收益统计
  - 阶段性交易分析
  - 技术要点：周期报告

- [ ] **F4.6.3** 模拟vs实盘对比
  - 滑点对比
  - 成交率对比
  - 技术要点：对比分析

### 4.3 API接口设计

```python
# /home/kaoru/Ginkgo/apiserver/api/paper_trading.py

# 账户管理
GET    /v1/paper-trading/accounts                       # 账户列表
POST   /v1/paper-trading/accounts                       # 创建账户
GET    /v1/paper-trading/accounts/{id}                  # 账户详情
PUT    /v1/paper-trading/accounts/{id}                  # 更新账户

# 模拟盘控制
POST   /v1/paper-trading/{account_id}/start             # 启动模拟盘
POST   /v1/paper-trading/{account_id}/stop              # 停止模拟盘
GET    /v1/paper-trading/{account_id}/status            # 获取状态

# 历史回放
POST   /v1/paper-trading/replay/start                   # 开始回放
POST   /v1/paper-trading/replay/pause                   # 暂停回放
POST   /v1/paper-trading/replay/seek                    # 跳转时间
GET    /v1/paper-trading/replay/status                  # 回放状态

# 查询接口
GET    /v1/paper-trading/{account_id}/positions         # 持仓查询
GET    /v1/paper-trading/{account_id}/orders            # 订单查询
GET    /v1/paper-trading/{account_id}/capital           # 资金查询
GET    /v1/paper-trading/{account_id}/pnls              # 盈亏查询

# 报告
GET    /v1/paper-trading/{account_id}/report/daily      # 日报
GET    /v1/paper-trading/{account_id}/report/period     # 周期报告
```

---

## 五、实盘交易模块功能规划

### 5.1 核心功能点（P0）

#### F5.1 券商接口
**功能描述**：与券商系统对接

**子功能点**：
- [ ] **F5.1.1** 连接管理
  - 建立连接
  - 断线重连
  - 心跳检测
  - 技术要点：连接管理

- [ ] **F5.1.2** 订单操作
  - 下单
  - 撤单
  - 改单（查询后撤单重下）
  - 技术要点：订单API

- [ ] **F5.1.3** 查询操作
  - 查询资金
  - 查询持仓
  - 查询委托
  - 查询成交
  - 技术要点：查询API

- [ ] **F5.1.4** 行情订阅
  - 订阅实时行情
  - 行情推送处理
  - 技术要点：行情API

#### F5.2 订单状态机
**功能描述**：管理订单生命周期

**子功能点**：
- [ ] **F5.2.1** 状态定义
  - PENDING（待发送）
  - SUBMITTED（已报送）
  - PARTIAL_FILLED（部分成交）
  - FILLED（全部成交）
  - CANCELLED（已撤销）
  - REJECTED（已拒绝）
  - 技术要点：状态机

- [ ] **F5.2.2** 状态转换
  - 定义合法状态转换
  - 状态转换触发
  - 技术要点：状态转换

- [ ] **F5.2.3** 状态通知
  - 状态变化推送
  - WebSocket实时通知
  - 技术要点：WebSocket

#### F5.3 实时持仓同步
**功能描述**：保持本地持仓与券商一致

**子功能点**：
- [ ] **F5.3.1** 定时同步
  - 定时从券商查询持仓
  - 对比本地持仓
  - 技术要点：定时任务

- [ ] **F5.3.2** 差异处理
  - 识别持仓差异
  - 差异报警
  - 技术要点：差异检测

- [ ] **F5.3.3** 事件驱动同步
  - 成交回报触发更新
  - 减少查询频率
  - 技术要点：事件驱动

#### F5.4 实时风控监控
**功能描述**：实时监控风险指标

**子功能点**：
- [ ] **F5.4.1** 仓位监控
  - 实时计算总仓位
  - 单股仓位监控
  - 技术要点：实时计算

- [ ] **F5.4.2** 盈亏监控
  - 实时盈亏计算
  - 累计盈亏监控
  - 技术要点：盈亏计算

- [ ] **F5.4.3** 风险预警
  - 超过阈值预警
  - 短信/邮件通知
  - 技术要点：预警系统

- [ ] **F5.4.4** 熔断机制
  - 触发熔断停止交易
  - 自动平仓
  - 技术要点：熔断逻辑

### 5.2 扩展功能点（P1）

#### F5.5 实盘监控仪表盘
**功能描述**：实时监控实盘状态

**子功能点**：
- [ ] **F5.5.1** 账户概览
  - 总资产、可用资金
  - 持仓市值、浮动盈亏
  - 技术要点：仪表盘

- [ ] **F5.5.2** 实时持仓
  - 持仓列表
  - 实时盈亏更新
  - 技术要点：实时更新

- [ ] **F5.5.3** 活跃订单
  - 活跃订单列表
  - 订单状态实时更新
  - 技术要点：实时列表

- [ ] **F5.5.4** 成交记录
  - 当日成交记录
  - 成交明细
  - 技术要点：成交记录

#### F5.6 交易日志
**功能描述**：记录所有交易操作

**子功能点**：
- [ ] **F5.6.1** 策略日志
  - 策略信号记录
  - 策略决策日志
  - 技术要点：日志记录

- [ ] **F5.6.2** 订单日志
  - 订单生命周期日志
  - 订单状态变化
  - 技术要点：订单日志

- [ ] **F5.6.3** 系统日志
  - 系统错误日志
  - 性能日志
  - 技术要点：系统日志

#### F5.7 异常处理
**功能描述**：处理各类异常情况

**子功能点**：
- [ ] **F5.7.1** 连接异常
  - 断线检测
  - 自动重连
  - 技术要点：异常处理

- [ ] **F5.7.2** 订单异常
  - 订单拒绝处理
  - 订单超时处理
  - 技术要点：订单异常

- [ ] **F5.7.3** 行情异常
  - 行情中断处理
  - 异常行情检测
  - 技术要点：行情异常

- [ ] **F5.7.4** 资金异常
  - 资金不足处理
  - 持仓异常处理
  - 技术要点：资金异常

### 5.3 API接口设计

```python
# /home/kaoru/Ginkgo/apiserver/api/live_trading.py

# 实盘账户
GET    /v1/live-trading/accounts                         # 实盘账户列表
GET    /v1/live-trading/accounts/{id}                    # 账户详情
POST   /v1/live-trading/accounts/{id}/connect            # 连接券商
POST   /v1/live-trading/accounts/{id}/disconnect         # 断开连接

# 策略管理
POST   /v1/live-trading/{account_id}/strategies/start    # 启动策略
POST   /v1/live-trading/{account_id}/strategies/stop     # 停止策略
GET    /v1/live-trading/{account_id}/strategies          # 策略列表

# 实时数据
GET    /v1/live-trading/{account_id}/positions           # 实时持仓
GET    /v1/live-trading/{account_id}/active-orders       # 活跃订单
GET    /v1/live-trading/{account_id}/capital             # 资金信息
GET    /v1/live-trading/{account_id}/fills               # 成交记录

# WebSocket
WS     /v1/live-trading/{account_id}/stream              # 实时数据流

# 风控
GET    /v1/live-trading/{account_id}/risk/status         # 风险状态
POST   /v1/live-trading/{account_id}/risk/circuit-breaker# 触发熔断

# 日志
GET    /v1/live-trading/{account_id}/logs/strategy       # 策略日志
GET    /v1/live-trading/{account_id}/logs/order          # 订单日志
GET    /v1/live-trading/{account_id}/logs/system         # 系统日志
```

---

## 六、前端UI模块功能规划

### 6.1 核心功能点（P0）

#### F6.1 仪表盘重构
**功能描述**：系统总览仪表盘

**子功能点**：
- [ ] **F6.1.1** 系统状态卡片
  - Worker状态
  - 数据更新时间
  - 运行任务数
  - 技术要点：状态卡片

- [ ] **F6.1.2** 快捷操作
  - 创建回测
  - 启动模拟盘
  - 查看持仓
  - 技术要点：快捷入口

- [ ] **F6.1.3** 关键指标
  - 总收益（所有实盘账户）
  - 今日盈亏
  - 运行中策略数
  - 技术要点：指标卡片

#### F6.2 图表组件库
**功能描述**：通用图表组件

**子功能点**：
- [ ] **F6.2.1** 基础图表
  - 折线图
  - 柱状图
  - 饼图
  - 技术要点：ECharts封装

- [ ] **F6.2.2** 金融图表
  - K线图
  - 分时图
  - 技术指标图
  - 技术要点：LightweightCharts

- [ ] **F6.2.3** 交互功能
  - 缩放
  - 数据缩放
  - tooltip
  - 图例开关
  - 技术要点：交互配置

#### F6.3 数据表格组件
**功能描述**：通用数据表格

**子功能点**：
- [ ] **F6.3.1** 基础功能
  - 排序
  - 筛选
  - 分页
  - 技术要点：表格组件

- [ ] **F6.3.2** 高级功能
  - 虚拟滚动
  - 列配置
  - 导出
  - 技术要点：表格增强

#### F6.4 实时通信
**功能描述**：前后端实时通信

**子功能点**：
- [ ] **F6.4.1** WebSocket连接
  - 自动连接
  - 断线重连
  - 心跳检测
  - 技术要点：WebSocket封装

- [ ] **F6.4.2** SSE订阅
  - 事件订阅
  - 自动重连
  - 技术要点：SSE封装

- [ ] **F6.4.3** 消息处理
  - 消息分发
  - 消息缓存
  - 技术要点：消息队列

### 6.2 扩展功能点（P1）

#### F6.5 表单组件库
**功能描述**：复杂表单组件

**子功能点**：
- [ ] **F6.5.1** 动态表单
  - 字段动态显示/隐藏
  - 字段联动
  - 技术要点：动态表单

- [ ] **F6.5.2** 表单验证
  - 实时验证
  - 自定义验证规则
  - 技术要点：表单验证

- [ ] **F6.5.3** 表单模板
  - 保存表单配置
  - 加载表单模板
  - 技术要点：模板系统

#### F6.6 数据可视化增强
**功能描述**：高级可视化功能

**子功能点**：
- [ ] **F6.6.1** 热力图
  - 相关性矩阵
  - IC热力图
  - 技术要点：ECharts热力图

- [ ] **F6.6.2** 树图
  - 持仓分布
  - 板块分布
  - 技术要点：ECharts树图

- [ ] **F6.6.3** 力导向图
  - 因子关系图
  - 技术要点：ECharts关系图

#### F6.7 用户体验优化
**功能描述**：提升用户体验

**子功能点**：
- [ ] **F6.7.1** 加载状态
  - 骨架屏
  - 进度条
  - 技术要点：加载优化

- [ ] **F6.7.2** 错误处理
  - 错误边界
  - 友好错误提示
  - 技术要点：错误处理

- [ ] **F6.7.3** 快捷键
  - 常用操作快捷键
  - 快捷键提示
  - 技术要点：快捷键

### 6.3 前端页面结构

```
web-ui/src/
├── views/
│   ├── Dashboard/
│   │   └── Dashboard.vue                    # 仪表盘
│   ├── Backtest/
│   │   ├── BacktestList.vue                 # 回测列表
│   │   ├── BacktestCreate.vue               # 创建回测
│   │   ├── BacktestDetail.vue               # 回测详情
│   │   ├── BacktestReport.vue               # 回测报告
│   │   ├── BacktestCompare.vue              # 回测对比
│   │   └── BacktestLogs.vue                 # 回测日志
│   ├── Research/
│   │   ├── FactorViewer.vue                 # 因子查看器
│   │   ├── ICAnalysis.vue                   # IC分析
│   │   ├── LayeringBacktest.vue             # 分层回测
│   │   ├── FactorComparison.vue             # 因子对比
│   │   ├── FactorOrthogonalization.vue      # 因子正交化
│   │   ├── FactorDecay.vue                  # 衰减分析
│   │   ├── FactorTurnover.vue               # 换手率分析
│   │   ├── PortfolioBuilder.vue             # 因子组合
│   │   ├── ParameterOptimizer.vue           # 参数优化
│   │   └── OutOfSampleTest.vue              # 样本外测试
│   ├── Trading/
│   │   ├── PaperTrading.vue                 # 模拟盘
│   │   ├── PaperTradingConfig.vue           # 模拟盘配置
│   │   ├── PaperTradingMonitor.vue          # 模拟盘监控
│   │   ├── LiveTrading.vue                  # 实盘
│   │   ├── OrderManagement.vue              # 订单管理
│   │   ├── RiskControl.vue                  # 风控管理
│   │   └── TradingLog.vue                   # 交易日志
│   ├── Portfolio/
│   │   ├── PortfolioList.vue                # 组合列表
│   │   ├── PortfolioDetail.vue              # 组合详情
│   │   └── PortfolioEditor.vue              # 组合编辑
│   ├── Data/
│   │   ├── DataView.vue                     # 数据查看
│   │   ├── StockInfo.vue                    # 股票信息
│   │   ├── KLineViewer.vue                  # K线查看
│   │   └── TickViewer.vue                   # Tick查看
│   └── Components/
│       ├── ComponentList.vue                # 组件列表
│       ├── ComponentDetail.vue              # 组件详情
│       └── ComponentEditor.vue              # 组件编辑
│
├── components/
│   ├── charts/
│   │   ├── common/
│   │   │   ├── LineChart.vue                # 折线图
│   │   │   ├── BarChart.vue                 # 柱状图
│   │   │   ├── PieChart.vue                 # 饼图
│   │   │   └── AreaChart.vue                # 面积图
│   │   ├── backtest/
│   │   │   ├── NetValueChart.vue            # 净值曲线
│   │   │   ├── DrawdownChart.vue            # 回撤曲线
│   │   │   ├── ReturnDistribution.vue       # 收益分布
│   │   │   └── PositionChart.vue            # 仓位变化
│   │   ├── factor/
│   │   │   ├── FactorDistribution.vue       # 因子分布
│   │   │   ├── ICTimeSeries.vue             # IC时序图
│   │   │   ├── ICHeatmap.vue                # IC热力图
│   │   │   ├── LayeringReturnChart.vue      # 分层收益
│   │   │   └── CorrelationMatrix.vue        # 相关性矩阵
│   │   └── trading/
│   │       ├── PositionPnLChart.vue         # 持仓盈亏
│   │       ├── RealtimeChart.vue            # 实时行情
│   │       └── OrderFlowChart.vue           # 订单流
│   ├── tables/
│   │   ├── DataTable.vue                    # 数据表格
│   │   ├── VirtualTable.vue                 # 虚拟滚动表格
│   │   └── EditableTable.vue                # 可编辑表格
│   ├── forms/
│   │   ├── DynamicForm.vue                  # 动态表单
│   │   ├── FormBuilder.vue                  # 表单构建器
│   │   └── FormValidator.vue                # 表单验证器
│   └── common/
│       ├── StatusCard.vue                   # 状态卡片
│       ├── MetricCard.vue                   # 指标卡片
│       ├── LoadingSkeleton.vue              # 骨架屏
│       └── ErrorBoundary.vue                # 错误边界
│
├── stores/
│   ├── backtest.ts                          # 回测状态管理
│   ├── research.ts                          # 研究状态管理
│   ├── trading.ts                           # 交易状态管理
│   └── websocket.ts                         # WebSocket管理
│
└── utils/
    ├── websocket.ts                         # WebSocket工具
    ├── sse.ts                               # SSE工具
    ├── chart.ts                             # 图表工具
    └── form.ts                              # 表单工具
```

---

## 总结

### 功能点统计

| 模块 | P0功能点 | P1功能点 | P2功能点 | 总计 |
|------|---------|---------|---------|------|
| 回测模块 | 15 | 16 | 6 | 37 |
| 研究模块 | 15 | 15 | 6 | 36 |
| 验证模块 | 6 | 8 | 0 | 14 |
| 模拟盘 | 15 | 6 | 0 | 21 |
| 实盘交易 | 16 | 10 | 0 | 26 |
| 前端UI | 12 | 12 | 0 | 24 |
| **总计** | **79** | **67** | **12** | **158** |

### 开发优先级建议

**第一阶段（MVP - 2个月）**：
- 回测模块P0功能（15个）
- 研究模块P0功能（15个）
- 前端UI核心组件（12个）

**第二阶段（完整功能 - 2个月）**：
- 回测模块P1功能（16个）
- 研究模块P1功能（15个）
- 模拟盘P0功能（15个）

**第三阶段（生产就绪 - 2个月）**：
- 实盘交易P0功能（16个）
- 验证模块P0+P1功能（14个）
- 前端UI完善（12个）

---

*文档版本：v1.0*
*创建日期：2026-02-09*
*维护者：Ginkgo开发团队*
