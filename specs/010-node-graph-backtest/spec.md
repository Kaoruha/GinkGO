# Feature Specification: 节点图拖拉拽配置回测功能

**Feature Branch**: `010-node-graph-backtest`
**Created**: 2026-02-02
**Status**: Draft
**Input**: User description: "节点图拖拉拽配置回测"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 节点画布基础操作 (Priority: P1)

用户通过可视化画布创建和管理回测配置节点，支持添加、连接、删除节点。

**Why this priority**: 这是核心基础功能，所有其他功能都依赖于节点图的基本操作能力。

**Independent Test**: 用户可以独立测试节点添加、连线、删除操作，无需依赖后端编译和执行功能。

**Acceptance Scenarios**:

1. **Given** 用户打开回测配置页面，**When** 点击节点库中的节点类型，**Then** 该节点被添加到画布中心位置
2. **Given** 画布上有两个节点，**When** 从源节点输出端口拖拽到目标节点输入端口，**Then** 建立连接线显示节点间依赖关系
3. **Given** 选中一个节点，**When** 按下 Delete 键或点击删除按钮，**Then** 节点及其所有连接线被移除
4. **Given** 选中一条连接线，**When** 点击删除按钮，**Then** 连接线被移除但节点保留

---

### User Story 2 - 节点参数配置 (Priority: P1)

用户点击节点可打开参数面板，配置节点特定参数（如时间范围、初始资金、Broker类型等）。

**Why this priority**: 没有参数配置，节点图只是空壳；这是实现回测配置的关键能力。

**Independent Test**: 用户可以为单个节点配置参数并保存，验证参数持久化和表单验证逻辑。

**Acceptance Scenarios**:

1. **Given** 用户点击 Engine 节点，**When** 在右侧面板设置开始日期、结束日期、Broker类型，**Then** 参数被保存到节点配置中，节点显示摘要信息
2. **Given** 用户配置 Strategy 节点，**When** 选择策略类型并设置策略参数，**Then** 节点显示已配置的策略名称
3. **Given** 用户输入无效日期格式，**When** 尝试保存参数，**Then** 显示错误提示并阻止保存
4. **Given** 用户配置 Broker 节点选择 OKX 类型，**When** 展开参数面板，**Then** 显示 OKX 特有配置项（API Key、Secret等）

---

### User Story 3 - 节点图验证与错误提示 (Priority: P2)

系统实时验证节点图的有效性，检测并提示配置错误（如循环依赖、必需参数缺失、类型不匹配）。

**Why this priority**: 提升用户体验，避免用户提交无效配置；可在前端独立实现验证逻辑。

**Independent Test**: 用户可以故意创建错误配置（如循环依赖、缺失参数），验证错误提示的准确性和位置指示。

**Acceptance Scenarios**:

1. **Given** 用户创建了循环依赖（A→B→C→A），**When** 系统检测到循环，**Then** 高亮显示循环涉及的节点和连接，显示错误提示
2. **Given** 用户未配置必需参数（如 Engine 缺少时间范围），**When** 尝试编译或保存，**Then** 节点显示红色边框和提示信息
3. **Given** 用户连接了不兼容的节点类型（如 Feeder 直接连到 Analyzer），**When** 系统检测到类型不匹配，**Then** 连接线显示为红色并显示错误原因
4. **Given** 节点图完全有效，**When** 用户触发验证，**Then** 显示"配置有效"提示并启用保存/运行按钮

---

### User Story 4 - 节点图保存与加载 (Priority: P2)

用户可以保存当前节点图配置，并从保存的配置列表中加载历史配置。

**Why this priority**: 使用户能够复用配置、对比不同策略、保留工作成果。

**Independent Test**: 用户可以保存节点图并重新加载，验证配置完整性和节点/参数还原正确性。

**Acceptance Scenarios**:

1. **Given** 用户完成节点图配置，**When** 点击保存并输入名称，**Then** 配置被保存到数据库，出现在"我的配置"列表中
2. **Given** 用户从配置列表选择一个保存的配置，**When** 点击加载，**Then** 画布还原为保存时的节点和参数状态
3. **Given** 用户修改已加载的配置，**When** 再次保存，**Then** 系统提示"覆盖保存"或"另存为新配置"
4. **Given** 用户删除一个保存的配置，**When** 确认删除，**Then** 配置从列表中移除

---

### User Story 5 - 节点图编译与回测任务创建 (Priority: P2)

系统将节点图编译为回测任务配置，发送到后端 API 创建回测任务。

**Why this priority**: 连接可视化配置与实际回测执行，是实现完整功能链路的关键步骤。

**Independent Test**: 用户可以编译节点图并查看生成的配置 JSON，验证编译逻辑正确性，无需实际运行回测。

**Acceptance Scenarios**:

1. **Given** 用户完成有效的节点图配置，**When** 点击"编译"按钮，**Then** 系统显示生成的回测配置 JSON 预览
2. **Given** 编译成功，**When** 用户点击"创建回测任务"，**Then** 任务被发送到后端 API，页面跳转到回测详情页
3. **Given** 编译过程中检测到错误，**When** 编译失败，**Then** 显示错误信息并阻止任务创建
4. **Given** 节点图包含多个 Portfolio 节点，**When** 编译配置，**Then** 生成的配置包含 portfolio_uuids 数组

---

### User Story 6 - 节点图模板与预设 (Priority: P3)

系统提供常用回测配置的节点图模板，用户可以基于模板快速创建配置。

**Why this priority**: 降低新用户学习成本，提升常用配置的创建效率。

**Independent Test**: 用户可以选择模板并加载到画布，验证模板节点和参数预填充正确性。

**Acceptance Scenarios**:

1. **Given** 用户打开创建页面，**When** 点击"从模板创建"，**Then** 显示模板列表（如"双均线策略"、"多因子策略"等）
2. **Given** 用户选择"双均线策略"模板，**When** 确认加载，**Then** 画布显示预配置的节点图（Strategy、RiskManagement、Feeder、Broker、Engine）
3. **Given** 基于模板加载的节点图，**When** 用户修改参数后保存，**Then** 保存为新配置而非覆盖模板
4. **Given** 管理员用户，**When** 创建新模板，**Then** 模板出现在模板列表中供其他用户使用

---

### Edge Cases

- **节点图大小限制**: 用户添加大量节点（>50个）时，系统性能和画布渲染如何处理？
- **并发编辑**: 多个用户同时编辑同一个保存的配置时，如何处理冲突？
- **节点类型变更**: 后端添加新的节点类型或参数时，前端如何兼容旧配置？
- **浏览器兼容性**: 不同浏览器对 Canvas/SVG 拖拽性能差异如何处理？
- **移动端支持**: 移动设备上如何处理拖拽操作（触摸事件）？
- **大图导航**: 当节点图超过画布可视区域时，如何提供缩放和平移功能？
- **撤销/重做**: 用户误操作节点时，如何支持撤销和重做功能？
- **跨组件拖拽**: 用户是否可以将一个配置中的节点拖拽到另一个配置？

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
- **FR-007**: System MUST 支持批量数据操作 (如 add_bars 而非单条插入)
- **FR-008**: System MUST 集成风险管理系统 (PositionRatioRisk, LossLimitRisk, ProfitLimitRisk)
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循 TDD 开发流程，先写测试再实现功能

**节点图核心功能需求**:
- **FR-011**: System MUST 提供可视化画布，支持节点拖拽和连接操作
- **FR-012**: System MUST 支持以下节点类型：Engine、Feeder、Broker、Portfolio、Strategy、Selector、Sizer、RiskManagement、Analyzer
- **FR-013**: System MUST 为每个节点类型提供对应的参数配置表单
- **FR-014**: System MUST 实时验证节点图的有效性（循环依赖、类型匹配、必需参数）
- **FR-015**: System MUST 将节点图编译为符合 BacktestTaskCreate API 的配置格式

