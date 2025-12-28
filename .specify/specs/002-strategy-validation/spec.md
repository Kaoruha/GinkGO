# Feature Specification: Strategy Evaluation Module

**Feature Branch**: `002-strategy-evaluation`
**Created**: 2025-12-27
**Status**: Draft
**Input**: User description: "构建一个评估模块，用来评估编写的策略"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 策略结构评估 (Priority: P1)

作为策略开发者，我需要快速发现编写的策略类是否存在结构性问题，避免在回测时才遇到错误。

**场景描述**:
开发者在创建新的策略类后，可以通过 CLI 命令或 API 调用评估模块，快速检查策略类是否符合 Ginkgo 框架的基本要求，包括：
- 是否正确继承自 BaseStrategy
- 是否实现了必需的 `cal()` 方法
- 方法的签名是否正确（参数类型、返回类型）
- 是否缺少必需的初始化参数

**Why this priority**: 这是核心功能，确保策略能够被框架正确识别和调用，是其他所有评估的基础。

**Independent Test**: 可以独立测试 - 评估一个简单的策略类结构，报告所有结构性问题，不依赖回测引擎或数据。

**Acceptance Scenarios**:

1. **Given** 一个正确继承 BaseStrategy 并实现 cal() 方法的策略类，**When** 执行结构评估，**Then** 评估通过，无错误报告
2. **Given** 一个忘记实现 cal() 方法的策略类，**When** 执行结构评估，**Then** 报告 "缺少必需的 cal() 方法" 错误
3. **Given** 一个 cal() 方法签名错误的策略（如缺少必需参数），**When** 执行结构评估，**Then** 报告具体的签名错误信息
4. **Given** 一个未继承 BaseStrategy 的普通类，**When** 执行结构评估，**Then** 报告 "必须继承 BaseStrategy" 错误

---

### User Story 2 - 策略逻辑评估 (Priority: P2)

作为策略开发者，我需要评估策略的业务逻辑是否符合框架要求，避免运行时错误。

**场景描述**:
评估模块检查策略的业务逻辑是否遵循 Ginkgo 的事件驱动架构：
- `cal()` 方法是否正确处理 `EventPriceUpdate` 事件
- 返回的 Signal 对象是否包含必需字段（code, direction, reason）
- 策略是否正确使用 `TimeProvider` 获取业务时间
- 策略是否避免在 `cal()` 中执行耗时操作（如数据库查询、网络请求）

**Why this priority**: 确保策略在回测环境中能够正常运行，避免运行时错误影响回测流程。

**Independent Test**: 可以独立测试 - 提供一个包含逻辑错误的策略样本，评估模块能够识别并报告具体的逻辑问题。

**Acceptance Scenarios**:

1. **Given** 一个正确处理事件并返回有效 Signal 的策略，**When** 执行逻辑评估，**Then** 评估通过
2. **Given** 一个返回 None 或空列表的策略，**When** 执行逻辑评估，**Then** 报告警告 "cal() 方法应返回 List[Signal]"
3. **Given** 一个返回 Signal 缺少 code 字段的策略，**When** 执行逻辑评估，**Then** 报告 "Signal 必须包含 code 字段"
4. **Given** 一个在 cal() 中直接查询数据库的策略，**When** 执行逻辑评估，**Then** 报告警告 "cal() 中不应执行数据库查询"

---

### User Story 3 - 策略最佳实践评估 (Priority: P3)

作为策略开发者，我需要获得代码质量建议，编写更符合最佳实践的策略代码。

**场景描述**:
评估模块提供可选的最佳实践检查：
- 是否使用装饰器（@time_logger, @retry）优化性能
- 是否正确处理异常情况
- 是否有适当的日志记录
- 参数验证是否完整
- 是否正确实现 `reset_state()` 方法

**Why this priority**: 这是增强功能，帮助开发者编写更高质量的代码，但不影响基本功能。

**Independent Test**: 可以独立测试 - 提供策略代码，生成最佳实践建议报告。

**Acceptance Scenarios**:

1. **Given** 一个使用 @time_logger 装饰器的策略，**When** 执行最佳实践评估，**Then** 报告 "使用了性能监控装饰器"
2. **Given** 一个没有异常处理的策略，**When** 执行最佳实践评估，**Then** 建议添加 try-except 块
3. **Given** 一个正确实现 reset_state() 的策略，**When** 执行最佳实践评估，**Then** 确认状态管理正确
4. **Given** 一个参数验证完整的策略，**When** 执行最佳实践评估，**Then** 确认参数处理良好

---

### User Story 4 - 信号生成追踪与可视化 (Priority: P2)

