# Feature Specification: Ginkgo 量化研究功能模块

**Feature Branch**: `011-quant-research-modules`
**Created**: 2026-02-16
**Status**: Draft
**Input**: 按照 feature-roadmap.md 指定研发计划

## 概述

Ginkgo WebUI 提供了完整的量化交易工作流界面，但后端 Ginkgo 库缺少部分关键功能支撑。本规格说明定义了 14 个核心功能模块的设计需求，分为 P0-P3 四个优先级。

## Clarifications

### Session 2026-02-16

- Q: Paper Trading 的数据来源是什么？ → A: 实盘数据（当日真实市场数据），而非历史数据回放
- Q: Paper Trading 的定位是什么？ → A: 策略生命周期的第三阶段，用于真实市场环境下的策略验证

### 策略生命周期与验证流程

```
阶段1        阶段2           阶段3              阶段4
回测    →   样本外验证   →   Paper Trading   →   实盘交易
(历史)      (历史预留)       (实盘数据)         (真钱下单)
```

| 阶段 | 数据 | 订单 | 目的 |
|------|------|------|------|
| 回测 | 样本内历史数据 | 模拟 | 策略开发和逻辑验证 |
| 样本外验证 | 历史预留数据 | 模拟 | 验证泛化能力，防过拟合 |
| Paper Trading | 实盘数据 | 模拟（不执行） | 真实市场环境验证 |
| 实盘交易 | 实盘数据 | 真实下单 | 生产环境运行 |

**Paper Trading 核心定义**：
- 使用实盘正在产生的真实数据
- **数据获取**：复用 data 模块 CRUD 层，无需独立数据源抽象
- **盘中**：实时更新持仓市值、盈亏等显示（如有实盘数据）
- **盘后**：从 data 模块获取当日日K，执行策略计算，模拟成交，更新持仓
- 模拟成交，不执行真实订单
- 持久化状态，累计表现
- 最终验证：Paper Trading 表现与回测结果吻合 → 可投入实盘

**功能模块清单：**
- **P0 核心基础**: Paper Trading 模拟盘、回测对比
- **P1 因子研究**: IC 分析、因子分层、因子对比、因子正交化、因子衰减分析、因子换手率分析
- **P2 策略验证**: 参数优化器、走步验证、蒙特卡洛模拟、敏感性分析、交叉验证
- **P3 高级功能**: 因子组合管理

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Paper Trading 模拟盘交易 (Priority: P1)

量化研究员在完成回测和样本外验证后，需要在不使用真实资金的情况下，用实盘数据验证策略表现。Paper Trading 使用 Portfolio 接收每日实盘数据，生成信号并模拟成交，验证策略在真实市场环境下的表现是否与回测结果吻合。

**Why this priority**: Paper Trading 是策略上线前的最后一道验证关卡，用真实市场数据验证策略的泛化能力，降低实盘风险。

**Independent Test**: 可以通过加载已完成回测的 Portfolio，启动 Paper Trading，在若干交易日后对比 Paper Trading 表现与回测结果是否吻合来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户已完成 Portfolio 回测（收益率 +25%），**When** 用户启动 Paper Trading，**Then** 系统开始接收实盘数据
2. **Given** Paper Trading 运行中且为交易时间，**When** 系统接收到实盘数据（Tick 或分钟线），**Then** 实时更新持仓市值、当日盈亏显示
3. **Given** Paper Trading 运行中，**When** 每日收盘后系统获取当日日K数据，**Then** Portfolio 执行策略计算，生成信号，模拟成交，更新持仓
4. **Given** Paper Trading 运行 30 个交易日，**When** 用户查看对比报告，**Then** 系统显示 Paper Trading 收益（如 +23%）与回测收益（+25%）的对比，以及差异分析
5. **Given** Paper Trading 表现与回测结果吻合（差异 < 10%），**When** 用户确认，**Then** 系统提示"策略验证通过，可投入实盘"
6. **Given** Paper Trading 表现与回测结果差异较大（差异 > 20%），**When** 用户查看分析，**Then** 系统提示"策略可能过拟合，建议重新优化"