**节点类型与参数需求**:
- **FR-016**: Engine 节点 MUST 支持配置：start_date、end_date、engine_uuid（可选）
- **FR-017**: Broker 节点 MUST 支持配置：broker_type（backtest/okx）、initial_cash、commission_rate、slippage_rate、broker_attitude
- **FR-018**: Portfolio 节点 MUST 支持选择多个已存在的 Portfolio 或创建新的 Portfolio
- **FR-019**: Strategy 节点 MUST 支持从可用策略列表选择并配置策略参数
- **FR-020**: RiskManagement 节点 MUST 支持添加多个风控组件（PositionRatioRisk、LossLimitRisk、ProfitLimitRisk）

**节点连接规则需求**:
- **FR-021**: System MUST 强制 Engine 节点作为根节点（无输入连接）
- **FR-022**: System MUST 要求至少一个 Portfolio 节点连接到 Engine
- **FR-023**: System MUST 支持一个 Engine 连接多个 Portfolio 节点
- **FR-024**: System MUST 支持 Strategy、Selector、Sizer、RiskManagement、Analyzer 节点连接到 Portfolio
- **FR-025**: System MUST 禁止创建循环依赖的连接

**数据持久化需求**:
- **FR-026**: System MUST 支持保存节点图配置到数据库（JSON 格式）
- **FR-027**: System MUST 支持从数据库加载已保存的节点图配置
- **FR-028**: System MUST 支持配置的命名、描述、创建时间、更新时间元数据
- **FR-029**: System MUST 支持配置的所有权（user_uuid）和共享设置

**用户体验需求**:
- **FR-030**: System MUST 提供节点拖拽时的视觉反馈（阴影、吸附效果）
- **FR-031**: System MUST 提供连接线绘制时的路径优化（避免穿过节点）
- **FR-032**: System MUST 支持画布缩放（10%-200%）和平移导航
- **FR-033**: System MUST 提供撤销/重做功能（至少 20 步历史）
- **FR-034**: System MUST 在节点上显示配置摘要（如策略名称、时间范围）

**代码维护与文档需求**:
- **FR-035**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-036**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-037**: Header updates MUST be verified during code review process

### Key Entities

- **NodeGraph**: 节点图配置实体，包含节点列表、连接列表、画布状态
  - `uuid`: 唯一标识符
  - `name`: 配置名称
  - `description`: 配置描述
  - `nodes`: 节点数组（id、type、position、parameters）
  - `connections`: 连接数组（sourceNodeId、sourcePort、targetNodeId、targetPort）
  - `user_uuid`: 所有者用户ID
  - `is_public`: 是否公开共享
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

- **NodeDefinition**: 节点类型定义实体，描述每种节点的输入输出端口和参数schema
  - `type`: 节点类型标识（如 "ENGINE"、"PORTFOLIO"）
  - `category`: 分类（如 "core"、"component"）
  - `label`: 显示名称
  - `description`: 节点功能描述
  - `input_ports`: 输入端口定义（name、type、required）
  - `output_ports`: 输出端口定义（name、type）
  - `parameters_schema`: 参数配置 schema（JSON Schema 格式）
  - `default_parameters`: 默认参数值

- **NodeTemplate**: 预设模板实体，包含常用配置的节点图模板
  - `uuid`: 唯一标识符
  - `name`: 模板名称
  - `description`: 模板描述
  - `node_graph`: 预配置的节点图数据
  - `category`: 模板分类（如 "trend_following"、"mean_reversion"）
  - `is_system`: 是否系统模板（不可删除）

## Success Criteria *(mandatory)*

### Measurable Outcomes

**节点图操作性能指标**:
- **SC-001**: 节点拖拽响应延迟 < 50ms（在画布包含 < 100 个节点时）
- **SC-002**: 连接线绘制实时更新率 > 60fps
- **SC-003**: 画布缩放操作响应时间 < 100ms
- **SC-004**: 节点图验证完成时间 < 500ms（50个节点规模）