作为策略开发者，我需要追踪策略运行时的信号生成过程，评估信号是否符合预期原因。

**场景描述**:
评估模块提供运行时信号追踪功能，帮助开发者理解策略行为：
- 追踪每次 `cal()` 调用的输入（事件数据）和输出（信号列表）
- 记录信号生成的上下文信息（价格、技术指标、策略状态）
- 支持多种数据源（K线、Tick、OrderFlow等）
- 可视化信号生成过程（价格图表 + 信号标注）

**Why this priority**: 帮助开发者验证策略逻辑是否按预期工作，是策略调试的关键工具。

**Independent Test**: 可以独立测试 - 提供测试数据和策略，生成追踪报告和可视化图表。

**Acceptance Scenarios**:

1. **Given** 一个策略和测试数据，**When** 执行信号追踪，**Then** 生成包含所有信号的追踪报告
2. **Given** 使用 K 线数据源，**When** 生成可视化，**Then** 显示价格图表和信号标注点
3. **Given** 使用 Tick 数据源，**When** 生成可视化，**Then** 显示 Tick 序列和信号标注点
4. **Given** 策略生成了不符合预期的信号，**When** 查看追踪报告，**Then** 能够看到完整的输入输出上下文

---

### User Story 5 - 数据库策略评估 (Priority: P1)

作为策略开发者，我需要评估存储在数据库中的策略代码，无需手动导出为本地文件。

**场景描述**:
Ginkgo 框架支持将策略代码直接存储在数据库的 MFile 表中（作为 MEDIUMBLOB），并通过 PortfolioFileMapping 与 Portfolio 绑定。评估模块应支持：
- 按 `file_id`（MFile.uuid）加载并评估数据库中的策略
- 按 `portfolio_id` 查找并评估其绑定的策略
- 列出数据库中所有可评估的策略（支持名称过滤）
- 批量评估数据库中的所有策略（支持名称过滤）
- 临时文件自动清理（评估完成后删除）

**Why this priority**: 数据库策略是 Ginkgo 的核心功能，评估模块必须原生支持，保持与本地文件评估一致的功能。

**Independent Test**: 可以独立测试 - 插入测试策略到数据库，通过 file_id 评估，检查临时文件是否被清理。

**Acceptance Scenarios**:

1. **Given** 数据库中存储了一个策略代码（MFile.type=STRATEGY），**When** 使用 `--file-id` 评估，**Then** 成功加载并评估，评估后临时文件被删除
2. **Given** 一个 Portfolio 绑定了策略文件，**When** 使用 `--portfolio-id` 评估，**Then** 自动查找绑定的策略并评估
3. **Given** 数据库中有 10 个策略，**When** 使用 `--list` 参数，**Then** 显示策略列表（file_id、name、size、updated_at）
4. **Given** 数据库策略和测试数据，**When** 使用 `--show-trace` 评估，**Then** 功能与本地文件完全相同
5. **Given** 数据库策略和测试数据，**When** 使用 `--visualize` 评估，**Then** 生成可视化图表，临时文件被清理
6. **Given** 临时文件创建后，**When** 评估完成（无论成功或失败），**Then** 临时文件被自动删除，不留残留

**Technical Notes**:
- 数据库策略加载路径：`MFile.uuid → file_id → MFile.data (bytes) → decode('utf-8') → 临时文件`
- Portfolio 绑定路径：`Portfolio.uuid → PortfolioFileMapping.portfolio_id → file_id → MFile`
- 使用 `tempfile.NamedTemporaryFile(delete=False)` + 上下文管理器确保清理
- 评估流程统一：本地文件和数据库策略最终都通过文件路径评估，操作完全相同

---

### User Story 6 - 架构可扩展性 (Priority: P4)

作为框架维护者，我需要评估模块能够支持评估多种 Ginkgo 组件类型（Strategy、Selector、Sizer、RiskManager），而不仅仅是策略。

**场景描述**:
评估模块采用可扩展架构设计：
- **统一评估器**：单一 `ComponentEvaluator` 类支持所有组件类型
- **规则注册表**：通过配置驱动的方式组装不同组件的评估规则
- **Pipeline 模式**：支持灵活的评估流程编排（静态分析 → 运行时检查 → 信号追踪）
- **模板化报告**：支持自定义报告模板和多渠道导出（终端、文件、HTTP、Webhook）
- **装饰器可视化**：可视化模块支持装饰器模式，可组合多种图表装饰（信号标注、技术指标、注释）

**Why this priority**: 虽然不是当前 MVP 的必需功能，但为未来扩展 Selector、Sizer、RiskManager 评估奠定基础，降低维护成本。

