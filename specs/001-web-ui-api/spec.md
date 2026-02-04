# Feature Specification: Web UI and API Server

**Feature Branch**: `001-web-ui-api`
**Created**: 2026-01-27
**Status**: Draft
**Input**: User description: "构建网页端or跨平台ui界面，已经对应的API Server"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 实时监控仪表盘 (Priority: P1)

量化交易员通过网页界面实时查看市场数据、持仓状态、策略表现和系统健康状态，无需依赖命令行界面。

**Why this priority**: 这是用户与系统交互的主要入口，提供可视化的实时监控能力是量化交易系统的核心需求，直接影响交易决策和风险控制。

**Independent Test**: 可以通过访问网页仪表盘，验证数据展示的准确性和实时性，独立于其他功能进行完整测试。

**Acceptance Scenarios**:

1. **Given** 用户已登录系统，**When** 打开仪表盘页面，**Then** 显示实时持仓信息、净值曲线、今日盈亏和系统状态
2. **Given** 市场有新价格数据到达，**When** 数据更新事件触发，**Then** 仪表盘在2秒内自动刷新显示最新数据
3. **Given** 系统有风控预警触发，**When** 预警事件发生，**Then** 仪表盘以醒目方式显示警报信息
4. **Given** 多个Portfolio同时运行，**When** 用户打开仪表盘，**Then** 支持常用2-4个Portfolio分屏同时展示，Portfolio数量无限制时通过列表/标签页等方式展示
5. **Given** 用户在分屏模式下，**When** 选择或切换Portfolio，**Then** 分屏布局动态更新，支持2分屏、3分屏、4分屏切换
6. **Given** 用户点击某个Portfolio分屏，**When** 展开详情，**Then** 显示该Portfolio包含的策略列表及各策略的独立表现

---

### User Story 1.5 - Paper模拟盘模式 (Priority: P1)

回测完成后，用户希望先将策略部署到Paper模式（模拟盘），使用实时市场数据进行仿真交易，验证策略在实际市场条件下的表现后再决定是否进入实盘。

**Why this priority**: Paper模式是连接回测和实盘的桥梁，允许用户在不承担真实资金风险的情况下验证策略，是量化交易系统的关键风控环节。

**Independent Test**: 可以通过完成回测后启动Paper模式、监控Paper运行、转为Live模式的完整流程进行独立测试。

**Acceptance Scenarios**:

1. **Given** 用户查看已完成回测的详情页，**When** 点击"启动Paper模式"按钮，**Then** 系统创建Paper Portfolio，配置被锁死不可修改，使用实时市场数据模拟交易
2. **Given** Paper Portfolio正在运行，**When** 用户在分屏中查看其表现，**Then** 显示Paper模式标识（如"模拟盘"标签）、模拟持仓、模拟盈亏和实时更新
3. **Given** Paper Portfolio运行一段时间后表现符合预期，**When** 用户点击"转为实盘"按钮，**Then** 系统验证后创建Live Portfolio，原Paper配置复制到Live并开始真实资金交易
4. **Given** Paper Portfolio运行期间，**When** 用户尝试修改策略配置，**Then** 界面提示"Paper模式配置已锁死，如需修改请停止并重新回测"
5. **Given** Live Portfolio运行中表现不符合预期，**When** 用户停止该Portfolio，**Then** Portfolio进入停止状态，用户需回到策略研发阶段重新回测验证
6. **Given** Live Portfolio运行期间，**When** 用户尝试修改策略配置，**Then** 界面提示"Live模式配置已锁死，如需修改请停止并回到策略研发阶段"

---

### User Story 2 - 策略回测管理 (Priority: P1)

用户通过界面配置回测参数（时间范围、初始资金、策略选择、风控设置），启动回测任务，并查看详细的回测报告和性能指标。

**Why this priority**: 回测是策略开发验证的核心环节，提供可视化配置和结果分析大幅提升策略研发效率。

**Independent Test**: 可以通过创建回测任务、配置参数、执行回测、查看结果的完整流程进行独立测试。

**Acceptance Scenarios**:

1. **Given** 用户在回测配置页面，**When** 选择策略、设置时间范围和初始资金，**Then** 系统验证参数有效性并允许启动回测
2. **Given** 回测任务正在运行，**When** 任务执行完成，**Then** 用户收到通知并可查看详细报告（收益率、最大回撤、夏普比率等）
3. **Given** 用户查看历史回测记录，**When** 选择某个已完成回测，**Then** 显示完整的回测配置和结果数据
4. **Given** 用户查看已完成回测的详情页，**When** 点击"启动Paper模式"按钮，**Then** 系统创建Paper Portfolio，配置锁死，使用实时数据模拟交易
5. **Given** Paper Portfolio运行验证通过，**When** 用户点击"转为实盘"按钮，**Then** 系统创建Live Portfolio开始真实资金交易

