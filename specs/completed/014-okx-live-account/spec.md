# Feature Specification: OKX实盘账号API接入

**Feature Branch**: `014-okx-live-account`
**Created**: 2026-03-12
**Status**: Draft
**Input**: User description: "接入实盘账号API，配置关联实盘模块与页面，以OKX为例"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 实盘账号配置与连接 (Priority: P1)

用户需要在系统中配置OKX交易所的API密钥，建立与实盘账户的连接，以便后续进行自动化交易。

**Why this priority**: 这是所有实盘交易功能的基础，没有账号连接就无法进行任何实盘操作。

**Independent Test**: 可以通过创建账号配置、验证连接状态、测试API调用三个步骤独立测试，成功后用户可以看到账户余额信息。

**Acceptance Scenarios**:

1. **Given** 用户已登录系统，**When** 进入实盘账号配置页面输入OKX API Key/Secret/Passphrase，**Then** 系统验证凭证有效性并显示"连接成功"状态
2. **Given** 用户输入错误的API凭证，**When** 点击"测试连接"，**Then** 系统显示具体错误信息（如"API Key无效"、"IP未白名单"等）
3. **Given** 用户已配置OKX账号，**When** 刷新账户信息，**Then** 系统显示实时账户余额、持仓、可用保证金等信息
4. **Given** 用户配置多个OKX账号，**When** 切换当前活动账号，**Then** 系统正确显示选中账号的信息

---

### User Story 2 - 实盘下单与持仓管理 (Priority: P2)

用户通过策略信号自动下单到OKX交易所，并实时同步持仓状态，实现自动化交易。

**Why this priority**: 这是实盘交易的核心功能，实现了从策略到实盘的完整链路。

**Independent Test**: 可以通过创建测试订单、验证订单状态同步、检查持仓更新来独立测试。

**Acceptance Scenarios**:

1. **Given** 策略生成买入信号且账户有足够余额，**When** 系统向OKX提交市价单，**Then** 订单成功成交且持仓增加
2. **Given** 订单已提交但未成交，**When** OKX返回部分成交状态，**Then** 系统正确更新持仓为部分成交状态
3. **Given** 用户主动取消挂单，**When** 系统向OKX发送取消请求，**Then** 订单状态变为"已撤销"且冻结资金解冻
4. **Given** OKX返回订单失败（如余额不足），**When** 系统接收错误响应，**Then** 记录失败原因并生成告警

---

### User Story 3 - 实盘风控与告警 (Priority: P2)

系统实时监控实盘账户的风险指标，当触发风控条件时自动采取措施并通知用户。

**Why this priority**: 实盘交易涉及真实资金，风控是必要的保护机制。

**Independent Test**: 可以通过设置风控阈值、触发风控条件、验证系统响应来独立测试。

**Acceptance Scenarios**:

1. **Given** 设置单笔交易金额上限为1000 USDT，**When** 策略生成1500 USDT的订单，**Then** 系统自动将订单金额调整为1000 USDT或拒绝订单
2. **Given** 设置日亏损上限为5%，**When** 当日累计亏损达到5%，**Then** 系统自动停止新订单并发送告警通知
3. **Given** 设置持仓占比上限为80%，**When** 持仓占比达到80%，**Then** 系统拒绝新的开仓订单
4. **Given** API连接异常中断，**When** 系统检测到连接断开，**Then** 停止所有交易活动并通知用户

---

### User Story 4 - 多交易所账号管理 (Priority: P3)

用户可以配置多个交易所的实盘账号（OKX、Binance等），并为不同的Portfolio绑定不同的交易所账号。

**Why this priority**: 提供扩展性，支持用户在不同交易所进行交易。

**Independent Test**: 可以通过添加不同交易所账号、为Portfolio分配账号、并发运行多个Portfolio来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户已配置OKX账号，**When** 添加Binance账号，**Then** 系统正确识别交易所类型并存储配置
2. **Given** 用户配置了OKX和Binance两个账号，**When** 查看账号列表，**Then** 系统显示所有账号及其状态（已连接/未连接/已绑定）
3. **Given** 用户创建多个Portfolio，**When** 为每个Portfolio绑定不同的交易所账号，**Then** 每个Portfolio独立运行并通过绑定账号进行交易
4. **Given** 某个Portfolio绑定的交易所账号连接失败，**When** 其他Portfolio正常运行，**Then** 系统继续处理正常Portfolio的订单，仅对失败Portfolio发送告警

---

### User Story 5 - 实盘交易历史与报表 (Priority: P3)

用户可以查看实盘交易历史记录，包括成交明细、资金流水、盈亏统计等，用于分析和复盘。

**Why this priority**: 帮助用户了解交易表现，优化策略。