---

### User Story 2 - 回测对比分析 (Priority: P1)

量化研究员需要对比多个回测结果，了解不同策略或参数配置的表现差异。系统生成对比表格和净值曲线对比图，帮助用户快速选择最优方案。

**Why this priority**: 回测对比是策略优化过程中的关键环节，帮助用户在多个方案中做出决策。

**Independent Test**: 可以通过运行两个不同参数的回测，然后调用对比功能来独立测试，验证指标对比表格和净值曲线是否正确生成。

**Acceptance Scenarios**:

1. **Given** 用户已完成 3 个回测任务，**When** 用户选择这 3 个回测并点击"对比分析"，**Then** 系统生成对比表格，包含收益率、夏普比率、最大回撤等指标的横向对比
2. **Given** 对比表格已生成，**When** 用户查看"最佳表现"列，**Then** 每个指标都标注了表现最好的回测
3. **Given** 用户查看净值曲线对比，**When** 选择归一化显示，**Then** 所有净值曲线从 1.0 开始绘制，便于直观比较

---

### User Story 3 - 因子 IC 分析 (Priority: P2)

量化研究员需要评估因子的预测能力。系统计算因子值与未来收益的相关性（IC），生成 IC 时序图和统计指标（IC均值、ICIR、t统计量等）。

**Why this priority**: IC 分析是因子研究的核心方法，是筛选有效因子的基础工具。

**Independent Test**: 可以通过提供一个已知因子数据和收益数据来独立测试，验证 IC 计算是否正确，统计指标是否符合预期。

**Acceptance Scenarios**:

1. **Given** 用户选择因子"MOM_20"和日期范围，**When** 用户点击"IC 分析"，**Then** 系统计算 1 日、5 日、10 日、20 日的 IC 时序
2. **Given** IC 时序已计算，**When** 用户查看统计结果，**Then** 显示 IC 均值、标准差、ICIR、t 统计量、正 IC 占比
3. **Given** IC 分析完成，**When** 用户点击"下载报告"，**Then** 导出包含 IC 时序图、分布图、统计表的报告文件

---

### User Story 4 - 因子分层回测 (Priority: P2)

量化研究员需要分析因子的单调性和多空收益。系统按因子值将股票分为 N 组，分别计算各组收益，验证因子是否具有稳定的区分能力。

**Why this priority**: 分层回测是验证因子有效性的重要方法，可以直接观察因子分组收益的单调性。

**Independent Test**: 可以通过提供一个因子数据和收益数据来独立测试，验证分组逻辑、各组收益计算、多空收益是否正确。

**Acceptance Scenarios**:

1. **Given** 用户选择因子和分组数（5 组），**When** 用户点击"分层回测"，**Then** 系统按因子值将股票分为 5 组，计算各组收益序列
2. **Given** 分层回测完成，**When** 用户查看结果，**Then** 显示各组累计收益曲线、多空收益曲线（最高组 - 最低组）
3. **Given** 用户查看统计指标，**When** 系统计算单调性 R²，**Then** 显示因子单调性得分（0-1，越接近 1 越单调）

---

### User Story 5 - 参数优化 (Priority: P2)

量化研究员需要找到策略的最优参数组合。系统支持网格搜索、遗传算法、贝叶斯优化等多种优化方法，自动搜索参数空间。

**Why this priority**: 参数优化是策略开发的核心环节，直接影响策略表现。

**Independent Test**: 可以通过定义一个简单策略和参数范围来独立测试，验证优化过程是否正确运行，是否找到较优参数。

**Acceptance Scenarios**:

1. **Given** 用户选择策略和待优化参数范围（如快均线 5-20，慢均线 20-60），**When** 用户选择"网格搜索"并点击"开始优化"，**Then** 系统遍历所有参数组合，记录每组的表现指标
2. **Given** 优化完成，**When** 用户查看结果，**Then** 按目标指标（如夏普比率）排序显示所有参数组合
3. **Given** 用户选择"遗传算法"，**When** 设置种群大小 50、迭代次数 20，**Then** 系统在参数空间中智能搜索，返回近似最优解

---

### User Story 6 - 走步验证 (Priority: P2)

量化研究员需要评估策略的过拟合程度。系统使用滑动窗口方式进行样本外验证，计算训练期和测试期收益的退化程度。

**Why this priority**: 走步验证是检验策略稳定性的关键方法，可以识别过拟合问题。

**Independent Test**: 可以通过提供一个策略和参数来独立测试，验证滑动窗口划分、各 fold 的收益计算是否正确。

**Acceptance Scenarios**:

1. **Given** 用户选择策略和参数，设置训练期 252 天、测试期 63 天，**When** 用户点击"走步验证"，**Then** 系统按滑动窗口划分数据，分别计算训练期和测试期收益
2. **Given** 验证完成，**When** 用户查看结果，**Then** 显示各 fold 的训练/测试收益对比、退化程度、稳定性得分
3. **Given** 测试期收益显著低于训练期，**When** 退化程度 > 50%，**Then** 系统提示"可能存在过拟合"

---

### User Story 7 - 蒙特卡洛模拟 (Priority: P3)

量化研究员需要评估策略的风险分布。系统基于历史收益进行随机模拟，计算 VaR、CVaR 等风险指标。

**Why this priority**: 蒙特卡洛模拟提供风险分布的可视化，帮助用户理解策略的潜在风险。

**Independent Test**: 可以通过提供一个历史收益序列来独立测试，验证模拟结果是否符合统计规律。

**Acceptance Scenarios**:

1. **Given** 用户输入历史收益序列和模拟次数 10000，**When** 用户点击"蒙特卡洛模拟"，**Then** 系统生成 10000 条模拟收益路径
2. **Given** 模拟完成，**When** 用户查看结果，**Then** 显示收益分布直方图、均值、标准差、分位数
3. **Given** 用户设置置信水平 95%，**When** 系统计算 VaR，**Then** 显示 95% VaR（最大可能损失）

---

### User Story 8 - 因子正交化 (Priority: P3)

量化研究员需要去除因子间的相关性。系统支持 Gram-Schmidt、PCA、残差法等正交化方法。

**Why this priority**: 正交化是多因子模型构建的重要步骤，减少因子间的信息冗余。

**Independent Test**: 可以通过提供多个相关因子来独立测试，验证正交化后因子相关性是否显著降低。

**Acceptance Scenarios**:

1. **Given** 用户选择 3 个因子，**When** 用户选择"Gram-Schmidt 正交化"，**Then** 系统按指定顺序依次正交化，返回新因子值
2. **Given** 正交化完成，**When** 用户查看相关系数矩阵，**Then** 正交化后的因子相关系数接近 0
3. **Given** 用户选择"PCA 正交化"，**When** 设置保留方差比例 95%，**Then** 系统返回主成分因子

---

### Edge Cases

- 当因子数据存在缺失值时，系统应如何处理？（默认：剔除缺失值对应的样本）
- 当参数空间过大（如网格搜索超过 10000 组合）时，系统应如何处理？（默认：提示用户缩小范围或使用智能优化）
- 当历史数据不足（如走步验证数据少于一个完整 fold）时，系统应如何处理？（默认：报错提示数据不足）
- 当 Paper Trading 获取实盘数据失败时，系统应如何处理？（默认：记录日志，等待下次尝试，不中断运行）
- 当 Paper Trading 表现与回测差异过大（>30%）时，系统应如何处理？（默认：自动告警，提示用户检查策略）