---

### User Story 2.5 - 回测组件管理 (Priority: P1)

用户通过网页界面管理回测组件（Strategy策略、Selector选股器、Sizer仓位管理、RiskManager风控等），支持查看现有组件、创建自定义组件、编辑组件代码、删除组件等完整CRUD操作。

**Why this priority**: 组件管理是策略研发的核心基础设施。通过Web界面管理组件代码，用户可以快速创建和迭代策略，无需手动编辑文件，大幅提升策略研发效率。

**Independent Test**: 可以通过创建自定义策略、编辑代码、在回测中使用新组件、验证组件功能等完整流程独立测试。

**Acceptance Scenarios**:

1. **Given** 用户访问组件管理页面，**When** 查看组件列表，**Then** 显示所有回测组件（Strategy/Selector/Sizer/RiskManager/Analyzer），按类型分组展示
2. **Given** 用户创建新组件，**When** 选择组件类型、输入名称、编写Python代码，**Then** 系统验证代码语法、将组件代码保存到MFile表、返回组件ID
3. **Given** 用户编辑现有组件，**When** 在在线代码编辑器中修改代码，**Then** 系统保存更新后的代码、记录版本历史、标记组件需要重新测试
4. **Given** 用户在回测配置页面选择策略，**When** 查看可用策略列表，**Then** 显示所有已保存的Strategy组件（包括预置组件和用户自定义组件）
5. **Given** 组件代码存在语法错误，**When** 用户保存组件，**Then** 界面显示具体的错误信息和行号，阻止保存
6. **Given** 用户删除正在使用的组件，**When** 尝试删除，**Then** 系统提示"该组件正在被回测任务使用，无法删除"

---

### User Story 3 - 数据管理界面 (Priority: P1)

用户通过界面管理市场数据（股票信息、K线数据、Tick数据），包括数据更新、数据质量检查、数据范围查询等功能。

**Why this priority**: 数据是量化交易的基础，提供可视化的数据管理工具确保数据质量和可用性。

**Independent Test**: 可以通过数据查询、更新操作、质量检查等功能独立测试数据管理能力。

**Acceptance Scenarios**:

1. **Given** 用户访问数据管理页面，**When** 查询特定股票的K线数据，**Then** 显示数据覆盖范围和数据质量统计
2. **Given** 用户触发数据更新任务，**When** 任务执行完成，**Then** 显示更新结果（成功/失败记录、数据增量）
3. **Given** 数据存在质量问题，**When** 系统检测到异常，**Then** 在数据管理界面标注问题数据

---

### User Story 4 - 用户认证与权限管理 (Priority: P1)

用户通过用户名和密码登录系统，系统验证身份后返回访问令牌。管理员可以通过系统设置界面管理用户账户、重置密码、分配管理员权限。

**Why this priority**: 用户认证是系统安全的基础，支持多用户登录和权限管理是团队协作和系统管理的必要功能。

**Independent Test**: 可以通过用户注册、登录、密码修改、用户管理等完整流程独立测试认证功能。

**Acceptance Scenarios**:

1. **Given** 用户访问登录页面，**When** 输入正确的用户名和密码，**Then** 系统验证通过并返回JWT令牌，跳转到仪表盘
2. **Given** 用户输入错误的凭据，**When** 提交登录请求，**Then** 系统返回401错误并提示"用户名或密码错误"
3. **Given** 管理员访问用户管理页面，**When** 查看用户列表，**Then** 显示所有用户的用户名、显示名称、邮箱、角色和状态
4. **Given** 管理员创建新用户，**When** 输入用户名、密码、显示名称和邮箱，**Then** 系统创建用户账户和认证凭据，新用户可以登录
5. **Given** 管理员重置用户密码，**When** 确认重置操作，**Then** 系统生成新密码并返回给管理员，用户可用新密码登录
6. **Given** 用户访问受保护的API接口，**When** 未提供有效令牌，**Then** 系统返回401错误并提示"未授权访问"

---

### User Story 5 - API服务接口 (Priority: P1)

外部系统或前端应用通过RESTful API访问Ginkgo核心功能，包括数据查询、回测执行、策略管理、实时订阅等能力。

**Why this priority**: API是解耦前端和后端的关键，支持多种客户端（网页、移动端、第三方集成）访问系统能力。

