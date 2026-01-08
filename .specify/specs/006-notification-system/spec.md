# Feature Specification: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-30
**Status**: Draft
**Input**: 创建完整的 MongoDB 基础设施层，使其与 ClickHouse 和 MySQL 并列为 Ginkgo 的第一等公民数据库。同时实现基于 MongoDB 的通知系统，支持 Discord 和 Email 渠道。用户管理使用 MySQL。

## 术语表 (Glossary)

| 中文术语 | 英文术语 | 说明 |
|---------|---------|------|
| 用户 | User | 通知接收者的通用术语，可以是 person (个人用户)、channel (频道/群组)、organization (组织) |
| 通知接收者 | Notification Receiver | User 的功能描述，强调其在通知系统中的角色(与 User 等价) |
| 联系方式 | Contact | 用户的联系渠道，包括 Email 和 Webhook(支持 Discord、钉钉、企业微信等) |
| 用户组 | User Group | 用于批量通知的用户集合，支持多对多映射 |
| Webhook 渠道 | Webhook Channel | 通用 Webhook 通知渠道，支持多种 Webhook 协议(Discord、钉钉、企业微信等) |
| Footer 简化 | Footer Simplification | 业务方法支持 footer 参数为字符串(如 "LiveBot")，内部自动转换为 Discord 格式 |
| 关键通知 | Critical Notification | 必须保证送达的通知类型(系统告警、交易信号、系统状态) |
| 非关键通知 | Non-Critical Notification | 可延迟或丢失的通知类型(营销类、信息类) |

## Clarifications

### Session 2025-12-31

- Q: MNotificationTemplate 的 `variables` 字段应使用什么结构来定义模板变量？ → A: JSON 对象(键值对映射)- 支持默认值和类型提示
- Q: 当 Kafka 服务完全不可用时，通知发送应采用什么降级策略？ → A: 同步发送(直接调用 DiscordChannel/EmailChannel)- 保证送达但可能阻塞
- Q: MongoDB 操作和通知发送的关键事件应使用什么日志级别？ → A: 分级日志(ERROR/WARNING/INFO/DEBUG)
- Q: Discord Webhook 和 Email SMTP 的请求超时应设置为多少？ → A: 渠道差异化超时(Discord 3s, Email 10s)，在 config.yaml 中定义
- Q: CLI 发送通知时，如何传递模板变量的值？ → A: `--var key=value` 重复使用参数(如 `--var symbol=AAPL --var price=100`)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - MongoDB 基础设施 (Priority: P1)

作为量化交易系统开发者，我需要 MongoDB 作为第一等公民数据库支持，以便存储灵活的文档数据(如通知记录)。

**Why this priority**: MongoDB 基础设施是整个通知系统的基石，必须优先实现。

**Independent Test**: 可以通过创建 MMongoBase 模型、GinkgoMongo 驱动和 BaseMongoCRUD 来独立测试，验证基本的 CRUD 操作和连接功能。

**Acceptance Scenarios**:
1. **Given** MongoDB 服务已启动，**When** 创建 MMongoBase 模型并保存数据，**Then** 数据成功持久化到 MongoDB
2. **Given** MongoDB 连接配置正确，**When** 使用 GinkgoMongo 驱动查询数据，**Then** 返回正确的查询结果
3. **Given** 已创建 MongoDB 模型，**When** 使用 BaseMongoCRUD 进行增删改查，**Then** 操作正确执行且支持装饰器(@time_logger, @retry)

---

### User Story 2 - 用户管理系统 (Priority: P1)

作为系统管理员，我需要管理通知接收者(用户、频道、组织)及其联系方式，以便发送通知到正确的人群。

**Why this priority**: 用户管理是通知系统的核心依赖，必须先有用户数据才能发送通知。

**Independent Test**: 可以通过创建 MUser/MUserContact/MUserGroup 模型和对应的 CRUD 来独立测试，验证用户、联系方式和用户组的管理功能。