---

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用 ServiceHub 模式，通过 `from ginkgo import services` 访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**量化交易特有需求**:
- **FR-006**: System MUST 支持多数据源接入 (ClickHouse/MySQL/MongoDB/Redis)
- **FR-007**: System MUST 支持批量数据操作
- **FR-008**: System MUST 集成风险管理系统
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循 TDD 开发流程，先写测试再实现功能

**P0 核心基础功能需求**:

*Paper Trading 系统*:
- **FR-011**: Paper Trading System MUST 使用实盘数据，复用 data 模块 CRUD 层获取数据
- **FR-012**: Paper Trading System MUST 盘中实时更新持仓市值和盈亏显示（如有实盘数据）
- **FR-013**: Paper Trading System MUST 盘后执行策略计算，模拟成交，持久化 Portfolio 状态
- **FR-014**: Paper Trading System MUST 生成信号但模拟成交，不执行真实订单
- **FR-015**: Paper Trading System MUST 复用回测引擎的成交逻辑（滑点、手续费计算）
- **FR-016**: Paper Trading System MUST 提供与回测结果的对比分析功能

*回测对比功能*:
- **FR-017**: 回测对比功能 MUST 支持多个回测结果的横向指标对比
- **FR-018**: 回测对比功能 MUST 生成净值曲线对比图
- **FR-019**: 回测对比功能 MUST 标注每个指标的最佳表现

**P1 因子研究功能需求**:
- **FR-020**: IC 分析功能 MUST 计算 Pearson IC 和 Rank IC
- **FR-021**: IC 分析功能 MUST 支持多周期（1/5/10/20 日）IC 计算
- **FR-022**: IC 分析功能 MUST 计算统计指标（均值、标准差、ICIR、t 统计量、正 IC 占比）
- **FR-023**: 因子分层功能 MUST 支持可配置分组数（3/5/10 组）
- **FR-024**: 因子分层功能 MUST 计算各组收益、多空收益、单调性 R²
- **FR-025**: 因子对比功能 MUST 对多个因子进行综合评分
- **FR-026**: 因子正交化功能 MUST 支持 Gram-Schmidt、PCA、残差法三种方法
- **FR-027**: 因子衰减分析功能 MUST 计算因子半衰期
- **FR-028**: 因子换手率分析功能 MUST 计算平均换手率

**P2 策略验证功能需求**:
- **FR-029**: 参数优化器 MUST 支持网格搜索、遗传算法、贝叶斯优化三种方法
- **FR-030**: 参数优化器 MUST 支持多目标优化（收益率、夏普比率、最大回撤）
- **FR-031**: 走步验证功能 MUST 支持可配置的训练期/测试期/步长
- **FR-032**: 走步验证功能 MUST 计算过拟合程度和稳定性得分
- **FR-033**: 蒙特卡洛模拟功能 MUST 支持 VaR 和 CVaR 计算
- **FR-034**: 敏感性分析功能 MUST 分析单个参数变化对策略表现的影响
- **FR-035**: 交叉验证功能 MUST 支持时间序列 K-Fold 验证

**P3 高级功能需求**:
- **FR-036**: 因子组合功能 MUST 支持多因子加权组合
- **FR-037**: 因子组合功能 MUST 支持行业中性约束

**代码维护与文档需求**:
- **FR-038**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-039**: Header updates MUST be verified during code review process

**配置验证需求**:
- **FR-040**: 配置类功能验证 MUST 包含配置文件存在性检查
- **FR-041**: 配置类验证 MUST 确认值从配置文件读取，而非代码默认值

---

### Key Entities