**Independent Test**: 可以通过API客户端测试各接口的请求响应、数据格式、错误处理等功能。

**Acceptance Scenarios**:

1. **Given** API客户端发起认证请求，**When** 提供有效凭据，**Then** 返回访问令牌用于后续请求
2. **Given** 客户端查询历史K线数据，**When** 请求参数合法，**Then** 返回JSON格式的数据和时间范围信息
3. **Given** 客户端提交回测任务，**When** 任务创建成功，**Then** 返回任务ID用于后续状态查询
4. **Given** 客户端订阅实时数据推送，**When** 连接建立成功，**Then** 收到WebSocket实时数据流

---

### User Story 6 - 警报中心与历史 (Priority: P1)

用户通过警报中心查看实时风控警报和系统通知，查询历史警报记录，标记警报处理状态。

**Why this priority**: 警报中心是用户监控系统状态和风险事件的核心入口，提供实时警报和历史查询帮助用户快速响应和处理风险事件。

**Independent Test**: 可以通过触发风控警报、查看实时警报、查询历史记录、标记处理等功能独立测试。

**Acceptance Scenarios**:

1. **Given** 用户在警报中心页面，**When** 系统触发风控警报（如止损），**Then** 实时警报Tab显示新警报并高亮紧急程度
2. **Given** 用户查看历史警报记录，**When** 切换到历史记录Tab并选择时间范围，**Then** 显示指定时间范围内的所有警报，支持按类型、级别、状态筛选
3. **Given** 用户处理警报，**When** 点击"标记处理"按钮，**Then** 警报状态更新为"已处理"并从实时警报列表移除
4. **Given** 用户查看警报详情，**When** 点击"查看详情"，**Then** 显示警报的完整信息（触发时间、影响范围、处理建议）

---

### Edge Cases

- **用户认证相关**:
  - **用户名冲突**: 注册时用户名已存在时，返回409错误并提示"用户名已存在"
  - **密码强度**: 注册时密码长度最少6位，不符合要求时提示密码太短
  - **令牌过期**: JWT令牌过期后，API返回401错误，前端需引导用户重新登录
  - **密码重置**: 管理员重置用户密码后，系统生成随机密码并返回，用户需在首次登录后修改密码
  - **用户删除**: 删除用户时级联删除其认证凭据（MUserCredential），用户无法再登录
  - **账户禁用**: 禁用用户账户时，设置MUser.is_active=False和MUserCredential.is_active=False，用户无法登录
  - **管理员权限**: 仅管理员可访问用户管理接口，普通用户返回403错误
- **网络断线处理**: WebSocket连接断开时，界面显示离线状态并自动重连，重连后恢复数据订阅
- **大结果集分页**: 查询历史数据超过10000条记录时，自动分页显示并提供导出功能
- **并发回测限制**: 同时运行的回测任务超过系统资源限制时，排队执行并告知用户等待时间
- **数据缺失处理**: 查询的时间范围无数据时，明确提示用户并建议可用的时间范围
- **权限控制**: 未授权访问尝试时，API返回401错误并提供登录指引
- **实时数据延迟**: 市场数据延迟超过阈值时，界面显示数据延迟警告
- **多Portfolio同时监控**: 支持Portfolio横向扩展无数量限制，常用2-4个分屏展示，更多Portfolio通过列表/标签页/分页等方式管理
- **Portfolio状态变化**: 当某个Portfolio停止或新Portfolio启动时，分屏布局提供刷新提示或自动调整选项
- **Portfolio内策略管理**: 当Portfolio包含多个策略时，Portfolio级别的风控警报需要显示是哪个策略触发的风险事件
- **独立风控隔离**: 某个Portfolio触发风控（如止损）时，仅影响该Portfolio的持仓，不影响其他Portfolio的运行和持仓
- **跨Portfolio持仓冲突**: 当不同Portfolio持有同一股票时，各自独立记录持仓，风控和盈亏计算互不影响
- **跨Portfolio汇总视图**: 用户可选择"按股票汇总"视图查看所有Portfolio对同一股票的总敞口，但此视图仅用于信息展示，不影响各Portfolio的独立性
- **回测转实盘限制**: 回测任务必须处于"已完成"状态才能转换，进行中或失败的回测不支持转换
- **Portfolio运行模式流转**: 策略研发 → Backtest → Paper → Live，单向流转。Paper和Live模式配置均锁死
- **配置锁死提示**:
  - 用户尝试修改Paper Portfolio配置时，提示"Paper模式配置已锁死，如需修改请停止并重新回测"
  - 用户尝试修改Live Portfolio配置时，提示"Live模式配置已锁死，如需修改请停止并回到策略研发阶段"
