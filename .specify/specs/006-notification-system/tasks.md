# Tasks: MongoDB 基础设施与通知系统

**Input**: Design documents from `/specs/006-notification-system/`
**Prerequisites**: plan.md, spec.md

**Tests**: 本项目遵循 TDD 原则，所有功能都应有对应的单元测试

**Organization**: 任务按用户故事组织，每个故事分多个小阶段，每个阶段约 5 个任务，设定明确的完成标准

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Ginkgo project structure at root level

---

## Phase 1: 项目初始化与依赖配置

**Goal**: 准备开发环境和依赖

**完成标准**:
- ✅ 项目目录结构已创建
- ✅ pymongo 和 pydantic 已添加到 requirements
- ✅ MongoDB 和 MySQL 配置文件已准备

- [ ] T001 [P] Create directory structure for MongoDB infrastructure in src/ginkgo/data/models/, src/ginkgo/data/drivers/, src/ginkgo/data/crud/
- [ ] T002 [P] Create directory structure for notification system in src/ginkgo/notifier/
- [ ] T003 [P] Create directory structure for tests in test/unit/data/, test/unit/notifier/
- [ ] T004 [P] Add pymongo and pydantic dependencies to project requirements
- [ ] T005 Add MongoDB services (mongo-master, mongo-test) to .conf/docker-compose.yml (参考 mysql-master 配置，端口 27017/27018)
- [ ] T006 Add MongoDB entrypoint script to .conf/mongo_entrypoint/ (初始化数据库、用户、集合)

---

## Phase 2: MongoDB 配置与驱动

**Goal**: MongoDB 服务可连接、可访问

**完成标准**:
- ✅ `docker-compose up` 后 MongoDB 服务正常运行
- ✅ `check_mongo_ready()` 函数返回成功
- ✅ GinkgoMongo 驱动可以连接并执行 ping 命令

- [ ] T007 Update .conf/docker-compose.yml volumes for MongoDB data persistence (../.db/mongo)
- [ ] T008 Add MongoDB connection configuration to ~/.ginkgo/secure.yml (MONGOHOST, MONGOPORT, MONGOUSER, MONGOPWD, MONGODB)
- [ ] T009 Update GCONF to load MongoDB configuration from secure.yml
- [ ] T010 [P] Add check_mongo_ready() function to src/ginkgo/libs/utils/health_check.py
- [ ] T011 Update src/ginkgo/libs/utils/health_check.py get_ginkgo_services_config() to include MongoDB
- [ ] T012 [US1] Create GinkgoMongo driver in src/ginkgo/data/drivers/ginkgo_mongo.py (基于 pymongo, 连接池)
- [ ] T013 [US1] Implement GinkgoMongo._get_uri() and connect() methods (MongoClient, 连接池配置)
- [ ] T014 [US1] Implement GinkgoMongo.health_check() method (ping 命令)
- [ ] T015 [US1] Add GinkgoMongo专用logger and @time_logger/@retry decorators

---

## Phase 3: MongoBase 与 MMongoBase 基类

**Goal**: MongoDB 模型基础设施就绪

**完成标准**:
- ✅ MMongoBase 可以创建实例并序列化为字典
- ✅ 字段默认值和枚举转换工作正常
- ✅ 单元测试通过

- [ ] T016 [US1] Create MongoBase class in src/ginkgo/data/drivers/base_mongo.py (提供 __collection__ 支持)
- [ ] T017 [US1] Create MMongoBase abstract model class in src/ginkgo/data/models/model_mongobase.py (Pydantic BaseModel + MBase)
- [ ] T018 [P] [US1] Implement MMongoBase fields (uuid, meta, desc, create_at, update_at, is_del, source)
- [ ] T019 [P] [US1] Implement MMongoBase methods (get_source_enum, set_source, delete, cancel_delete, __repr__)
- [ ] T020 [US1] Add MMongoBase Pydantic features (model_dump wrapper, from_mongo classmethod)
- [ ] T021 [P] [US1] Write unit test for MMongoBase initialization in test/unit/data/test_model_mongobase.py
- [ ] T022 [P] [US1] Write unit test for MMongoBase enum handling in test/unit/data/test_model_mongobase.py