**Acceptance Scenarios**:
1. **Given** 用户管理系统已初始化，**When** 创建一个 person 类型的用户并添加 Email 联系方式，**Then** 用户和联系方式成功保存且可查询
2. **Given** 用户和用户组已创建，**When** 通过 MUserGroupMapping 将用户添加到用户组，**Then** 映射关系正确建立且外键约束生效
3. **Given** 用户被软删除(is_del=True)，**When** 查询其联系方式和组映射，**Then** 关联数据也被标记为删除
4. **Given** Discord 频道作为 channel 类型用户存在，**When** 添加其 Webhook URL 作为联系方式，**Then** 频道可以作为通知接收者使用

---

### User Story 3 - Webhook 通知发送 (Priority: P2)

作为交易员，我希望收到重要交易信号和系统告警的 Webhook 通知(Discord、钉钉、企业微信等)，以便及时了解交易状态。

**Why this priority**: Webhook 是主要通知渠道之一，用户有明确的接收需求。

**Independent Test**: 可以通过创建 WebhookChannel 并发送测试通知来独立测试，验证 Webhook 调用功能。

**Acceptance Scenarios**:
1. **Given** Discord/钉钉/企业微信 频道用户已创建且 Webhook URL 已配置，**When** 发送通知到该频道，**Then** 平台成功接收消息
2. **Given** 通知发送失败(Webhook 不可用)，**When** Kafka Worker 重试机制处理，**Then** 通知在重试后成功发送或失败记录被保存到 MongoDB
3. **Given** 用户禁用了 Webhook 联系方式，**When** 发送通知，**Then** 不会发送到该用户的 Webhook 频道
4. **Given** 业务封装方法(如 send_trading_signal_webhook)，**When** 使用 footer='LiveBot' 字符串参数，**Then** 内部自动转换为 Discord 格式 {"text": "LiveBot"}

---

### User Story 4 - Email 通知发送 (Priority: P2)

作为交易员，我希望收到交易报告和分析结果的 Email 通知，以便后续查看和分析。

**Why this priority**: Email 是备用通知渠道，适合详细报告和离线查看。

**Independent Test**: 可以通过创建 EmailChannel 并发送测试邮件来独立测试，验证 SMTP 功能。

**Acceptance Scenarios**:
1. **Given** 用户 Email 地址已配置且 SMTP 已设置，**When** 发送邮件通知，**Then** Email 成功送达
2. **Given** SMTP 服务器连接失败，**When** Kafka Worker 重试机制处理，**Then** 通知在重试后成功发送或失败记录被保存

---

### User Story 5 - Kafka 异步通知处理 (Priority: P2)

作为系统架构师，我希望通知发送通过 Kafka 异步队列处理，以提高系统可靠性和解耦发送逻辑。

**Why this priority**: Kafka 异步机制是高可用通知的核心，确保发送失败能够重试。

**Independent Test**: 可以通过创建 Kafka Producer 发送通知消息并启动 Worker 消费来独立测试，验证异步处理流程。

**Acceptance Scenarios**:
1. **Given** Kafka 集群运行正常，**When** 发送通知到 `ginkgo.alerts` topic，**Then** Worker 根据 contact_type 路由到 WebhookChannel 或 EmailChannel
2. **Given** 发送失败(如 Webhook 返回 500)，**When** Worker 重试逻辑执行，**Then** 消息重新入队并在后续重试
3. **Given** 通知发送成功/失败，**When** Worker 处理完成，**Then** 结果记录到 MNotificationRecord(MongoDB)

---

### User Story 6 - 用户组批量通知 (Priority: P3)

作为管理员，我希望向用户组发送通知，以便一次性通知多个相关人员。

**Why this priority**: 用户组批量通知是便捷功能，建立在单用户通知基础上。

**Independent Test**: 可以通过创建用户组、添加成员、发送组通知来独立测试，验证批量发送功能。

**Acceptance Scenarios**:
1. **Given** 用户组已创建且包含多个成员，**When** 发送通知到该组，**Then** 所有成员接收通知
2. **Given** 用户组中部分用户联系方式被禁用，**When** 发送组通知，**Then** 仅启用联系方式的用户接收通知

---

### User Story 7 - 通知记录查询 (Priority: P3)

作为用户，我希望查看历史通知记录，以便审计和排查问题。

**Why this priority**: 历史查询是辅助功能，提升系统可维护性。

**Independent Test**: 可以通过发送通知后查询 MNotificationRecord 来独立测试，验证记录保存和 TTL 清理功能。