- **Live不符合预期处理**: Live Portfolio如表现不符合预期，停止后必须回到策略研发阶段重新回测验证，不能直接修改配置
- **Paper转Live确认**: Paper转Live时需要用户明确确认，提示"即将进入实盘模式，真实资金将被使用"
- **组件语法验证**: 用户保存组件代码时，系统验证Python语法，如有错误显示具体行号和错误信息
- **组件删除限制**: 正在被回测任务或Portfolio使用的组件无法删除，必须先停止引用才能删除
- **组件版本管理**: 组件代码每次修改都保存版本历史，支持回滚到历史版本
- **预置组件保护**: 系统预置的组件（如SimpleBuyAndHold）不能修改或删除，只能查看和复制

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: API Server MUST 遵循事件驱动架构，通过ServiceHub访问核心服务
- **FR-002**: API层MUST 作为独立进程运行，通过Kafka与交易核心解耦
- **FR-003**: UI层MUST 仅通过API与后端交互，不直接访问数据库或核心服务
- **FR-004**: System MUST 使用`@time_logger`监控API响应时间，使用`@retry`处理数据库连接失败
- **FR-005**: API接口MUST 提供完整的类型注解和OpenAPI文档

**Web UI功能需求**:
- **FR-006**: UI MUST 提供实时监控仪表盘，显示持仓、净值、盈亏、系统状态
- **FR-006.1**: UI MUST 支持Portfolio横向扩展，无数量限制，支持分屏（常用2-4个）、列表、标签页等多种展示方式
- **FR-006.2**: UI MUST 支持分屏布局切换（2分屏、3分屏、4分屏），并保持各分屏数据独立刷新
- **FR-006.3**: UI MUST 支持在Portfolio分屏中展开查看其包含的策略列表及各策略表现
- **FR-006.4**: UI MUST 支持可选的"按股票汇总"视图，显示跨Portfolio的整体股票敞口（各Portfolio独立持仓+汇总数据）
- **FR-006.5**: UI MUST 显示Portfolio运行模式标识（Backtest/Paper/Live），Paper模式显示"模拟盘"标签，Live模式显示"实盘"标签
- **FR-006.6**: UI MUST 在Paper和Live模式下锁死配置修改入口，配置锁死状态下不提供编辑功能
- **FR-007**: UI MUST 支持策略回测配置（参数设置、任务管理、结果查看）
- **FR-008**: UI MUST 提供数据管理界面（数据查询、更新、质量检查）
- **FR-009**: UI MUST 提供警报中心，支持查看实时警报和历史记录，支持标记处理状态
- **FR-009.1**: UI MUST 支持Portfolio详情页配置风控参数（止损、止盈、仓位限制），仅策略研发阶段可修改
- **FR-009.2**: UI MUST 支持Portfolio包含多个策略，显示Portfolio整体风险及各策略的风险贡献
- **FR-010**: UI MUST 响应式设计，支持桌面和移动设备访问
- **FR-011**: UI MUST 提供回测组件管理界面（Strategy/Selector/Sizer/RiskManager/Analyzer），支持组件的CRUD操作和在线代码编辑
- **FR-011.1**: UI MUST 支持查看组件列表，按组件类型（STRATEGY/SELECTOR/SIZER/RISKMANAGER/ANALYZER）分组展示
- **FR-011.2**: UI MUST 支持创建自定义组件，提供在线代码编辑器（支持Python语法高亮和行号）
- **FR-011.3**: UI MUST 支持编辑现有组件代码，保存时验证Python语法并记录版本历史
- **FR-011.4**: UI MUST 支持删除未使用的组件，正在使用的组件必须先停止引用才能删除

**API Server功能需求**:
- **FR-012**: API MUST 提供RESTful接口用于数据查询（股票信息、K线、Tick、回测结果）
- **FR-013**: API MUST 提供WebSocket接口用于实时数据推送（价格更新、持仓变化、系统事件）
- **FR-014**: API MUST 支持回测任务管理（创建、启动、停止、查询状态、获取结果）
- **FR-014.1**: API MUST 支持回测转Paper模式接口，创建Paper Portfolio（配置锁死，实时数据模拟）
- **FR-014.2**: API MUST 支持Paper转Live模式接口，将验证通过的Paper Portfolio转为Live Portfolio（真实资金交易）
- **FR-015**: API MUST 提供数据管理接口（数据更新、质量检查、范围查询）
- **FR-016**: API MUST 提供警报查询接口（实时警报、历史记录、标记处理状态）
- **FR-017**: API MUST 提供Portfolio风控配置接口（仅策略研发阶段可修改）