---

## Phase 4: ModelConversion 兼容性验证

**Goal**: Pydantic 模型与现有架构兼容

**完成标准**:
- ✅ Pydantic 模型可以调用 `to_dataframe()` 和 `to_entity()`
- ✅ 现有 MySQL/ClickHouse 测试全部通过（无回归）

- [ ] T023 Create test file test/unit/data/test_model_conversion_pydantic.py
- [ ] T024 [P] Verify Pydantic model.__dict__ compatibility with pd.DataFrame()
- [ ] T025 Update BaseCRUD TypeVar to support MMongoBase (Union[MClickBase, MMysqlBase, MMongoBase])
- [ ] T026 Add MMongoBase import to src/ginkgo/data/crud/base_crud.py and model_conversion.py
- [ ] T027 Run full test suite (pytest test/unit/data/crud/) to verify no regression
- [ ] T028 [P] Run Ginkgo existing tests (pytest test/unit/ -k "not network" -x)

---

## Phase 5: BaseMongoCRUD 实现

**Goal**: MongoDB CRUD 操作基础设施

**完成标准**:
- ✅ 可以创建 CRUD 实例并执行基本增删改查
- ✅ 单元测试通过 CRUD 操作

- [ ] T029 [US1] Create BaseMongoCRUD abstract class in src/ginkgo/data/crud/base_mongo_crud.py
- [ ] T030 [US1] Implement BaseMongoCRUD.__init__ with GinkgoMongo driver injection
- [ ] T031 [P] [US1] Implement BaseMongoCRUD.add() and add_many() methods (insert_one, insert_many)
- [ ] T032 [P] [US1] Implement BaseMongoCRUD.get() and get_all() methods (find_one, find)
- [ ] T033 [US1] Implement BaseMongoCRUD.update(), delete(), hard_delete() methods
- [ ] T034 [US1] Add @time_logger and @retry decorators to BaseMongoCRUD methods
- [ ] T035 Update src/ginkgo/data/models/__init__.py to export MMongoBase

---

## Phase 6: MongoDB 基础设施验证

**Goal**: MongoDB 作为第一等公民数据库可用 (US1 MVP 里程碑)

**完成标准**:
- ✅ CLI 命令 `ginkgo data init --mongo` 可以初始化集合
- ✅ CLI 命令 `ginkgo mongo status` 显示连接状态
- ✅ 性能监控已添加（计时、计数）

- [ ] T036 [US1] Create CLI command `ginkgo data init --mongo` in src/ginkgo/interfaces/cli/data.py
- [ ] T037 [US1] Create CLI command `ginkgo mongo status` in src/ginkgo/interfaces/cli/mongo.py
- [ ] T038 [US1] Add error handling for MongoDB connection failures in GinkgoMongo (优雅降级)
- [ ] T039 [US1] Add structured logging with GLOG for MongoDB operations
- [ ] T040 [US1] Add performance monitoring for MongoDB CRUD operations

**Checkpoint**: 🎯 **US1 (MongoDB 基础设施) 完成** - MongoDB 作为第一等公民数据库就绪

---

## Phase 7: 枚举定义 (US2 前置)

**Goal**: 用户管理所需的枚举类型就绪

**完成标准**:
- ✅ USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES 已定义
- ✅ 枚举可以正确处理 int/enum 转换

- [ ] T041 [US2] Add USER_TYPES enum to src/ginkgo/enums.py (VOID=-1, OTHER=0, PERSON=1, CHANNEL=2, ORGANIZATION=3)
- [ ] T042 [US2] Add CONTACT_TYPES enum to src/ginkgo/enums.py (VOID=-1, OTHER=0, EMAIL=1, DISCORD=2)
- [ ] T043 [US2] Add NOTIFICATION_STATUS_TYPES enum to src/ginkgo/enums.py (PENDING=0, SENT=1, FAILED=2, RETRYING=3)
- [ ] T044 [US2] Update src/ginkgo/enums.py __all__ to export new enums