**Independent Test**: 可以通过执行交易、查询历史记录、生成报表来独立测试。

**Acceptance Scenarios**:

1. **Given** 用户执行了多笔实盘交易，**When** 查看交易历史页面，**Then** 系统显示所有成交记录（时间、品种、方向、价格、数量、手续费）
2. **Given** 用户选择日期范围，**When** 查询历史记录，**Then** 系统正确过滤并显示该时间段内的交易
3. **Given** 用户查看统计报表，**When** 选择"按日汇总"，**Then** 系统显示每日的成交金额、盈亏、手续费等汇总数据
4. **Given** 用户导出交易记录，**When** 点击"导出CSV"，**Then** 系统生成包含所有字段的CSV文件

---

### Edge Cases

- 当OKX API返回限流错误（429）时，系统如何处理？
- 当网络中断导致订单状态不确定时，系统如何恢复一致性？
- 当用户在同一时间从多个渠道发起订单操作时，如何防止冲突？
- 当交易所维护或紧急停止交易时，系统如何响应？
- 当API密钥权限不足（如只有只读权限）时，系统如何提示？
- 当交易对不存在或暂停交易时，系统如何处理？
- 当订单金额超过交易所最大限制时，系统如何拆分或拒绝？
- 当Broker实例崩溃无响应时，如何检测和恢复？
- 当数据库中账号配置被删除或禁用时，正在运行的Broker实例如何处理？
- 当Portfolio被删除时，绑定的Broker实例如何处理？
- 当用户尝试将一个已绑定的LiveAccount分配给另一个Portfolio时，系统如何提示？

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import service_hub`访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**量化交易特有需求**:
- **FR-006**: System MUST 支持多数据源接入 (ClickHouse/MySQL/MongoDB/Redis)
- **FR-007**: System MUST 支持批量数据操作 (如add_bars而非单条插入)
- **FR-008**: System MUST 集成风险管理系统 (PositionRatioRisk, LossLimitRisk等)
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循TDD开发流程，先写测试再实现功能
- **FR-011**: 实盘交易 MUST 复用回测数据模型（Bar/Position/Order），仅通过可选扩展字段区分实盘特有属性

**DTO消息队列原则**:
- **FR-012**: System MUST 所有 Kafka 消息发送使用 DTO 包装（Pydantic BaseModel 实现）
- **FR-013**: 发送端 MUST 使用 DTO.model_dump_json() 序列化消息
- **FR-014**: 接收端 MUST 使用 DTO(**data) 反序列化消息
- **FR-015**: DTO MUST 提供 Commands 常量类定义命令/事件类型
- **FR-016**: DTO MUST 提供 is_xxx() 方法进行类型判断
- **FR-017**: 禁止直接发送字典或裸 JSON 字符串到 Kafka

**实盘账号管理需求**:
- **FR-018**: System MUST 支持用户配置、存储、查询实盘账号信息（交易所类型、API凭证）
- **FR-019**: System MUST 对API凭证进行加密存储（使用系统加密服务）
- **FR-020**: System MUST 验证API凭证有效性（测试连接、检查权限）
- **FR-021**: System MUST 支持账号的启用/禁用状态切换
- **FR-022**: System MUST 支持多个同一交易所的不同账号配置
- **FR-023**: System MUST 从数据库加载Broker配置（而非从配置文件）
- **FR-024**: System MUST 在实盘引擎启动时批量创建所有实盘Portfolio的Broker实例
- **FR-025**: System MUST 支持Broker实例的动态生命周期管理（Portfolio的live_account_id变更时销毁旧实例、创建新实例）
- **FR-026**: System MUST 维护Broker实例心跳检测，自动检测崩溃实例
- **FR-027**: System MUST 自动重启崩溃的Broker实例
- **FR-028**: System MUST 在Broker重启后进行数据完整性校验（同步余额、持仓、订单状态）后再继续交易

**实盘交易需求**:
- **FR-029**: System MUST 支持向交易所提交市价单和限价单
- **FR-030**: System MUST 使用WebSocket实时推送订单状态（待成交、部分成交、完全成交、已撤销、失败）
- **FR-031**: System MUST 使用WebSocket实时推送持仓信息（数量、可用数量、平均成本）
- **FR-032**: System MUST 使用WebSocket实时推送账户余额（总资产、可用余额、冻结资金）
- **FR-033**: System MUST 定时进行全量数据校验（如每30秒）确保数据一致性
- **FR-034**: System MUST 在WebSocket断开时自动切换到轮询模式
- **FR-035**: System MUST 处理交易所限流错误（自动重试、延迟重试）
- **FR-036**: System MUST 处理网络超时和连接异常（重连机制、告警通知）
- **FR-037**: System MUST 记录所有API调用日志（请求、响应、耗时）
- **FR-038**: System MUST 记录所有交易操作到数据库（用于审计和分析）

**实盘风控需求**:
- **FR-039**: System MUST 支持配置单笔交易金额上限
- **FR-040**: System MUST 支持配置日亏损上限（百分比或绝对值）
- **FR-041**: System MUST 支持配置持仓占比上限
- **FR-042**: System MUST 在触发风控时自动停止交易
- **FR-043**: System MUST 在触发风控时发送告警通知
- **FR-044**: System MUST 支持紧急停止功能（一键停止所有实盘交易）

**Web UI需求**:
- **FR-045**: System MUST 提供实盘账号配置页面（添加、编辑、删除、测试连接）
- **FR-046**: System MUST 提供账户信息展示页面（余额、持仓、今日盈亏）
- **FR-047**: System MUST 提供交易历史查询页面（成交记录、资金流水）
- **FR-048**: System MUST 提供风控配置页面（设置阈值、查看触发记录）
- **FR-049**: System MUST 提供实盘交易控制面板（启动/停止/暂停/恢复/紧急停止）
- **FR-050**: System MUST 支持单Portfolio独立控制（每个实盘Portfolio可单独启动/停止/暂停/恢复）
- **FR-051**: System MUST 支持全局紧急停止（一键停止所有实盘Portfolio）

**代码维护与文档需求**:
- **FR-052**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-053**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-054**: Header updates MUST be verified during code review process
- **FR-055**: CI/CD pipeline MUST include header accuracy verification

**配置验证需求**:
- **FR-056**: 配置类功能验证 MUST 包含配置文件存在性检查（不仅检查返回值）
- **FR-057**: 配置类验证 MUST 确认值从配置文件读取，而非代码默认值
- **FR-058**: 配置类验证 MUST 确认用户可通过修改配置文件改变行为
- **FR-059**: 配置类验证 MUST 确认缺失配置时降级到默认值
- **FR-060**: 外部依赖验证 MUST 包含存在性、正确性、版本兼容性三维度检查
- **FR-061**: 禁止仅因默认值/Mock使测试通过就认为验证完成（假阳性预防）

### Key Entities

- **LiveAccount**: 实盘账号配置信息
  - 账户ID、用户ID、交易所类型（OKX/Binance等）
  - API凭证（加密存储的API Key、Secret、Passphrase）
  - 账户状态（启用/禁用/连接中/断开）
  - 环境类型（生产/测试网）
  - 创建时间、更新时间

- **MPortfolio (扩展)**: 投资组合实体，新增实盘账号绑定
  - **新增字段**：`live_account_id` - 外键关联到LiveAccount（一对一绑定）
  - **绑定约束**：一个Portfolio只能绑定一个LiveAccount，一个LiveAccount只能被一个Portfolio绑定
  - 现有字段：name, mode, state, initial_capital, current_capital等

- **BrokerInstance**: Broker实例运行时配置
  - 实例ID、关联的Portfolio ID、关联的LiveAccount ID
  - 实例状态（未初始化/运行中/已停止/错误）
  - 最后心跳时间
  - 创建时间、更新时间
  - **生命周期**：系统启动时批量创建所有实盘Portfolio的实例，live_account_id变更时销毁旧实例并创建新实例

- **AccountBalance**: 账户余额信息
  - 账户ID、总资产、可用余额、冻结资金
  - 各币种余额明细
  - 更新时间

- **Position (复用)**: 持仓信息（回测和实盘共用）
  - 基础字段：code、volume、available、cost_price、current_price
  - **实盘扩展**：account_id（关联LiveAccount）

- **Order (复用)**: 订单信息（回测和实盘共用）
  - 基础字段：code、direction、volume、price、order_type、status
  - **实盘扩展**：account_id（关联LiveAccount）、exchange_order_id（交易所订单ID）

- **TradeRecord**: 交易记录（仅实盘，用于审计和分析）
  - 交易ID、账户ID、交易对、交易方向
  - 成交价格、成交数量、手续费
  - 成交时间

- **RiskControl**: 风控配置（Portfolio级别）
  - 配置ID、Portfolio ID、风控类型、阈值
  - 触发状态、触发时间、解除时间

## Success Criteria *(mandatory)*

### Measurable Outcomes

**实盘交易性能指标**:
- **SC-001**: 订单提交延迟 < 500ms（从信号生成到订单提交到交易所）
- **SC-002**: 账户信息同步延迟 < 2s（余额、持仓信息更新）
- **SC-003**: API调用成功率 > 99%（排除交易所维护时间）
- **SC-004**: 系统支持 >= 10个并发实盘账号同时运行

**系统可靠性指标**:
- **SC-005**: 代码测试覆盖率 > 85%（单元测试+集成测试）
- **SC-006**: CI/CD流水线通过率 > 95%
- **SC-007**: 零API凭证泄露事件（所有凭证加密存储）
- **SC-008**: 风控响应时间 < 100ms（检测到违规到停止交易）

**业务与用户体验指标**:
- **SC-009**: 用户配置实盘账号时间 < 5分钟（从开始到测试连接成功）
- **SC-010**: Web页面响应时间 < 1s（账号信息、交易历史查询）
- **SC-011**: 错误提示准确率 > 95%（用户能根据提示快速定位问题）
- **SC-012**: 用户配置错误率 < 5%（良好的表单验证和引导）

**功能完整性指标**:
- **SC-013**: 支持OKX现货交易100%功能覆盖（下单、撤单、查询）
- **SC-014**: 支持OKX合约交易基础功能（下单、撤单、持仓查询、资金费率）
- **SC-015**: 实盘数据与回测数据格式兼容100%（策略无需修改即可切换）

## Assumptions

1. **OKX API版本**: 使用OKX V5 API（当前稳定版本）
2. **python-okx SDK**: 使用 okxapi/python-okx 作为官方推荐SDK
3. **API权限**: 用户提供的API密钥具有交易权限（读写权限）
4. **网络环境**: 系统部署在可以访问OKX API的网络环境（如已处理代理/防火墙）
5. **交易对**: 主要支持BTC/USDT、ETH/USDT等主流交易对
6. **订单类型**: 首期支持市价单和限价单，暂不支持条件单、冰山单等复杂订单
7. **账户类型**: 首期支持普通账户，暂不支持统一账户（Unified Account）
8. **IP白名单**: 用户已在OKX后台配置API IP白名单
9. **时间同步**: 系统时间与交易所时间误差在合理范围内（<1s）
10. **币种精度**: 遵循OKX API返回的交易对精度规则
11. **手续费**: 使用OKX默认费率，暂不支持VIP费率配置
12. **Broker配置**: Broker配置存储在MySQL数据库，通过ServiceHub访问
13. **Broker实例**: 每个绑定LiveAccount的Portfolio创建一个独立的Broker实例
14. **绑定关系**: Portfolio与LiveAccount强制一对一绑定（MPortfolio.live_account_id外键）
15. **账户唯一性**: 一个LiveAccount（API凭证）只能被一个Portfolio绑定，不可复用
16. **并发限制**: 每个Broker实例独立管理API调用，遵守交易所限流规则
17. **数据同步策略**: 混合模式（WebSocket实时推送 + 30秒定时全量校验）

## Clarifications

### Session 2026-03-13

- Q: 使用哪个OKX Python库？ → A: python-okx (由 okxapi 维护)
- Q: Broker配置来源？ → A: 不能从config读取，需要从数据库/配置服务读取
- Q: Broker与Portfolio绑定关系？ → A: **强制一对一** - 一个Portfolio只能绑定一个LiveAccount，一个LiveAccount只能被一个Portfolio使用
- Q: Portfolio-LiveAccount绑定方式？ → A: MPortfolio 添加 `live_account_id` 外键字段（简化方案）
- Q: 风控配置粒度？ → A: Portfolio级别（一对一绑定后自然成为Portfolio级风控）
- Q: Broker实例生命周期？ → A: 系统启动时批量加载所有实盘Portfolio的Broker实例，Portfolio的live_account_id更新时动态管理（销毁旧实例、创建新实例）
- Q: 实盘数据同步策略？ → A: 混合模式（WebSocket推送 + 定时全量校验）
- Q: Broker崩溃恢复策略？ → A: 自动重启 + 数据完整性校验（恢复后先同步数据再继续）
- Q: 实盘与回测数据模型？ → A: 使用相同的数据模型（Bar/Position/Order），仅增加实盘特有字段（如exchange_order_id）
- Q: 实盘交易控制粒度？ → A: 完整控制（启动/停止/暂停/恢复/紧急停止 + 单Portfolio独立控制）

## Dependencies

1. **python-okx** - OKX V5 API Python SDK ([okxapi/python-okx](https://github.com/okxapi/python-okx))
2. 现有的LiveCore实盘模块
3. Web UI前端框架（Vue 3 + Ant Design Vue）
4. 加密服务（用于API凭证加密存储）
5. 告警通知服务（邮件、企业微信、钉钉等）

### 依赖说明

**python-okx** 提供以下能力：
- 全部REST API端点实现
- 私有/公开WebSocket支持（带重连和多路复用）
- 测试网支持（flag参数）
- 自动处理API签名、限流、重试