- **PaperTradingEngine**: Paper Trading 引擎，管理 Portfolio 在实盘数据上的运行（启动/停止/状态持久化）
- **PaperTradingResult**: Paper Trading 结果，包含累计表现、每日信号记录、与回测的对比分析
- **ICAnalysisResult**: IC 分析结果，包含 IC 时序、统计指标、图表数据
- **LayeringResult**: 分层回测结果，包含各组收益、多空收益、单调性指标
- **OptimizationResult**: 优化结果，包含参数组合、目标值、排名
- **WalkForwardResult**: 走步验证结果，包含各 fold 训练/测试收益、退化程度
- **MonteCarloResult**: 蒙特卡洛结果，包含收益分布、分位数、VaR/CVaR

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-001**: IC 分析计算时间 < 10 秒（1000 只股票 × 500 交易日）
- **SC-002**: 分层回测计算时间 < 30 秒（1000 只股票 × 500 交易日 × 5 组）
- **SC-003**: 参数优化支持 > 1000 组参数组合
- **SC-004**: 蒙特卡洛模拟支持 > 10000 次模拟

**功能完整性指标**:
- **SC-005**: Paper Trading 支持每日自动获取实盘数据并执行策略
- **SC-006**: Paper Trading 提供与回测结果的自动对比分析
- **SC-007**: 回测对比支持 >= 10 个回测同时对比
- **SC-008**: 因子研究支持所有内置因子类型
- **SC-009**: 参数优化支持所有数值型策略参数

**系统可靠性指标**:
- **SC-010**: 代码测试覆盖率 > 80%
- **SC-011**: 所有公共 API 有完整文档
- **SC-012**: 所有模块遵循 Ginkgo 架构规范（ServiceHub、装饰器、类型注解）

**业务与用户体验指标**:
- **SC-013**: 策略开发者可在 30 分钟内学会使用新模块
- **SC-014**: 所有功能通过 CLI 和 Python API 两种方式访问
- **SC-015**: 错误信息清晰，包含解决建议

---

## Assumptions

1. **Paper Trading 数据获取**: 复用 data 模块 CRUD 层，盘后通过 bar_crud 获取当日日K数据
2. **Paper Trading 运行假设**: Paper Trading 作为独立服务运行，盘中实时更新显示，盘后执行策略
3. **数据格式假设**: 因子数据采用 DataFrame 格式，包含 date、code、factor_value 列
4. **收益数据假设**: 收益数据采用 DataFrame 格式，包含 date、code、return 列
5. **滑点默认值**: 默认使用 0.1% 百分比滑点
6. **手续费默认值**: 默认使用 0.03% 手续费率，最低 5 元
7. **优化默认目标**: 参数优化默认目标为夏普比率最大化
8. **走步验证默认参数**: 训练期 252 天，测试期 63 天，步长 21 天
9. **蒙特卡洛默认参数**: 模拟次数 10000，置信水平 95%

---

## Dependencies

1. **现有模块依赖**:
   - 回测引擎 (`ginkgo.trading.engines`) - Paper Trading 复用成交逻辑
   - 因子计算引擎 (`ginkgo.features`)
   - 数据访问层 (`ginkgo.data`) - 复用 CRUD 获取日K数据
   - Portfolio 管理 (`ginkgo.trading.portfolios`) - Paper Trading 以 Portfolio 为单位运行
   - 数据更新服务 (`ginkgo.workers`) - 每日数据更新

2. **新增依赖**:
   - scipy（优化算法、统计分析）
   - scikit-learn（PCA、标准化）
   - optuna（贝叶斯优化，可选）
   - deap（遗传算法，可选）

---

## Out of Scope

1. **实盘交易执行**: Paper Trading 仅模拟成交，不执行真实订单，不修改实盘交易逻辑
2. **WebUI 前端开发**: 本功能仅定义后端库 API，前端界面开发单独规划
3. **数据源扩展**: 本功能使用现有数据源，不新增数据源类型
4. **分布式计算**: 初期版本不支持分布式参数优化，后续可扩展

---

## References

- [feature-roadmap.md](../../docs/feature-roadmap.md) - 详细设计和研发计划
- [Ginkgo CLAUDE.md](../../CLAUDE.md) - 项目开发规范