**Acceptance Scenarios**:
1. **Given** 通知已发送，**When** 查询 MongoDB 通知记录，**Then** 记录包含完整的发送状态和结果
2. **Given** 通知记录已存在超过 7 天，**When** TTL 索引自动清理，**Then** 过期记录被自动删除

---

### Edge Cases

- **MongoDB 连接失败**: 系统启动时 MongoDB 不可用，GinkgoMongo 应优雅降级并记录错误
- **Webhook 失效**: Webhook URL 返回 404，应标记发送失败并重试
- **Webhook 请求超时**: Webhook 请求超过配置超时时间(Discord 默认 3s)，应标记超时并重试
- **Email SMTP 超时**: SMTP 服务器无响应或超过配置超时时间(默认 10s)，应超时并重试
- **用户无联系方式**: 用户没有任何启用的联系方式，通知应记录为 "无有效渠道"
- **并发发送**: 同一用户同时收到多个通知，应保证 Kafka 消费顺序
- **级联软删除**: 用户删除时，其联系方式和组映射应同步标记删除
- **模板渲染失败**: 模板语法错误或必需变量缺失，应回退到原始模板内容并记录警告
- **Kafka 不可用**: Kafka 服务完全不可用时，NotificationService 应自动降级为同步发送模式(直接调用 WebhookChannel/EmailChannel)，保证关键通知送达，同时记录降级事件到日志
- **Footer 参数类型错误**: 业务封装方法收到非预期的 footer 类型(如 list)，应记录警告并忽略该参数

**Kafka 健康检查标准**(FR-019a):
- 连接超时：尝试连接 Kafka 超过 10 秒无响应
- Topic 不存在：`ginkgo.alerts` topic 不存在且无法创建
- Producer 初始化失败：Kafka Producer 初始化连续失败 3 次
- Broker 不可达：所有 Kafka Broker 均无法连接(主机名解析失败、端口拒绝连接等)

## Requirements *(mandatory)*

### Functional Requirements

**MongoDB 基础设施**:
- **FR-001**: System MUST 提供 MMongoBase 作为 MongoDB 文档模型基类(与 MClickBase/MMysqlBase 设计一致)
- **FR-002**: System MUST 提供 GinkgoMongo 驱动基于 pymongo 实现连接池和 CRUD 操作
- **FR-003**: System MUST 提供 BaseMongoCRUD 抽象类支持泛型类型和标准 CRUD 方法
- **FR-004**: System MUST 支持通过 `~/.ginkgo/secure.yml` 配置 MongoDB 连接凭证

**用户管理系统**:
- **FR-005**: System MUST 支持 MUser 模型存储通知接收者(person/channel/organization 类型)
- **FR-006**: System MUST 支持 MUserContact 模型存储联系方式(Email/Webhook/Discord 枚举存储)
  - Webhook 类型支持钉钉、企业微信等通用 Webhook 协议
  - Discord 类型为专用 Webhook 封装，支持 Discord 特有特性(embeds、fields、author、icon_url 等)
- **FR-007**: System MUST 支持 MUserGroup 模型管理用户组
- **FR-008**: System MUST 支持 MUserGroupMapping 多对多映射(带外键约束)
- **FR-009**: System MUST 支持级联软删除：用户删除时同步标记联系方式和组映射为 is_del=True
- **FR-010**: System MUST 支持 is_primary 字段标记默认联系方式

**通知发送**:
- **FR-011**: System MUST 支持通过 Webhook 发送通知(Discord、钉钉、企业微信等)
- **FR-011a**: System MUST 提供 send_webhook_direct() 底层方法，支持直接传递完整 Dict 格式参数
- **FR-011b**: System MUST 提供 send_discord_webhook() Discord 基础方法，支持完整 Discord 特性(embeds、fields、author、icon_url 等)
- **FR-011c**: System MUST 提供 send_trading_signal_webhook() 业务封装方法，支持简化参数(direction、code、price、volume、strategy、reason、footer='LiveBot')
- **FR-011d**: System MUST 提供 send_system_notification_webhook() 业务封装方法，支持简化参数(message_type、content、details、footer='DataBot')
- **FR-012**: System MUST 支持通过 Email SMTP 发送通知
- **FR-013**: ~~System MUST 支持 Webhook URL 存储在 MUserContact.contact_value(频道作为 channel 类型用户，支持 Discord、钉钉、企业微信等)~~ **[已合并到 FR-006]**
- **FR-014**: System MUST 支持 Email SMTP 凭证存储在 `~/.ginkgo/secure.yml`(全局配置)
- **FR-014a**: System MUST 支持渠道差异化超时配置(在 ~/.ginkgo/config.yaml 中定义，Discord 默认 3s，Email 默认 10s)