---

## Phase 8: 用户模型 (MySQL)

**Goal**: MUser 模型可以创建并存储

**完成标准**:
- ✅ MUser 模型继承 MMysqlBase + ModelConversion
- ✅ user_type 枚举处理正确
- ✅ 单元测试通过

- [ ] T045 [US2] Create MUser model in src/ginkgo/data/models/model_user.py (继承 MMysqlBase, user_type 枚举)
- [ ] T046 [P] [US2] Implement MUser.__init__() with enum handling (user_type, is_active, source)
- [ ] T047 [P] [US2] Implement MUser.update(@singledispatchmethod) for str and pd.Series
- [ ] T048 [P] [US2] Add MUser relationship: contacts = relationship("MUserContact", back_populates="user")
- [ ] T049 [US2] Write unit test for MUser model in test/unit/data/models/test_model_user.py

---

## Phase 9: 用户联系方式模型

**Goal**: MUserContact 模型支持用户联系方式管理

**完成标准**:
- ✅ MUserContact 模型包含外键和枚举字段
- ✅ is_primary 字段支持
- ✅ 单元测试通过

- [ ] T050 [US2] Create MUserContact model in src/ginkgo/data/models/model_user_contact.py
- [ ] T051 [P] [US2] Implement MUserContact fields (user_id 外键引用 users.uuid, contact_type 枚举, is_primary)
- [ ] T052 [P] [US2] Implement MUserContact.update() with is_primary handling
- [ ] T053 [US2] Write unit test for MUserContact in test/unit/data/models/test_model_user_contact.py

---

## Phase 10: 用户组模型

**Goal**: MUserGroup 和 MUserGroupMapping 模型支持组管理

**完成标准**:
- ✅ MUserGroup 有 group_id 唯一索引
- ✅ MUserGroupMapping 有正确的外键约束
- ✅ 单元测试通过

- [ ] T054 [P] [US2] Create MUserGroup model in src/ginkgo/data/models/model_user_group.py
- [ ] T055 [P] [US2] Create MUserGroupMapping model in src/ginkgo/data/models/model_user_group_mapping.py
- [ ] T056 [US2] Write unit test for MUserGroup in test/unit/data/models/test_model_user_group.py
- [ ] T057 [US2] Write unit test for MUserGroupMapping 外键约束 in test/unit/data/models/test_model_user_group_mapping.py

---

## Phase 11: 用户 CRUD 层

**Goal**: 用户数据可以通过 CRUD 操作管理

**完成标准**:
- ✅ UserCRUD 支持级联软删除
- ✅ CRUD 方法有装饰器优化
- ✅ 单元测试通过

- [ ] T058 [US2] Create UserCRUD in src/ginkgo/data/crud/user_crud.py (继承 BaseCRUD)
- [ ] T059 [US2] Implement UserCRUD.delete() with cascade soft delete (联系方式和组映射)
- [ ] T060 [P] [US2] Create UserContactCRUD in src/ginkgo/data/crud/user_contact_crud.py (继承 BaseCRUD)
- [ ] T061 [P] [US2] Create UserGroupCRUD in src/ginkgo/data/crud/user_group_crud.py
- [ ] T062 [P] [US2] Create UserGroupMappingCRUD in src/ginkgo/data/crud/user_group_mapping_crud.py
- [ ] T063 [US2] Add @time_logger and @retry decorators to all CRUD methods

---

## Phase 12: 用户服务层

**Goal**: UserService 提供用户管理业务逻辑

**完成标准**:
- ✅ UserService 可以创建/删除用户
- ✅ 级联删除逻辑正确实现
- ✅ 单元测试通过