**用户认证与权限管理需求**:
- **FR-018**: API MUST 实现基于JWT的用户认证机制，支持多用户登录
- **FR-018.1**: API MUST 在用户创建时自动创建认证凭据，默认密码与用户名一致
- **FR-018.2**: API MUST 支持用户注册接口，同时创建MUser和MUserCredential记录
- **FR-018.3**: API MUST 支持用户登录接口，验证用户名和密码后返回JWT令牌
- **FR-018.4**: API MUST 支持密码修改接口，验证旧密码后更新新密码
- **FR-018.5**: API MUST 支持密码重置接口，管理员可重置任意用户的密码
- **FR-019**: API MUST 提供用户管理接口（列表、创建、更新、删除用户）
- **FR-019.1**: API MUST 支持管理员分配用户角色（普通用户/管理员）
- **FR-019.2**: API MUST 支持启用/禁用用户账户
- **FR-020**: API MUST 实现令牌中间件，验证受保护接口的访问权限
- **FR-021**: 密码MUST 使用bcrypt哈希存储，不以明文形式保存

**性能与可靠性需求**:
- **FR-019**: API响应时间 MUST < 500ms (95th percentile) for 数据查询接口
- **FR-020**: WebSocket消息延迟 MUST < 100ms for 实时数据推送
- **FR-021**: API MUST 支持100并发用户同时访问
- **FR-022**: API MUST 提供请求限流机制（防止滥用，按用户/IP限制）
- **FR-023**: System MUST 记录所有API访问日志（用于审计和性能分析）

**跨平台支持需求**:
- **FR-024**: UI MUST 使用现代前端框架支持组件化开发和状态管理
- **FR-025**: UI MUST 支持离线访问能力（本地缓存、后台数据同步）
- **FR-026**: UI MUST 在桌面和移动设备上提供一致的用户体验

**安全需求**:
- **FR-027**: API MUST 实现HTTPS加密传输
- **FR-028**: API MUST 防止常见安全漏洞（SQL注入、XSS、CSRF）
- **FR-029**: 敏感配置MUST 通过环境变量或加密配置文件管理
- **FR-030**: API MUST 实现CORS策略，控制跨域访问

**代码维护与文档需求**:
- **FR-031**: API接口MUST 包含完整的API文档（接口定义、参数说明、示例代码）
- **FR-032**: UI组件MUST 包含交互式文档（组件示例、属性说明、使用指南）
- **FR-033**: Code files MUST include three-line headers (Upstream/Downstream/Role)

### Key Entities *(include if feature involves data)*

**用户与认证实体**:
- **MUser**: 用户实体，包含uuid、username（登录用户名，唯一）、display_name（显示名称）、email（邮箱地址）、description（用户描述）、user_type（用户类型：PERSON/CHANNEL/ORGANIZATION）、is_active（是否激活）、source（数据来源）、credential（一对一关联MUserCredential）
- **MUserCredential**: 用户认证凭证实体，包含uuid、user_id（外键关联MUser.uuid）、password_hash（bcrypt密码哈希）、is_active（是否可登录）、is_admin（是否管理员）、last_login_at（最后登录时间）、last_login_ip（最后登录IP），与MUser一对一关联，删除MUser时级联删除

**交易与回测实体**:
- **BacktestJob**: 回测任务实体，包含配置参数（策略、时间范围、资金）、执行状态、结果数据
- **Portfolio**: 投资组合实体（顶层概念），包含Portfolio名称、**运行模式（mode: Backtest/Paper/Live）**、状态、实时持仓、净值曲线、盈亏统计、**配置锁死状态（config_locked，Paper和Live模式下为true）**、**独立风控配置（risk_config）**、**策略列表（strategies，n个策略的集合）**
- **Strategy**: 策略实体（Portfolio的组成部分），包含策略名称、类型、状态、**所属Portfolio（portfolio_id）**、独立表现指标
- **MFile**: 组件文件实体，存储回测组件的Python代码，包含name（文件名）、type（组件类型：STRATEGY/SELECTOR/SIZER/RISKMANAGER/ANALYZER/ENGINE/HANDLER）、data（二进制代码内容）
- **Component**: 回测组件实体（MFile的UI抽象），包含组件ID、名称、类型（STRATEGY/SELECTOR/SIZER/RISKMANAGER/ANALYZER）、代码内容、版本历史、创建时间、是否为预置组件
- **PortfolioView**: 持仓视图实体，用于UI展示，关联Portfolio及其包含的策略数据
- **RiskAlert**: 风控警报实体，包含警报类型、**所属Portfolio（portfolio_id）**、触发时间、影响范围、处理状态
- **DataQualityReport**: 数据质量报告实体，包含数据覆盖范围、缺失统计、质量评分
- **APISession**: API会话实体，包含Token、过期时间、权限范围、访问日志