**FR-014a 配置结构** (config.yaml):
```yaml
notifications:
  timeouts:
    discord: 3  # Discord Webhook 超时时间(秒)
    email: 10    # Email SMTP 超时时间(秒)
```

**异步处理**:
- **FR-015**: System MUST 使用 Kafka 异步队列处理通知发送
- **FR-016**: System MUST 使用单一 Kafka topic `ginkgo.alerts`，Worker 根据 contact_type 字段(EMAIL/WEBHOOK/DISCORD)路由到对应渠道
- **FR-017**: System MUST 在 Worker 中根据 user_id 区分接收者并调用对应渠道
- **FR-018**: System MUST 支持 Kafka 自动重试机制处理发送失败
- **FR-019**: System MUST 将发送成功/失败结果记录到 MongoDB
- **FR-019a**: System MUST 在 Kafka 不可用时自动降级为同步发送模式(直接调用渠道)，保证关键通知送达

**关键通知定义**(FR-019a 适用于以下通知类型):
- 系统告警类通知(错误、异常、风控触发)
- 交易信号类通知(买入、卖出信号)
- 系统状态类通知(服务启动、停止、故障恢复)
- 非关键通知：营销类、信息类通知(可延迟或丢失)

**通知记录**:
- **FR-020**: System MUST 使用 MNotificationRecord 存储通知记录(MongoDB)
- **FR-021**: System MUST 支持 7 天 TTL 索引自动清理过期通知记录
- **FR-022**: System MUST 保留 priority 字段(预留未来扩展，当前按 FIFO 处理)

**FR-022 实现说明**:
- 当前版本仅保留 priority 字段，不实现优先级队列逻辑
- 所有通知按 FIFO(先进先出)顺序处理
- 未来版本可基于 priority 字段实现优先级队列功能
- **FR-023**: System MUST 记录每个通知的发送状态和渠道结果

**通知模板**:
- **FR-024**: System MUST 使用 MNotificationTemplate 存储通知模板(MongoDB)
- **FR-025**: System MUST 支持模板变量替换(使用 Jinja2 语法)
- **FR-026**: System MUST 支持多种模板类型(TEXT, MARKDOWN, EMBEDDED)
- **FR-027**: System MUST 提供模板管理 CLI 命令(create, list, update, delete)
- **FR-028**: System MUST 支持通过模板 ID 或模板名称发送通知

**CLI 命令**:
- **FR-029**: System MUST 提供 `ginkgo data init` 初始化所有数据库(包括 MongoDB)
- **FR-030**: System MUST 提供 `ginkgo mongo status` 显示 MongoDB 连接状态
- **FR-031**: System MUST 提供 `ginkgo users create/list/update/delete` 管理用户
- **FR-032**: System MUST 提供 `ginkgo users contacts add/list/enable` 管理联系方式
- **FR-033**: System MUST 提供 `ginkgo groups create/list/add-user/remove-user` 管理用户组
- **FR-034**: System MUST 提供 `ginkgo templates create/list/update/delete` 管理通知模板
- **FR-035**: System MUST 提供 `ginkgo notify send --user/--group/--message/--template` 发送通知(支持组合使用，支持 `--var key=value` 重复参数传递模板变量)

**FR-035 CLI 参数说明**:
- `--user <uuids>`: 支持逗号分隔多个用户 UUID(如 `--user uuid1,uuid2,uuid3`)
- `--group <group_ids>`: 支持逗号分隔多个用户组 ID(如 `--group traders,admins`)
- `--message <text>`: 直接发送文本消息
- `--template <template_id>`: 使用模板发送通知
- `--var <key=value>`: 模板变量，可重复使用(如 `--var symbol=AAPL --var price=100`)