**用户体验指标**:
- **SC-005**: 新用户创建第一个有效回测配置的时间 < 10 分钟
- **SC-006**: 配置保存/加载操作成功率 > 99%
- **SC-007**: 错误提示准确率 > 95%（正确识别配置错误且无误报）
- **SC-008**: 节点图编译成功率（有效配置）= 100%

**功能完整性指标**:
- **SC-009**: 支持的节点类型 >= 9 种（Engine、Feeder、Broker、Portfolio、Strategy、Selector、Sizer、RiskManagement、Analyzer）
- **SC-010**: 提供的预设模板 >= 5 个
- **SC-011**: 节点参数配置表单覆盖率 = 100%（所有节点类型都有配置面板）
- **SC-012**: 节点图编译配置与后端 API 兼容性 = 100%

**系统可靠性指标**:
- **SC-013**: 代码测试覆盖率 > 80%（单元测试+集成测试）
- **SC-014**: 浏览器兼容性支持（Chrome、Firefox、Safari、Edge 最新两个版本）
- **SC-015**: 节点图配置数据持久化成功率 > 99.9%
- **SC-016**: 并发编辑冲突检测准确率 = 100%

**业务价值指标**:
- **SC-017**: 使用节点图创建的回测任务占所有创建任务的比率 > 60%（功能上线后3个月内）
- **SC-018**: 用户配置复用率（从历史配置加载）> 40%
- **SC-019**: 模板使用率 > 30%
- **SC-020**: 配置错误率（编译失败的配置）< 10%

## Assumptions

1. **前端框架**: 使用 Vue 3 + TypeScript，项目已有 Ant Design Vue 组件库
2. **节点图库**: 使用 Vue Flow 或类似的 Vue 节点图库，而非从头实现
3. **API 兼容性**: 后端 Backtest API 已实现并稳定（参考 `/home/kaoru/Ginkgo/apiserver/api/backtest.py`）
4. **数据存储**: 使用现有的 MySQL 数据库，新增 `node_graphs` 和 `node_templates` 表
5. **用户系统**: 假设已实现用户认证和权限管理（JWT middleware 已存在）
6. **浏览器支持**: 优先支持现代浏览器（Chrome、Firefox、Safari、Edge），不强制支持 IE
7. **节点类型扩展性**: 设计支持未来添加新的节点类型而无需修改核心逻辑
8. **配置版本控制**: 初期不支持版本历史，但数据模型预留扩展能力
9. **协作功能**: 初期不支持多人实时协作编辑，但支持配置共享和只读查看
10. **移动端支持**: 优先实现桌面端体验，移动端支持作为未来增强功能

## Dependencies

1. **后端 API**: `/api/backtest/*` 接口已实现并可用
2. **Portfolio API**: `/api/portfolio/*` 接口用于获取可用 Portfolio 列表
3. **Components API**: `/api/components/*` 接口用于获取可用的策略、风控等组件
4. **数据库**: MySQL 服务运行正常，具备创建新表的权限
5. **认证服务**: JWT 认证中间件正常运行，可获取当前 user_uuid
6. **前端构建**: Vite 构建工具和 Vue 3 开发环境已配置

## Out of Scope

以下功能明确不在本功能范围内：

1. **回测执行监控**: 回测任务创建后的实时进度监控（已有其他功能实现）
2. **回测结果分析**: 回测完成后的结果可视化（已有其他功能实现）
3. **策略代码编辑**: 在节点图中直接编写策略代码（策略已通过 Components API 提供）
4. **实时协作**: 多用户同时编辑同一个节点图
5. **版本历史**: 节点图配置的版本控制和回滚
6. **导入导出**: 从文件系统导入或导出节点图配置（仅支持数据库存储）
7. **移动端优化**: 移动设备的触摸手势优化
8. **性能分析**: 节点图配置的性能预测和优化建议
9. **自动调参**: 基于节点图的参数优化功能
10. **回测对比**: 多个节点图配置的回测结果对比