## Success Criteria *(mandatory)*

### Measurable Outcomes

**用户体验指标**:
- **SC-001**: 用户可以在5分钟内完成回测任务配置和启动（从登录到查看结果）
- **SC-002**: 仪表盘数据刷新延迟 < 2秒（用户感知的实时性）
- **SC-003**: 界面操作响应时间 < 500ms（用户点击反馈）
- **SC-004**: 新用户上手时间 < 15分钟（通过引导和文档）

**API性能指标**:
- **SC-005**: API 95th percentile响应时间 < 500ms
- **SC-006**: WebSocket消息延迟 < 100ms
- **SC-007**: API可用性 > 99.5%（月度统计）
- **SC-008**: API并发支持 >= 100用户

**功能完整性指标**:
- **SC-009**: 核心功能覆盖率达到100%（仪表盘、回测、数据管理、风控）
- **SC-010**: API文档覆盖率 = 100%（所有公开接口）
- **SC-011**: UI自动化测试覆盖率 > 70%

**跨平台兼容性指标**:
- **SC-012**: UI支持主流浏览器（最新两个版本的Chrome、Firefox、Safari、Edge）
- **SC-013**: UI在移动设备上的可用性评分 > 90/100
- **SC-014**: 离线模式下基本功能可用性 > 70%

**安全与合规指标**:
- **SC-015**: 零已知安全漏洞（通过安全扫描工具验证）
- **SC-016**: 所有API接口通过认证授权测试
- **SC-017**: 敏感数据加密覆盖率 = 100%（传输和存储）

**业务价值指标**:
- **SC-018**: 相比命令行界面，策略研发效率提升 > 50%（通过用户调研验证）
- **SC-019**: 用户满意度评分 > 4.0/5.0
- **SC-020**: 用户活跃度：每周活跃用户 > 80%的注册用户

## Assumptions

1. **用户模型**: 多用户系统，支持用户注册、登录、权限管理。MUser存储用户基本信息（username、display_name、email），MUserCredential存储认证凭证（password_hash、is_admin），一对一关联
2. **Portfolio模型**: 支持多Portfolio同时运行，每个Portfolio包含n个策略组合，Portfolio数量横向扩展无限制
3. **Portfolio运行模式**: Backtest（回测）→ Paper（模拟盘）→ Live（实盘），单向流转，Paper和Live配置锁死
4. **部署环境**: API Server和UI部署在同一服务器或容器，使用反向代理服务
5. **数据存储**: 使用现有的ClickHouse、MySQL、MongoDB、Redis，无需额外数据库
6. **实时通信**: WebSocket用于实时数据推送，Kafka作为内部消息总线
7. **认证方式**: 使用JWT Token进行无状态认证，支持多用户登录和权限控制
8. **密码安全**: 密码使用bcrypt哈希存储，注册时默认密码与用户名一致
9. **数据量**: UI主要展示汇总数据和分页数据，不直接处理千万级原始数据
10. **移动端**: 使用响应式Web设计，通过浏览器在移动设备上访问

## Dependencies

1. **现有Ginkgo核心**: API Server依赖完整的事件驱动回测引擎、数据服务、风控系统
2. **Kafka服务**: 实时数据推送依赖Kafka消息队列
3. **数据库服务**: ClickHouse、MySQL、MongoDB、Redis必须正常运行
4. **反向代理**: Nginx或Apache用于HTTPS终止和静态文件服务

## Clarifications