**Independent Test**: 可以独立测试 - 创建 RiskManager 评估规则配置，验证 `ginkgo validate risk_manager my_risk.py` 可以工作。

**Acceptance Scenarios**:

1. **Given** 评估器采用规则注册表模式，**When** 注册新的组件类型规则，**Then** CLI 自动支持新组件类型评估
2. **Given** 可视化模块采用装饰器模式，**When** 添加新的图表装饰器（如技术指标），**Then** 可以与信号标注装饰器组合使用
3. **Given** 报告模块采用模板引擎，**When** 添加新的输出格式（如 HTML），**Then** 只需创建新模板文件无需修改代码
4. **Given** 评估流程采用 Pipeline 模式，**When** 添加新的评估阶段（如数据质量检查），**Then** 可以插入到现有流程中

**Technical Notes**:
- **单一评估器模式**：使用 `ComponentEvaluator` + `RULES_REGISTRY` 配置，而非每个组件类型一个评估器类
- **规则配置驱动**：通过 YAML 配置文件定义规则集，支持继承和组合（basic → standard → strict）
- **可视化分层**：ChartBuilder（构建器）+ Renderer（渲染后端）+ Decorator（装饰器）三层分离
- **报告模板化**：使用 Jinja2 模板引擎，数据和展示分离
- **Pipeline 流水线**：支持串行/并行执行、条件跳过、失败快速终止等策略

---

### Edge Cases

- **策略类无法导入**: 当策略类有语法错误或导入依赖缺失时，评估模块应友好报告错误
- **动态生成的策略类**: 当策略类是通过元类或工厂模式动态创建时，评估模块仍能正常工作
- **继承链过深**: 当策略类有多层继承时，评估模块应正确识别 BaseStrategy 的继承关系
- **异步方法**: 当策略的 cal() 方法是异步的（async def），评估模块应明确报告不支持
- **策略文件包含多个类**: 当一个 .py 文件中定义了多个策略类时，评估模块应分别处理每个类
- **信号追踪数据源不支持**: 当使用不支持的数据源时，追踪器应明确提示支持的数据源类型
- **可视化数据缺失**: 当数据源返回空数据时，可视化应友好提示而非崩溃
- **大量信号生成**: 当策略生成数百个信号时，可视化应支持分页或聚合显示

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: 评估模块 MUST 遵循事件驱动架构原则
- **FR-002**: 评估模块 MUST 使用 ServiceHub 模式访问服务
- **FR-003**: 评估模块 MUST 严格分层：评估器层、规则层、报告层
- **FR-004**: 评估模块 MUST 使用 `@time_logger`、`@retry` 装饰器
- **FR-005**: 评估模块 MUST 提供类型注解

**结构评估需求**:
- **FR-011**: 评估模块 MUST 检查策略类是否继承自 BaseStrategy
- **FR-012**: 评估模块 MUST 检查策略类是否实现 `cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]` 方法
- **FR-013**: 评估模块 MUST 检查 `__init__` 方法是否调用 `super().__init__()`
- **FR-014**: 评估模块 MUST 检查策略类是否有 `__abstract__ = False` 标记

**逻辑评估需求**:
- **FR-021**: 评估模块 MUST 检查 `cal()` 方法是否使用正确的参数名称
- **FR-022**: 评估模块 MUST 检查返回的 Signal 对象是否包含必需字段
- **FR-023**: 评估模块 MUST 检查 Signal 的 direction 是否为有效的 DIRECTION_TYPES
- **FR-024**: 评估模块 MUST 检查策略是否使用 `self.get_time_provider()` 获取时间

**最佳实践评估需求**:
- **FR-031**: 评估模块 SHOULD 检查是否使用性能优化装饰器
- **FR-032**: 评估模块 SHOULD 检查是否有适当的异常处理
- **FR-033**: 评估模块 SHOULD 检查日志记录是否充分
- **FR-034**: 评估模块 SHOULD 检查 `reset_state()` 是否调用 `super().reset_state()`

**CLI 接口需求**:
- **FR-041**: 系统 MUST 提供 `ginkgo validate <component_file>` 命令，支持 `--type` 参数指定组件类型
- **FR-042**: 系统 MUST 支持 `--format` 参数（text/json/markdown）
- **FR-043**: 系统 MUST 支持 `--verbose` 参数显示详细输出
- **FR-044**: 系统 MUST 提供清晰的错误定位（行号、列号、文件名）