**--var 参数传递机制**:
- `--var` 参数值会覆盖模板中 `variables` 定义的默认值
- 如果模板中某变量未定义默认值且未通过 `--var` 传递，模板渲染会失败并记录警告
- 变量传递遵循类型检查：字符串、数字、布尔值自动转换
- 示例：模板定义 `{"price": {"type": "float", "default": 0.0}}`，执行 `--var price=150` 会覆盖默认值为 150.0

- `--user`、`--group`、`--message`、`--template` 可组合使用(如 `--user uuid1 --group traders --template signal`)
- **FR-036**: System MUST 提供 `ginkgo worker start --notification` 启动通知 Worker

**Ginkgo 架构约束**:
- **FR-037**: System MUST 遵循事件驱动架构和依赖注入模式
- **FR-038**: System MUST 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 装饰器优化性能
- **FR-039**: System MUST 提供完整类型注解支持静态类型检查
- **FR-040**: System MUST 遵循 TDD 开发流程，先写测试再实现功能

### Key Entities

**术语说明**:
- **用户 / User**: 通知接收者的通用术语，可以是 person (个人用户)、channel (频道/群组)、organization (组织)
- **通知接收者**: User 的功能描述，强调其在通知系统中的角色
- **联系方式 / Contact**: 用户的联系渠道，包括 Email 和 Discord Webhook

**枚举类型**:
- **USER_TYPES**: 用户类型枚举 (VOID=-1, OTHER=0, PERSON=1, CHANNEL=2, ORGANIZATION=3)
- **CONTACT_TYPES**: 联系方式类型枚举 (VOID=-1, OTHER=0, EMAIL=1, WEBHOOK=2, DISCORD=3)
  - EMAIL: 邮件联系方式
  - WEBHOOK: Webhook 通用类型(支持钉钉、企业微信等 Webhook 协议)
  - DISCORD: Discord 专用 Webhook 封装(支持 embeds、fields、author、icon_url 等 Discord 特性)
- **NOTIFICATION_STATUS_TYPES**: 通知状态枚举 (PENDING=0, SENT=1, FAILED=2, RETRYING=3)
- **TEMPLATE_TYPES**: 模板类型枚举 (VOID=-1, OTHER=0, TEXT=1, MARKDOWN=2, EMBEDDED=3)

**数据模型**:
- **MUser**: 通知接收者(person 个人用户 / channel 频道 / organization 组织)
  - MySQL 表名: `users`
  - 属性: user_type (枚举), name, is_active
- **MUserContact**: 联系方式
  - MySQL 表名: `user_contacts`
  - 属性: user_id (外键引用 users.uuid), contact_type (枚举: EMAIL/WEBHOOK), contact_value (Webhook URL 或 Email 地址), is_enabled, is_primary
- **MUserGroup**: 用户组
  - MySQL 表名: `user_groups`
  - 属性: group_id (唯一), group_name, description, is_active
- **MUserGroupMapping**: 用户组成员映射(多对多，带外键)
  - MySQL 表名: `user_group_mappings`
  - 属性: user_id (外键引用 users.uuid), group_id (外键引用 user_groups.uuid), user_name, group_name
- **MNotificationTemplate**: 通知模板(MongoDB)
  - 属性: template_id (唯一), template_name, template_type (枚举: TEXT/MARKDOWN/EMBEDDED), subject, content, variables (JSON对象，键值对映射，支持默认值和类型提示), is_active
  - 功能: 存储预定义的通知模板(如交易信号、回测完成、错误告警)
  - variables 示例: `{"symbol": {"type": "string", "default": "", "description": "交易代码"}, "price": {"type": "float", "default": 0.0, "description": "价格"}}`
- **MNotificationRecord**: 通知记录(MongoDB)
  - 属性: message_id, content, content_type, channels, status (枚举: NOTIFICATION_STATUS_TYPES), channel_results, priority (预留字段，当前按 FIFO 处理，未来支持优先级队列)
- **WebhookChannel**: Webhook 通用渠道
  - 功能: 发送 Webhook 请求到支持 Webhook 协议的平台(Discord、钉钉、企业微信等)
  - 设计: 通用 Webhook 实现，Discord 作为主要适配协议
  - Footer 支持: Union[str, Dict] - 自动处理字符串转换为 Discord 格式