- [ ] T064 [US2] Create UserService in src/ginkgo/user/services/user_service.py
- [ ] T065 [US2] Implement UserService.add_user() method (支持 person/channel/organization)
- [ ] T066 [US2] Implement UserService.add_contact() method (Email/Discord)
- [ ] T067 [US2] Implement UserService.delete_user() method (级联删除联系方式和组映射)
- [ ] T068 [US2] Create UserGroupService in src/ginkgo/user/services/user_group_service.py
- [ ] T069 [US2] Implement UserGroupService.create_group() and add_user_to_group()

---

## Phase 13: 用户管理 CLI 命令

**Goal**: 用户可以通过 CLI 管理用户和组

**完成标准**:
- ✅ 所有 FR-025, FR-026, FR-027 命令已实现
- ✅ CLI 命令可以正确执行并显示结果

- [ ] T070 [US2] Create `ginkgo user add` command (--type, --name)
- [ ] T071 [US2] Create `ginkgo user list` command
- [ ] T072 [US2] Create `ginkgo user update` command (--name, --type, --is-active)
- [ ] T073 [US2] Create `ginkgo user delete` command (软删除级联)
- [ ] T074 [US2] Create `ginkgo user contact add/list/enable` commands
- [ ] T075 [US2] Create `ginkgo user group create/list/add-user/remove-user` commands

**Checkpoint**: **US2 (用户管理系统) 完成** (FR-005 到 FR-010, FR-025 到 FR-027)

---

## Phase 14: Discord 通知渠道模型

**Goal**: Discord 通知记录可以存储

**完成标准**:
- ✅ MNotificationRecord 模型支持 Discord 发送结果
- ✅ TTL 索引配置正确（7天）
- ✅ 单元测试通过

- [ ] T076 [US3] Create MNotificationRecord model in src/ginkgo/data/models/model_notification_record.py
- [ ] T077 [US3] Add TTL index to MNotificationRecord (7天自动清理, create_at + expireAfterSeconds)
- [ ] T078 [US3] Create NotificationRecordCRUD in src/ginkgo/data/crud/notification_record_crud.py
- [ ] T079 [US3] Write unit test for MNotificationRecord in test/unit/data/models/test_notification_record.py

---

## Phase 15: Discord 通知渠道实现

**Goal**: Discord Webhook 可以发送消息

**完成标准**:
- ✅ DiscordChannel.send() 可以发送 Webhook 请求
- ✅ 错误处理和重试逻辑工作正常
- ✅ 单元测试通过

- [ ] T080 [US3] Create INotificationChannel interface in src/ginkgo/notifier/channels/base_channel.py
- [ ] T081 [US3] Create DiscordChannel in src/ginkgo/notifier/channels/discord_channel.py
- [ ] T082 [US3] Implement DiscordChannel.send() method (requests.post to webhook_url)
- [ ] T083 [US3] Add error handling and retry logic for Discord Webhook failures
- [ ] T084 [US3] Write unit test for DiscordChannel in test/unit/notifier/channels/test_discord_channel.py

**Checkpoint**: **US3 (Discord 通知发送) 完成**

---

## Phase 16: Email 通知渠道

**Goal**: Email SMTP 可以发送邮件

**完成标准**:
- ✅ SMTP 配置已添加到 secure.yml
- ✅ EmailChannel.send() 可以发送邮件
- ✅ 单元测试通过