### Session 2026-01-28
- Q: 实时监控应如何支持多个Portfolio同时运行？ → A: 分屏对比 - 支持2-4个Portfolio分屏同时展示（常用场景），系统支持Portfolio横向扩展无数量限制，通过列表/标签页/分页等方式管理更多Portfolio
- Q: 多个Portfolio同时运行时，风控管理如何处理？ → A: Portfolio级独立风控 - 每个Portfolio有独立的风控配置，Portfolio间互不影响
- Q: 当不同Portfolio持有同一只股票时，UI应如何展示这种持仓关系？ → A: 独立展示+可选汇总 - 各Portfolio独立展示，提供可选的"按股票汇总"视图
- Q: 用户是否可以在UI中启动/停止实时运行的Portfolio？ → A: 仅查看状态 - UI仅显示Portfolio运行状态
- Q: 回测完成后，用户能否将回测配置直接转换为实时运行的Portfolio？ → A: 支持一键转换 - 复用Ginkgo已有的回测转Live逻辑
- Q: 关于"回测对比"功能的优先级？ → A: 保留P1优先级 - 第一版就必须实现回测对比功能，支持多个回测任务的性能指标对比和净值曲线叠加展示
- **关键架构澄清**:
  - Portfolio数量：支持横向扩展，无硬编码数量限制（2-4分屏是常用展示方式）
  - Portfolio运行模式：策略研发 → Backtest（回测）→ Paper（模拟盘，配置锁死）→ Live（实盘，配置锁死）
  - 配置锁死：Paper和Live模式配置均锁死，如需修改必须回退到策略研发阶段重新回测
  - 不符合预期处理：Live模式如不符合预期，停止后回到策略研发阶段，重新回测验证
  - 回测对比：P1优先级功能，第一版必须支持多个回测的对比分析（指标对比表格 + 净值曲线叠加）

### Session 2026-01-31
- Q: Web项目构建执行方式？ → A: 用户手动执行 - Web前端项目（web-ui/）的构建步骤由用户手动执行，不在自动化任务中包含npm install/pnpm build等命令

## Development & Troubleshooting

### Log Files

遇到 Web UI 或 API Server 问题时，优先查看以下日志文件：

| 日志文件 | 路径 | 用途 |
|---------|------|------|
| Vite 开发日志 | `/tmp/vite-dev.log` | 前端编译错误、HMR 更新状态、Vue 组件语法错误 |
| API Server 日志 | `/tmp/apiserver-dev.log` | 后端 API 错误、数据库连接问题、请求处理异常 |

### 常见问题排查流程

1. **前端编译错误**
   - 症状：网页空白、组件不显示
   - 排查：查看 `/tmp/vite-dev.log`，搜索 `[vue/compiler-sfc]` 或 `Unexpected token`
   - 常见原因：TypeScript 语法错误、Python 语法混入（如 `try:` 应为 `try {`）

2. **API 接口错误**
   - 症状：数据加载失败、接口返回 500
   - 排查：查看 `/tmp/apiserver-dev.log`，搜索 `ERROR` 或 `Traceback`
   - 常见原因：数据库连接失败、ORM 查询错误、权限问题

3. **实时数据不更新**
   - 症状：仪表盘数据静止
   - 排查：检查 WebSocket 连接状态、Kafka 消息队列状态
   - 日志：查看 API Server 日志中的 WebSocket 相关输出

### 开发注意事项

- **前端语法**: 使用 TypeScript/JavaScript 语法，注意不要混入 Python 语法（如 `try:` 应为 `try {`）
- **API 调试**: 使用浏览器开发者工具 Network 面板查看请求/响应
- **热更新**: Vite 支持 HMR，修改代码后自动刷新，无需手动重启

## Implementation Status

### 已完成功能 (Completed)

#### 用户管理模块 (User Management)
- **状态**: ✅ 已完成
- **实现日期**: 2026-01-31
- **相关文件**:
  - API: `/home/kaoru/Ginkgo/apiserver/api/settings.py`
  - 前端: `/home/kaoru/Ginkgo/web-ui/src/views/Settings/UserManagement.vue`
  - 接口定义: `/home/kaoru/Ginkgo/web-ui/src/api/modules/settings.ts`

**功能列表**:
1. **用户CRUD操作**
   - 用户列表展示（支持搜索、状态筛选）
   - 创建用户（用户名、密码、显示名称、邮箱、角色、状态）
   - 编辑用户（显示名称、邮箱、角色、状态）
   - 删除用户（软删除，级联删除认证凭据）
   - 重置密码（重置为与用户名相同的初始值）

2. **联系方式管理**
   - 联系方式列表展示（邮箱/Webhook）
   - 创建联系方式
   - 编辑联系方式
   - 删除联系方式
   - 测试联系方式（发送测试通知）
   - 设置主要联系方式
   - 启用/禁用联系方式
   - 点击地址复制到剪贴板

3. **数据模型**
   - `MUser`: 用户基本信息（username, display_name, email）
   - `MUserCredential`: 认证凭据（password_hash, is_admin, is_active）
   - `MUserContact`: 联系方式（contact_type, address, is_primary, is_active）