- **EmailChannel**: Email 渠道
  - 功能: 通过 SMTP 发送邮件
- **TemplateEngine**: 模板引擎
  - 功能: 使用 Jinja2 渲染通知模板，支持变量替换和默认值回退

**Webhook 渠道三层方法架构**:

NotificationService 提供三层方法结构，满足不同使用场景：

┌─────────────────────────────────────────────────────────┐
│ **层级1: 业务封装层** (面向常见业务场景)                  │
│ • `send_trading_signal_webhook(footer='LiveBot')`      │
│ • `send_system_notification_webhook(footer='DataBot')  │
│ └─ Footer: str 参数，内部自动转换为 {"text": str}       │
│ └─ 适用: 交易信号、系统通知等标准化业务场景              │
├─────────────────────────────────────────────────────────┤
│ **层级2: Discord 基础层** (Discord 专用完整功能)         │
│ • `send_discord_webhook(footer={...})`                 │
│ └─ Footer: Dict 格式，支持完整 Discord 功能             │
│ └─ 支持: embeds, fields, author, icon_url 等           │
│ └─ 适用: 需要 Discord 特性的场景                        │
├─────────────────────────────────────────────────────────┤
│ **层级3: 底层通道层** (保持通用性)                       │
│ • `send_webhook_direct(footer=...)`                    │
│ └─ Footer: Union[str, Dict]，WebhookChannel 自动处理   │
│ └─ 适用: 直接调用 WebhookChannel，最大灵活性            │
└─────────────────────────────────────────────────────────┘

**Footer 参数简化说明**:
- 业务封装方法支持 `footer="LiveBot"` 字符串格式
- 内部自动转换为 Discord 格式: `{"text": "LiveBot"}`
- 底层方法仍支持完整 Dict 格式: `{"text": "...", "icon_url": "..."}`
- CLI 优化: 用户可使用简洁参数，无需构造复杂 Dict 结构

## Success Criteria *(mandatory)*

### Measurable Outcomes

**MongoDB 基础设施**:
- **SC-001**: MongoDB CRUD 操作响应时间 < 50ms (p95)
- **SC-002**: MongoDB 连接池支持 >= 10 个并发连接
- **SC-003**: TTL 索引自动清理过期记录(7天后，计算方式：create_at + 7*24*3600 秒)

**用户管理**:
- **SC-004**: 单次可查询 >= 1000 个用户
- **SC-005**: 用户软删除级联操作响应时间 < 100ms
- **SC-006**: 用户组映射外键约束生效率 100%

**通知发送**:
- **SC-007**: 通知发送延迟(入队到发送)< 5 秒(p95)
- **SC-008**: Kafka 重试成功率 > 95%(针对暂时性故障)
- **SC-009**: Webhook 调用成功率 > 98%(排除 Webhook 配置错误)

**异步处理**:
- **SC-010**: Kafka 消费吞吐量 >= 100 msg/s (单 worker)
- **SC-011**: Worker 故障恢复时间 < 30 秒(自动重启)

**数据保留**:
- ~~**SC-012**: 通知记录 7 天后自动清理(TTL 索引，计算方式：create_at + 7*24*3600 秒)~~ **[已合并到 SC-003]**
- **SC-013**: 通知记录查询响应时间 < 200ms(p95)

**代码质量**:
- **SC-014**: MongoDB 相关代码测试覆盖率 > 80%
- **SC-015**: 所有模型文件包含三行头部注释(Upstream/Downstream/Role)
- **SC-016**: 日志级别策略：ERROR(发送失败、连接断开)、WARNING(降级模式、重试)、INFO(关键操作、状态变更)、DEBUG(详细追踪)

---

## Dependencies & Technical Constraints

### Python 依赖

- **Jinja2**: 模板引擎，用于通知模板变量替换
- **pymongo**: MongoDB Python 驱动
- **kafka-python**: Kafka Python 客户端
- **pydantic**: 数据验证和模型定义

### 技术约束

- **MongoDB 4.4+**: 支持 TTL 索引和聚合管道
- **Kafka 2.8+**: 支持事务和自动重试
- **Python 3.11+**: 类型注解和异步支持