**数据库策略评估需求**:
- **FR-045**: 系统 MUST 支持 `--file-id <uuid>` 参数从数据库加载策略（MFile.uuid）
- **FR-046**: 系统 MUST 支持 `--portfolio-id <uuid>` 参数评估 Portfolio 绑定的策略
- **FR-047**: 系统 MUST 提供 `--list` 参数列出数据库中所有可评估的策略
- **FR-048**: 系统 MUST 支持 `--all` 参数批量评估所有数据库策略
- **FR-049**: 系统 MUST 支持 `--filter <pattern>` 参数过滤策略名称
- **FR-050**: 数据库策略评估 MUST 自动清理临时文件（无论成功或失败）
- **FR-051**: 数据库策略 MUST 支持与本地文件相同的所有功能（--show-trace, --visualize）

**报告输出需求**:
- **FR-052**: 评估报告 MUST 包含错误、警告、建议三个级别
- **FR-053**: 错误信息 MUST 包含具体的修复建议
- **FR-054**: 评估报告 MUST 包含总体评分（通过/不通过）
- **FR-055**: 评估报告 MUST 支持多种输出格式

**信号追踪需求**:
- **FR-061**: 评估模块 MUST 提供 SignalTracer 用于追踪信号生成过程
- **FR-062**: SignalTracer MUST 记录每次 cal() 调用的输入（事件）和输出（信号）
- **FR-063**: SignalTracer MUST 捕获信号生成的上下文（时间、价格、策略状态）
- **FR-064**: 追踪报告 MUST 支持导出为 JSON/CSV/Markdown 格式

**数据源适配器需求**:
- **FR-071**: 评估模块 MUST 提供 DataSourceAdapter 接口
- **FR-072**: 系统 MUST 支持多种数据源适配器（K线、Tick、OrderFlow）
- **FR-073**: 适配器 MUST 自动根据事件类型选择（AdapterFactory 模式）
- **FR-074**: 适配器 MUST 提供 get_visualization_data() 方法提取可视化数据
- **FR-075**: 适配器 MUST 提供 format_signal_info() 方法格式化信号描述
- **FR-076**: 适配器 MUST 提供 get_data_summary() 方法提取数据摘要

**可视化需求**:
- **FR-081**: 系统 MUST 提供 SignalVisualizer 用于生成可视化图表
- **FR-082**: 可视化 MUST 支持多种数据源类型（K线、Tick等）
- **FR-083**: 可视化 MUST 在图表上标注信号位置（买入/卖出点）
- **FR-084**: 可视化 MUST 支持输出为 PNG/SVG/HTML 格式
- **FR-085**: 可视化 MUST 支持交互式图表（可选，使用 Plotly）

**架构扩展性需求**:
- **FR-091**: 系统 MUST 提供统一的 ComponentEvaluator 类支持多种组件类型评估
- **FR-092**: 系统 MUST 提供规则注册表（RuleRegistry）支持动态注册评估规则
- **FR-093**: 系统 SHOULD 支持通过 YAML 配置文件定义评估规则集和级别
- **FR-094**: 系统 MUST 支持装饰器模式的可视化架构（ChartBuilder + Renderer + Decorator）
- **FR-095**: 系统 MUST 支持模板驱动的报告生成（Jinja2 模板引擎）

### Key Entities

**评估相关**:
- **StrategyClass**: 被评估的策略类，包含类定义、方法、属性
- **EvaluationRule**: 评估规则实体，定义具体的检查逻辑和错误消息
- **EvaluationReport**: 评估报告实体，包含评估结果、错误列表、建议列表
- **EvaluationSeverity**: 评估严重程度枚举（ERROR/WARNING/INFO）
- **EvaluationLevel**: 评估级别枚举（basic/standard/strict）

**信号追踪相关**:
- **SignalTrace**: 信号追踪记录，包含单次 cal() 调用的输入输出
- **SignalTraceReport**: 追踪报告，包含所有 SignalTrace 的汇总
- **SignalTracer**: 信号追踪器，负责捕获和记录信号生成过程

**数据源适配器相关**:
- **DataSourceAdapter**: 数据源适配器接口，定义统一的数据提取方法
- **BarDataAdapter**: K线数据适配器，处理 EventPriceUpdate
- **TickDataAdapter**: Tick数据适配器，处理 EventTickUpdate
- **OrderFlowAdapter**: 订单流数据适配器，处理 EventOrderFlow
- **AdapterFactory**: 适配器工厂，根据事件类型自动选择适配器

**可视化相关**:
- **SignalVisualizer**: 信号可视化器，生成价格图表和信号标注
- **ChartConfig**: 图表配置，定义图表样式、颜色、布局