4. **API端点**
   - `GET /settings/users` - 获取用户列表
   - `POST /settings/users` - 创建用户
   - `PUT /settings/users/{uuid}` - 更新用户
   - `DELETE /settings/users/{uuid}` - 删除用户
   - `POST /settings/users/{uuid}/reset-password` - 重置密码
   - `GET /settings/users/{user_uuid}/contacts` - 获取联系方式列表
   - `POST /settings/users/{user_uuid}/contacts` - 创建联系方式
   - `PUT /settings/users/contacts/{contact_uuid}` - 更新联系方式
   - `DELETE /settings/users/contacts/{contact_uuid}` - 删除联系方式
   - `POST /settings/users/contacts/{contact_uuid}/test` - 测试联系方式
   - `POST /settings/users/contacts/{contact_uuid}/set-primary` - 设置主要联系方式

#### 用户组管理模块 (User Group Management)
- **状态**: ✅ 已完成
- **实现日期**: 2026-01-31
- **相关文件**:
  - API: `/home/kaoru/Ginkgo/apiserver/api/settings.py`
  - 前端: `/home/kaoru/Ginkgo/web-ui/src/views/Settings/UserGroupManagement.vue`
  - 接口定义: `/home/kaoru/Ginkgo/web-ui/src/api/modules/settings.ts`

**功能列表**:
1. **用户组CRUD操作**
   - 用户组列表展示
   - 创建用户组（组名称、描述）
   - 编辑用户组（组名称、描述）
   - 删除用户组（软删除，级联删除映射关系）

2. **权限配置**
   - 权限选择器（前端UI已实现）
   - 权限数组存储（暂未实现后端权限验证）

3. **用户统计**
   - 自动统计组内用户数量
   - 通过 MUserGroupMapping 表查询

4. **数据模型**
   - `MUserGroup`: 用户组（name, description, is_active）
   - `MUserGroupMapping`: 用户-组映射（user_uuid, group_uuid）

5. **API端点**
   - `GET /settings/user-groups` - 获取用户组列表
   - `POST /settings/user-groups` - 创建用户组
   - `PUT /settings/user-groups/{uuid}` - 更新用户组
   - `DELETE /settings/user-groups/{uuid}` - 删除用户组
   - `GET /settings/user-groups/{group_uuid}/members` - 获取组成员列表
   - `POST /settings/user-groups/{group_uuid}/members` - 添加用户到组
   - `DELETE /settings/user-groups/{group_uuid}/members/{user_uuid}` - 从组移除用户

**备注**: 权限功能暂时保留在前端UI中，后端返回空权限数组，完整的权限验证系统待后续实现。

#### 通知管理模块 (Notification Management)
- **状态**: ✅ 已完成
- **实现日期**: 2026-01-31
- **相关文件**:
  - API: `/home/kaoru/Ginkgo/apiserver/api/settings.py`
  - 前端: `/home/kaoru/Ginkgo/web-ui/src/views/Settings/NotificationManagement.vue`
  - 接口定义: `/home/kaoru/Ginkgo/web-ui/src/api/modules/settings.ts`

**功能列表**:
1. **通知模板管理**
   - 模板列表展示（类型、主题、启用状态）
   - 创建通知模板
   - 编辑通知模板
   - 删除通知模板
   - 切换模板启用状态
   - 测试通知模板

2. **通知历史查询**
   - 历史记录列表展示（类型、主题、接收人、状态、时间）
   - 按类型筛选
   - 分页查询
   - 查看通知详情

3. **数据模型**
   - `MNotificationTemplate`: 通知模板（template_id, template_name, template_type, subject, content, is_active）
   - `MNotificationRecord`: 通知记录（message_id, content, channels, status, channel_results）

4. **API端点**
   - `GET /settings/notifications/templates` - 获取通知模板列表
   - `POST /settings/notifications/templates` - 创建通知模板
   - `PUT /settings/notifications/templates/{uuid}` - 更新通知模板
   - `DELETE /settings/notifications/templates/{uuid}` - 删除通知模板
   - `PATCH /settings/notifications/templates/{uuid}` - 切换模板启用状态
   - `POST /settings/notifications/templates/{uuid}/test` - 测试通知模板
   - `GET /settings/notifications/history` - 获取通知历史记录

**备注**: 接收人管理功能保留前端UI，后端待实现。测试通知功能框架已实现，实际发送逻辑待完善。

## Out of Scope

- 原生移动应用开发（iOS/Android）
- 多用户租户隔离和复杂权限管理
- 社交功能（用户分享、评论、协作）
- 支付和订阅管理
- 机器学习模型训练界面（未来可扩展）
- 高频交易微秒级延迟优化（当前目标是毫秒级）
