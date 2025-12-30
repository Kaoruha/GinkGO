# Feature Specification: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-30
**Status**: Draft
**Input**: 创建完整的 MongoDB 基础设施层，使其与 ClickHouse 和 MySQL 并列为 Ginkgo 的第一等公民数据库。同时实现基于 MongoDB 的通知系统，支持 Discord 和 Email 渠道。用户管理使用 MySQL。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - MongoDB 基础设施 (Priority: P1)

作为量化交易系统开发者，我需要 MongoDB 作为第一等公民数据库支持，以便存储灵活的文档数据（如通知记录）。

**Why this priority**: MongoDB 基础设施是整个通知系统的基石，必须优先实现。

**Independent Test**: 可以通过创建 MMongoBase 模型、GinkgoMongo 驱动和 BaseMongoCRUD 来独立测试，验证基本的 CRUD 操作和连接功能。

**Acceptance Scenarios**:
1. **Given** MongoDB 服务已启动，**When** 创建 MMongoBase 模型并保存数据，**Then** 数据成功持久化到 MongoDB
2. **Given** MongoDB 连接配置正确，**When** 使用 GinkgoMongo 驱动查询数据，**Then** 返回正确的查询结果
3. **Given** 已创建 MongoDB 模型，**When** 使用 BaseMongoCRUD 进行增删改查，**Then** 操作正确执行且支持装饰器（@time_logger, @retry）

---

### User Story 2 - 用户管理系统 (Priority: P1)

作为系统管理员，我需要管理通知接收者（用户、频道、组织）及其联系方式，以便发送通知到正确的人群。

**Why this priority**: 用户管理是通知系统的核心依赖，必须先有用户数据才能发送通知。

**Independent Test**: 可以通过创建 MUser/MUserContact/MUserGroup 模型和对应的 CRUD 来独立测试，验证用户、联系方式和用户组的管理功能。

**Acceptance Scenarios**:
1. **Given** 用户管理系统已初始化，**When** 创建一个 person 类型的用户并添加 Email 联系方式，**Then** 用户和联系方式成功保存且可查询
2. **Given** 用户和用户组已创建，**When** 通过 MUserGroupMapping 将用户添加到用户组，**Then** 映射关系正确建立且外键约束生效
3. **Given** 用户被软删除（is_del=True），**When** 查询其联系方式和组映射，**Then** 关联数据也被标记为删除
4. **Given** Discord 频道作为 channel 类型用户存在，**When** 添加其 Webhook URL 作为联系方式，**Then** 频道可以作为通知接收者使用

---

### User Story 3 - Discord 通知发送 (Priority: P2)

作为交易员，我希望收到重要交易信号和系统告警的 Discord 通知，以便及时了解交易状态。

**Why this priority**: Discord 是主要通知渠道之一，用户有明确的接收需求。

**Independent Test**: 可以通过创建 DiscordChannel 并发送测试通知来独立测试，验证 Webhook 调用功能。

**Acceptance Scenarios**:
1. **Given** Discord 频道用户已创建且 Webhook URL 已配置，**When** 发送通知到该频道，**Then** Discord 成功接收消息
2. **Given** 通知发送失败（Webhook 不可用），**When** Kafka Worker 重试机制处理，**Then** 通知在重试后成功发送或失败记录被保存到 MongoDB
3. **Given** 用户禁用了 Discord 联系方式，**When** 发送通知，**Then** 不会发送到该用户的 Discord 频道

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
1. **Given** Kafka 集群运行正常，**When** 发送通知到 `notifications-discord` topic，**Then** Worker 消费消息并调用 DiscordChannel 发送
2. **Given** 发送失败（如 Webhook 返回 500），**When** Worker 重试逻辑执行，**Then** 消息重新入队并在后续重试
3. **Given** 通知发送成功/失败，**When** Worker 处理完成，**Then** 结果记录到 MNotificationRecord（MongoDB）

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
- **Discord Webhook 失效**: Webhook URL 返回 404，应标记发送失败并重试
- **Email SMTP 超时**: SMTP 服务器无响应，应超时并重试
- **用户无联系方式**: 用户没有任何启用的联系方式，通知应记录为 "无有效渠道"
- **并发发送**: 同一用户同时收到多个通知，应保证 Kafka 消费顺序
- **级联软删除**: 用户删除时，其联系方式和组映射应同步标记删除

## Requirements *(mandatory)*

### Functional Requirements

**MongoDB 基础设施**:
- **FR-001**: System MUST 提供 MMongoBase 作为 MongoDB 文档模型基类（与 MClickBase/MMysqlBase 设计一致）
- **FR-002**: System MUST 提供 GinkgoMongo 驱动基于 pymongo 实现连接池和 CRUD 操作
- **FR-003**: System MUST 提供 BaseMongoCRUD 抽象类支持泛型类型和标准 CRUD 方法
- **FR-004**: System MUST 支持通过 `~/.ginkgo/secure.yml` 配置 MongoDB 连接凭证

**用户管理系统**:
- **FR-005**: System MUST 支持 MUser 模型存储通知接收者（person/channel/organization 类型）
- **FR-006**: System MUST 支持 MUserContact 模型存储联系方式（Email/Discord 枚举存储）
- **FR-007**: System MUST 支持 MUserGroup 模型管理用户组
- **FR-008**: System MUST 支持 MUserGroupMapping 多对多映射（带外键约束）
- **FR-009**: System MUST 支持级联软删除：用户删除时同步标记联系方式和组映射为 is_del=True
- **FR-010**: System MUST 支持 is_primary 字段标记默认联系方式