**架构扩展性相关**:
- **ComponentType**: 组件类型枚举（STRATEGY, SELECTOR, SIZER, RISK_MANAGER）
- **ComponentEvaluator**: 统一组件评估器，支持所有组件类型
- **RuleRegistry**: 规则注册表，存储和管理评估规则
- **PipelineStage**: Pipeline 阶段接口，定义评估流程中的单个步骤
- **EvaluationPipeline**: 评估流水线，编排多个 PipelineStage 执行
- **ChartBuilder**: 图表构建器，使用装饰器模式组合可视化元素
- **ChartRenderer**: 图表渲染后端接口（MatplotlibRenderer, PlotlyRenderer）
- **ChartDecorator**: 图表装饰器接口（SignalDecorator, IndicatorDecorator）
- **TemplateEngine**: 模板引擎接口，支持 Jinja2 模板渲染
- **ReportExporter**: 报告导出器接口（FileExporter, HTTPExporter, WebhookExporter）

## Success Criteria *(mandatory)*

### Measurable Outcomes

**功能完整性指标**:
- **SC-001**: 能够识别 100% 的结构性错误（继承、方法签名等）
- **SC-002**: 能够识别 90% 以上的常见逻辑错误（信号字段缺失、参数错误等）
- **SC-003**: 静态验证时间 < 2秒（对于单个策略文件）
- **SC-004**: 信号追踪支持 K线 和 Tick 数据源

**易用性指标**:
- **SC-006**: 错误信息的可理解性 > 90%（用户测试评分）
- **SC-007**: 新手开发者能够在 5 分钟内理解验证报告并修复错误
- **SC-008**: CLI 命令响应时间 < 1秒（基本验证）
- **SC-009**: 开发者能在 1 分钟内通过可视化确认信号是否符合预期

**质量与可靠性指标**:
- **SC-010**: 验证模块自身的测试覆盖率 > 85%
- **SC-011**: 验证误报率 < 5%（将正确代码报告为错误）
- **SC-012**: 验证漏报率 < 10%（未能检测到实际错误）

**开发效率指标**:
- **SC-013**: 策略开发调试时间减少 50%（对比必须运行完整回测）
- **SC-014**: 策略代码质量问题提前发现率 > 80%（在回测前）
- **SC-015**: 新手策略开发者上手时间减少 40%
- **SC-016**: 信号验证速度 > 回测速度 10倍（不需要完整回测即可验证）

## Assumptions

1. **策略文件位置**: 假设策略文件位于标准位置（`src/ginkgo/trading/strategies/` 或用户自定义目录）
2. **Python 版本**: 假设使用 Python 3.8+，支持类型注解和装饰器
3. **BaseStrategy 接口**: 假设 BaseStrategy 的接口在验证周期内保持稳定
4. **策略复杂度**: 假设单个策略文件不超过 2000 行代码
5. **验证场景**: 主要针对回测策略验证，实时策略可能需要额外规则

## Dependencies

1. **Ginkgo 核心模块**: 依赖 BaseStrategy、Signal、EventBase 等核心类的定义
2. **Python AST 模块**: 用于静态代码分析
3. **inspect 模块**: 用于运行时检查类和方法
4. **typing 模块**: 用于类型检查
5. **Rich 库**: 用于美化 CLI 输出（与现有 CLI 保持一致）
6. **Matplotlib**: 用于生成静态可视化图表（PNG/SVG）
7. **Plotly** (可选): 用于生成交互式可视化图表（HTML）
8. **Pandas**: 用于数据处理和聚合
9. **contextlib**: 用于信号追踪的上下文管理器
10. **Jinja2**: 用于模板驱动的报告生成（FR-095）

## Out of Scope

1. **策略性能分析**: 不分析策略的运行时性能（如计算复杂度）
2. **策略盈利能力评估**: 不评估策略的投资表现
3. **策略参数优化**: 不提供参数调整建议
4. **跨语言策略**: 仅支持 Python 编写的策略
5. **实时策略监控**: 不涉及策略在实盘运行时的监控
6. **完整回测执行**: 本模块提供快速验证，不替代完整回测流程
7. **自动化策略修复**: 仅提供建议，不自动修复代码
8. **其他组件类型评估（当前版本）**: P4 优先级，未来支持 Selector/Sizer/RiskManager 评估

## In Scope (明确包含)

1. **快速代码验证**: 静态分析 + 运行时检查，快速发现结构/逻辑问题
2. **信号生成追踪**: 捕获策略运行时的信号生成过程
3. **信号可视化**: 在图表上标注信号位置，方便验证是否符合预期
4. **多数据源支持**: 初期支持 K线 和 Tick，可扩展到 OrderFlow 等
5. **开发者友好**: 提供清晰的错误提示和修复建议
6. **可扩展架构**: 为未来支持其他组件类型评估奠定基础（P4 优先级）