- [ ] T085 [US4] Add Email SMTP configuration to ~/.ginkgo/secure.yml (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
- [ ] T086 [US4] Create EmailChannel in src/ginkgo/notifier/channels/email_channel.py
- [ ] T087 [US4] Implement EmailChannel.send() method (smtplib.SMTP, sendmail)
- [ ] T088 [US4] Add error handling and retry logic for SMTP failures
- [ ] T089 [US4] Write unit test for EmailChannel in test/unit/notifier/channels/test_email_channel.py

**Checkpoint**: **US4 (Email 通知发送) 完成**

---

## Phase 17: Kafka 基础设施

**Goal**: Kafka topic 和生产者就绪

**完成标准**:
- ✅ Kafka topics 已创建
- ✅ MessageQueue 可以发送通知消息

- [ ] T090 [US5] Create Kafka topics: notifications-discord, notifications-email
- [ ] T091 [US5] Create MessageQueue producer in src/ginkgo/notifier/core/message_queue.py
- [ ] T092 [US5] Implement MessageQueue.send_notification() method (序列化, 发送到对应 topic)
- [ ] T093 [US5] Write unit test for Kafka producer in test/unit/notifier/core/test_message_queue.py

---

## Phase 18: NotificationService 核心

**Goal**: 通知服务可以协调 Discord/Email 渠道

**完成标准**:
- ✅ NotificationService 可以根据用户联系方式选择渠道
- ✅ 单元测试通过

- [ ] T094 [US5] Create NotificationService in src/ginkgo/notifier/core/notification_service.py
- [ ] T095 [US5] Implement NotificationService.send() method (根据用户联系方式选择渠道)
- [ ] T096 [US5] Implement NotificationService.send_to_users() method (批量发送)
- [ ] T097 [US5] Write unit test for NotificationService in test/unit/notifier/core/test_notification_service.py

---

## Phase 19: Kafka Worker 实现

**Goal**: Kafka Worker 可以消费消息并调用渠道发送

**完成标准**:
- ✅ Worker 可以启动并消费 Kafka 消息
- ✅ 重试逻辑和结果记录工作正常
- ✅ 集成测试通过

- [ ] T098 [US5] Create Kafka worker in src/ginkgo/notifier/workers/notification_worker.py
- [ ] T099 [US5] Implement worker Discord message handler (调用 DiscordChannel.send())
- [ ] T100 [US5] Implement worker Email message handler (调用 EmailChannel.send())
- [ ] T101 [US5] Implement worker retry logic (Kafka 自动重试 + 失败记录)
- [ ] T102 [US5] Implement worker result recording (保存到 MNotificationRecord)
- [ ] T103 [US5] Write integration test for Kafka worker in test/integration/notifier/test_worker_integration.py

---

## Phase 20: 通知系统 CLI 命令

**Goal**: 用户可以通过 CLI 发送通知

**完成标准**:
- ✅ FR-028 命令已实现
- ✅ Worker 可以通过 CLI 启动

- [ ] T104 [US5] Create `ginkgo notification send` command (支持 --message, --users, --group)
- [ ] T105 [US5] Create `ginkgo notification send-to-users` command
- [ ] T106 [US5] Create `ginkgo worker start --notification` command

**Checkpoint**: **US5 (Kafka 异步通知处理) 完成**

---

## Phase 21: 用户组批量通知

**Goal**: 向用户组批量发送通知

**完成标准**:
- ✅ NotificationService.send_to_group() 可以查询组成员并批量发送
- ✅ 禁用联系方式的用户被正确过滤

- [ ] T107 [US6] Implement NotificationService.send_to_group() (查询组成员, 批量发送)
- [ ] T108 [US6] Add filtering logic for disabled contacts (仅启用联系方式的用户)
- [ ] T109 [US6] Create CLI command `ginkgo notification send-to-group`

**Checkpoint**: **US6 (用户组批量通知) 完成**

---

## Phase 22: 通知记录查询

**Goal**: 用户可以查询历史通知记录

**完成标准**:
- ✅ NotificationService.query_*() 方法工作正常
- ✅ TTL 清理功能验证通过

- [ ] T110 [US7] Implement NotificationService.send_sync() method (同步发送, 用于测试)
- [ ] T111 [US7] Implement NotificationService.query_history() method (查询 MNotificationRecord)
- [ ] T112 [US7] Implement NotificationService.query_by_user() method (按用户查询)
- [ ] T113 [US7] Verify TTL index auto-cleanup (测试 7 天自动清理)
- [ ] T114 [US7] Create CLI command `ginkgo notification history`

**Checkpoint**: **US7 (通知记录查询) 完成**

---

## Phase 23: 性能优化与测试

**Goal**: 系统性能达标，代码质量符合规范

**完成标准**:
- ✅ 性能基准测试通过 (SC-006, SC-007)
- ✅ 代码质量检查通过 (三行头部注释, 类型注解)
- ✅ 安全合规检查通过 (secure.yml.gitignore)

- [ ] T115 [P] 批量操作优化 (确保使用 insert_many 而非单条插入)
- [ ] T116 [P] 装饰器性能优化 (@time_logger, @cache_with_expiration 配置调优)
- [ ] T117 [P] 连接池优化 (MongoDB/MySQL 连接池大小调整)
- [ ] T118 [P] 数据库查询优化 (MongoDB 索引和查询调优)
- [ ] T119 [P] TDD 流程验证 (确保所有功能都有对应的测试)
- [ ] T120 [P] 代码质量检查 (类型注解、命名规范、三行头部注释)
- [ ] T120a [P] 头部注释同步验证 (验证 Upstream/Downstream/Role 与代码实际功能一致, SC-015)
- [ ] T121 [P] 安全合规检查 (敏感信息检查、secure.yml.gitignore)
- [ ] T122 [P] 性能基准测试 (CRUD 操作延迟、连接池效率, 验证 SC-006/SC-007)
- [ ] T122a [P] MongoDB CRUD 性能测试 (验证 SC-001: < 50ms p95)
- [ ] T122b [P] MongoDB 连接池测试 (验证 SC-002: >= 10 并发连接)
- [ ] T122c [P] 用户查询性能测试 (验证 SC-004: >= 1000 用户)
- [ ] T122d [P] 级联删除性能测试 (验证 SC-005: < 100ms)
- [ ] T122e [P] 通知发送延迟测试 (验证 SC-007: < 5 秒 p95)
- [ ] T122f [P] Kafka 吞吐量测试 (验证 SC-010: >= 100 msg/s)

---

## Phase 24: 文档与收尾

**Goal**: 文档完善，代码清理

**完成标准**:
- ✅ API 文档已更新
- ✅ 架构文档已更新
- ✅ 代码重构完成

- [ ] T123 [P] API 文档更新 (包含 NotificationService 使用示例)
- [ ] T124 [P] 架构文档更新 (MongoDB 集成说明)
- [ ] T125 Code cleanup and refactoring
- [ ] T126 [P] Additional integration tests in test/integration/
- [ ] T127 [P] Security hardening (Webhook URL 验证, SMTP 加密)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-3**: MongoDB 基础设施 (US1) - 无外部依赖
- **Phase 4**: ModelConversion 兼容性验证 - 依赖 Phase 1-3
- **Phase 5-6**: BaseMongoCRUD + MongoDB 验证 - 依赖 Phase 4
- **Phase 7**: 枚举定义 - 依赖 Phase 6 (US1 完成)
- **Phase 8-13**: 用户管理系统 (US2) - 依赖 Phase 7
- **Phase 14-16**: Discord 渠道 (US3, US4) - 依赖 Phase 5 (MongoDB 基础)
- **Phase 17-20**: Kafka + Worker (US5) - 依赖 Phase 14-16 (通知渠道)
- **Phase 21**: 用户组批量 (US6) - 依赖 Phase 8-13 (用户管理) + Phase 20 (通知服务)
- **Phase 22**: 历史查询 (US7) - 依赖 Phase 20 (通知记录)
- **Phase 23-24**: 优化与文档 - 依赖所有功能完成

### User Story Dependencies

- **US1 (MongoDB 基础)**: Phase 1-6
- **US2 (用户管理)**: Phase 7-13
- **US3 (Discord)**: Phase 14-15
- **US4 (Email)**: Phase 16
- **US5 (Kafka)**: Phase 17-20
- **US6 (用户组)**: Phase 21
- **US7 (历史查询)**: Phase 22

### Parallel Opportunities

- Phase 1: T001-T003, T004, T006 可并行
- Phase 3: T018-T019 (字段+方法) 可并行
- Phase 4: T024-T026, T028 可并行
- Phase 5: T031-T033 (CRUD 操作) 可并行
- Phase 8: T046-T048 (MUser 字段) 可并行
- Phase 9: T051-T052 (模型创建) 可并行
- Phase 10: T054-T055 (模型创建) 可并行
- Phase 11: T060-T062 (CRUD 创建) 可并行
- Phase 23: T115-T118, T121-T122 可并行
- Phase 24: T123-T124, T126-T127 可并行

---

## Implementation Strategy

### MVP First (Phase 1-6)

1. ✅ Phase 1: 项目初始化
2. ✅ Phase 2: MongoDB 配置与驱动
3. ✅ Phase 3: MongoBase 与 MMongoBase
4. ✅ Phase 4: ModelConversion 兼容性验证
5. ✅ Phase 5: BaseMongoCRUD 实现
6. ✅ Phase 6: MongoDB 基础设施验证
7. **STOP and VALIDATE**: MongoDB 作为第一等公民数据库完全可用
8. 部署/演示 MongoDB 基础设施

### Incremental Delivery

1. **MVP** (Phase 1-6): MongoDB 基础设施
2. **用户管理** (Phase 7-13): 用户、联系方式、用户组
3. **Discord** (Phase 14-15): Discord 渠道
4. **Email** (Phase 16): Email 渠道
5. **Kafka** (Phase 17-20): 异步处理
6. **批量功能** (Phase 21): 用户组批量
7. **历史查询** (Phase 22): 通知记录查询
8. **优化** (Phase 23-24): 性能、安全、文档

---

## 任务管理原则遵循

根据章程第6条任务管理原则，请确保：

- **任务数量控制**: 本项目共有 134 个任务，分为 24 个小阶段，每个阶段 3-14 个任务 (平均 5.6 个/阶段)
- **定期清理**: 在每个开发阶段完成后，主动清理已完成和过期的任务
- **优先级明确**: P1 (Phase 1-6 + 7-13) → P2 (Phase 14-20) → P3 (Phase 21-22)
- **状态实时更新**: 任务状态必须及时更新，保持团队协作效率
- **用户体验优化**: 每个阶段聚焦，任务列表简洁

---

## Summary

- **Total Tasks**: 134
- **任务/阶段**: 平均 5.6 个/阶段 (范围 3-14)
- **阶段总数**: 24

| 阶段范围 | 任务数 | 目标 |
|---------|--------|------|
| Phase 1-6 | 40 | MongoDB 基础设施 (US1 - MVP) |
| Phase 7-13 | 38 | 用户管理系统 (US2 - P1) |
| Phase 14-16 | 15 | Discord + Email (US3, US4 - P2) |
| Phase 17-20 | 18 | Kafka 异步处理 (US5 - P2) |
| Phase 21-22 | 8 | 用户组 + 历史 (US6, US7 - P3) |
| Phase 23-24 | 15 | 优化与文档 |

**Parallel Opportunities Identified**:
- Phase 1: 4 parallel tasks
- Phase 3: 2 parallel tasks
- Phase 4: 4 parallel tasks
- Phase 5: 3 parallel tasks
- Phase 8-10: 每阶段 2-3 parallel tasks
- Phase 11: 3 parallel tasks
- Phase 23-24: 多个并行优化任务

**Suggested MVP Scope**: Phase 1-6 (US1 - MongoDB 基础设施)

**Checkpoint Validation**:
- Phase 6 结束: US1 完成 - MongoDB 作为第一等公民数据库就绪
- Phase 13 结束: US2 完成 - 用户管理系统完成
- Phase 20 结束: US5 完成 - Kafka 异步通知处理完成