**通知发送**:
- **FR-011**: System MUST 支持通过 Discord Webhook 发送通知
- **FR-012**: System MUST 支持通过 Email SMTP 发送通知
- **FR-013**: System MUST 支持 Discord Webhook URL 存储在 MUserContact.contact_value（频道作为 channel 类型用户）
- **FR-014**: System MUST 支持 Email SMTP 凭证存储在 `~/.ginkgo/secure.yml`（全局配置）

**异步处理**:
- **FR-015**: System MUST 使用 Kafka 异步队列处理通知发送
- **FR-016**: System MUST 按渠道分 topic：`notifications-discord`, `notifications-email`
- **FR-017**: System MUST 在 Worker 中根据 user_id 区分接收者并调用对应渠道
- **FR-018**: System MUST 支持 Kafka 自动重试机制处理发送失败
- **FR-019**: System MUST 将发送成功/失败结果记录到 MongoDB

**通知记录**:
- **FR-020**: System MUST 使用 MNotificationRecord 存储通知记录（MongoDB）
- **FR-021**: System MUST 支持 7 天 TTL 索引自动清理过期通知记录
- **FR-022**: System MUST 保留 priority 字段（预留未来扩展，当前按 FIFO 处理）
- **FR-023**: System MUST 记录每个通知的发送状态和渠道结果

**CLI 命令**:
- **FR-024**: System MUST 提供 `ginkgo data init --mongo` 初始化 MongoDB
- **FR-025**: System MUST 提供 `ginkgo user add/list/update/delete` 管理用户
- **FR-026**: System MUST 提供 `ginkgo user contact add/list/enable` 管理联系方式
- **FR-027**: System MUST 提供 `ginkgo user group create/list/add-user/remove-user` 管理用户组
- **FR-028**: System MUST 提供 `ginkgo notification send/send-to-users/send-to-group` 发送通知

**Ginkgo 架构约束**:
- **FR-029**: System MUST 遵循事件驱动架构和依赖注入模式
- **FR-030**: System MUST 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 装饰器优化性能
- **FR-031**: System MUST 提供完整类型注解支持静态类型检查
- **FR-032**: System MUST 遵循 TDD 开发流程，先写测试再实现功能

### Key Entities

**术语说明**:
- **用户 / User**: 通知接收者的通用术语，可以是 person (个人用户)、channel (频道/群组)、organization (组织)
- **通知接收者**: User 的功能描述，强调其在通知系统中的角色
- **联系方式 / Contact**: 用户的联系渠道，包括 Email 和 Discord Webhook

**枚举类型**:
- **USER_TYPES**: 用户类型枚举 (VOID=-1, OTHER=0, PERSON=1, CHANNEL=2, ORGANIZATION=3)
- **CONTACT_TYPES**: 联系方式类型枚举 (VOID=-1, OTHER=0, EMAIL=1, DISCORD=2)
- **NOTIFICATION_STATUS_TYPES**: 通知状态枚举 (PENDING=0, SENT=1, FAILED=2, RETRYING=3)

**数据模型**:
- **MUser**: 通知接收者（person 个人用户 / channel 频道 / organization 组织）
  - 属性: user_type (枚举), name, is_active
- **MUserContact**: 联系方式
  - 属性: user_id (外键引用 users.uuid), contact_type (枚举: EMAIL/DISCORD), contact_value, is_enabled, is_primary
- **MUserGroup**: 用户组
  - 属性: group_id (唯一), group_name, description, is_active
- **MUserGroupMapping**: 用户组成员映射（多对多，带外键）
  - 属性: user_id (外键引用 users.uuid), group_id (外键引用 user_groups.uuid), user_name, group_name
- **MNotificationRecord**: 通知记录（MongoDB）
  - 属性: message_id, content, content_type, channels, status (枚举: NOTIFICATION_STATUS_TYPES), channel_results, priority (预留字段，当前按 FIFO 处理，未来支持优先级队列)
- **DiscordChannel**: Discord 渠道
  - 功能: 发送 Webhook 请求到 Discord URL
- **EmailChannel**: Email 渠道
  - 功能: 通过 SMTP 发送邮件

## Success Criteria *(mandatory)*

### Measurable Outcomes

**MongoDB 基础设施**:
- **SC-001**: MongoDB CRUD 操作响应时间 < 50ms (p95)
- **SC-002**: MongoDB 连接池支持 >= 10 个并发连接
- **SC-003**: TTL 索引自动清理过期记录（7天后）

**用户管理**:
- **SC-004**: 单次可查询 >= 1000 个用户
- **SC-005**: 用户软删除级联操作响应时间 < 100ms
- **SC-006**: 用户组映射外键约束生效率 100%

**通知发送**:
- **SC-007**: 通知发送延迟（入队到发送）< 5 秒（p95）
- **SC-008**: Kafka 重试成功率 > 95%（针对暂时性故障）
- **SC-009**: Discord Webhook 调用成功率 > 98%（排除 Webhook 配置错误）

**异步处理**:
- **SC-010**: Kafka 消费吞吐量 >= 100 msg/s (单 worker)
- **SC-011**: Worker 故障恢复时间 < 30 秒（自动重启）

**数据保留**:
- **SC-012**: 通知记录 7 天后自动清理（TTL 索引）
- **SC-013**: 通知记录查询响应时间 < 200ms（p95）

**代码质量**:
- **SC-014**: MongoDB 相关代码测试覆盖率 > 80%
- **SC-015**: 所有模型文件包含三行头部注释（Upstream/Downstream/Role）
