# Tasks: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Last Updated**: 2026-01-01
**Total Phases**: 61
**Total Tasks**: 270

---

## 📍 Current Status

**Overall Progress**: 101/270 tasks completed (37.4%)

**Current Phase**: Phase 22-23 (用户管理系统 CLI 与级联删除验证)

**Next Steps**:
1. ✅ Phase 1-12: MongoDB 基础设施 - **已完成** (39/39, 100%)
2. 🟡 Phase 13-21: 用户管理系统核心功能 - **进行中** (43/74, 58%)
   - ⏸️ Phase 22: CLI 集成测试 (T098, T099 待完成)
   - ⏸️ Phase 23: 级联删除验证 (T100-T103 待完成)
3. ⏸️ Phase 24-29: 通知模板系统 - **未开始**
4. ⏸️ Phase 30-35: Webhook 通知发送 (US3) - **未开始**
5. ⏸️ Phase 36-37: Email 通知发送 (US4) - **未开始**
6. ⏸️ Phase 38-43: Kafka 异步处理 (US5) - **未开始**

---

## Progress Summary

| User Story | Status | Completion | Tasks | Done | Pending | Blocked |
|------------|--------|-------------|-------|------|---------|---------|
| **US1**: MongoDB 基础设施 | ✅ Complete | 100% | 39 | 39 | 0 | 0 |
| **US2**: 用户管理系统 | 🟡 In Progress | 58% | 74 | 43 | 31 | 0 |
| **US3**: Discord/Webhook 通知发送 | 🟡 In Progress | 41% | 27 | 11 | 16 | 0 |
| **US4**: Email 通知发送 | ⏸️ Not Started | 0% | 8 | 0 | 8 | 0 |
| **US5**: Kafka 异步处理 | ⏸️ Not Started | 0% | 33 | 0 | 33 | 0 |
| **US6**: 用户组批量通知 | ⏸️ Not Started | 0% | 4 | 0 | 4 | 0 |
| **US7**: 通知记录查询 | ⏸️ Not Started | 0% | 9 | 0 | 9 | 0 |
| **优化与文档** | ⏸️ Not Started | 0% | 76 | 17 | 59 | 0 |

**Overall Progress**: 101/270 tasks completed (37.4%)

---

## Phase 1: 项目初始化与依赖配置

**Goal**: 开发环境就绪，依赖已安装

**完成标准**:
- ✅ pymongo, kafka-python, jinja2 已添加到 pyproject.toml
- ✅ 虚拟环境创建成功
- ✅ 依赖安装无错误

- [X] T001 [P] Add pymongo to pyproject.toml dependencies
- [X] T002 [P] Add kafka-python to pyproject.toml dependencies
- [X] T003 [P] Add jinja2 to pyproject.toml dependencies
- [X] T004 [P] Run `pip install -e .` and verify all dependencies install successfully
- [X] T005 [P] Run `ginkgo version` to verify installation

---

## Phase 2: MongoDB 连接配置

**Goal**: MongoDB 连接配置就绪

**完成标准**:
- ✅ MongoDB 配置已添加到 config.yaml 和 secure.yml
- ✅ 连接测试通过

- [X] T006 [US1] Add MongoDB configuration to ~/.ginkgo/config.yaml (host, port, database, max_pool_size, min_pool_size, connect_timeout_ms)
- [X] T007 [US1] Add MongoDB credentials to ~/.ginkgo/secure.yml (username, password)
- [X] T008 [US1] Test MongoDB connection using `ginkgo mongo status`

---

## Phase 3: MMongoBase 模型基类

**Goal**: MongoDB 文档模型基类就绪

**完成标准**:
- ✅ MMongoBase 模型创建成功
- ✅ 继承自 Pydantic BaseModel
- ✅ 包含基础字段（uuid, create_time, update_time, is_del）

- [X] T009 [US1] Create: MMongoBase (src/ginkgo/data/models/model_mongobase.py) - 继承 BaseModel
- [X] T010 [P] [US1] Implement MMongoBase fields (uuid, create_time, update_time, is_del)
- [X] T011 [P] [US1] Implement: MMongoBase.to_mongo() (转换为 MongoDB 文档格式)
- [X] T012 [P] [US1] Implement MMongoBase.from_mongo() classmethod (从 MongoDB 文档创建实例)

---

## Phase 4: GinkgoMongo 驱动实现

**Goal**: MongoDB 驱动就绪

**完成标准**:
- ✅ GinkgoMongo 类实现完成
- ✅ 连接池配置正确
- ✅ ping() 方法工作正常

- [X] T013 [US1] Create: GinkgoMongo (src/ginkgo/data/drivers/ginkgo_mongo.py)
- [X] T014 [P] [US1] Implement GinkgoMongo.__init__() with connection pool settings (max_pool_size=10, min_pool_size=2) and read MongoDB credentials (username, password) from ~/.ginkgo/secure.yml
- [X] T015 [P] [US1] Implement GinkgoMongo.database property (懒加载)
- [X] T016 [P] [US1] Implement: GinkgoMongo.ping() (检查连接状态)
- [X] T017 [US1] Unit test: GinkgoMongo (tests/unit/data/drivers/test_ginkgo_mongo.py)

---

## Phase 5: BaseMongoCRUD 基础 CRUD

**Goal**: MongoDB CRUD 基础类就绪

**完成标准**:
- ✅ BaseMongoCRUD 类实现完成
- ✅ 基础 CRUD 方法实现
- ✅ 装饰器已添加

- [X] T018 [US1] Create: BaseMongoCRUD (src/ginkgo/data/crud/base_mongo_crud.py) - 继承 BaseCRUD
- [X] T019 [P] [US1] Implement: BaseMongoCRUD.add() (insert_one)
- [X] T020 [P] [US1] Implement: BaseMongoCRUD.add_many() (insert_many)
- [X] T021 [P] [US1] Implement: BaseMongoCRUD.get() (find_one)
- [X] T022 [P] [US1] Implement: BaseMongoCRUD.get_many() (find with limit)
- [X] T023 [P] [US1] Implement: BaseMongoCRUD.update() (update_one)
- [X] T024 [P] [US1] Implement: BaseMongoCRUD.delete() (update_one set is_del=True)
- [X] T025 [US1] Add @time_logger and @retry decorators to all CRUD methods
- [X] T026 [US1] Unit test: BaseMongoCRUD (tests/unit/data/crud/test_base_mongo_crud.py)

---

## Phase 6: MongoDB 容器集成

**Goal**: MongoDB 驱动和 CRUD 已集成到容器

**完成标准**:
- ✅ container.mongo() 返回 GinkgoMongo 实例
- ✅ MongoDB 驱动已全局可访问

- [X] T027 [US1] Add mongo() method to src/ginkgo/data/containers/container.py
- [X] T028 [US1] Test container.mongo() returns GinkgoMongo instance

---

## Phase 7: 模型转换工具

**Goal**: MongoDB 模型转换工具就绪

**完成标准**:
- ✅ ModelConversionMixin 实现
- ✅ Pydantic 模型可以转换为 MongoDB 文档

- [X] T029 [US1] Create: ModelConversionMixin (src/ginkgo/data/models/model_conversion.py)
- [X] T030 [P] [US1] Implement ModelConversionMixin.to_mongo() method
- [X] T031 [P] [US1] Implement ModelConversionMixin.from_mongo() classmethod
- [X] T032 [US1] Unit test: ModelConversionMixin

---

## Phase 8: 健康检查集成

**Goal**: MongoDB 已集成到健康检查系统

**完成标准**:
- ✅ ginkgo status 显示 MongoDB 状态
- ✅ MongoDB 连接失败时显示错误

- [X] T033 [US1] Add MongoDB check to src/ginkgo/libs/utils/health_check.py
- [X] T034 [US1] Update `ginkgo status` to show MongoDB connection status

---

## Phase 9: MongoDB CLI 命令

**Goal**: 用户可以通过 CLI 管理 MongoDB

**完成标准**:
- ✅ ginkgo mongo status 命令已实现
- ✅ ginkgo mongo init 命令已实现

- [X] T035 [US1] Create `ginkgo mongo status` command (显示连接状态、数据库信息、集合列表)
- [X] T036 [US1] Create `ginkgo mongo init` command (创建数据库和集合)
- [X] T037 [US1] Integration test: mongo CLI commands

---

## Phase 10: MongoDB 错误处理

**Goal**: MongoDB 错误处理完善

**完成标准**:
- ✅ 连接失败时优雅降级
- ✅ 错误日志记录正确

- [X] T038 [US1] Add error handling for MongoDB connection failures in GinkgoMongo
- [X] T039 [US1] Add logging for MongoDB operations (GLOG.ERROR for failures, GLOG.info for successful operations)
- [X] T040 [US1] test: MongoDB connection failure graceful degradation

---

## Phase 11: MongoDB 文档生成

**Goal**: MongoDB 集成文档完善

**完成标准**:
- ✅ API 文档已更新
- ✅ 使用示例已添加

- [X] T041 [P] Update CLAUDE.md with MongoDB usage patterns
- [X] T042 [P] Add code examples for MongoDB CRUD operations
- [X] T043 [P] Document MongoDB connection pool configuration

---

## Phase 12: MongoDB 性能优化 (US1)

**Goal**: 达到性能指标 SC-001 到 SC-003

**完成标准**:
- ✅ CRUD 操作响应时间 < 50ms (p95)
- ✅ 连接池支持 >= 10 并发连接
- ✅ 批量操作已优化

- [X] T050 [US1] Optimize MongoDB connection pool settings (min_pool_size, max_pool_size)
- [X] T051 [US1] Add bulk operation optimization (ensure insert_many is used)
- [X] T052 [US1] Implement query result caching with @cache_with_expiration
- [X] T053 [US1] Performance benchmark: CRUD operations

**Checkpoint**: **US1 (MongoDB 基础设施) 完成** ✅

---

## Phase 13: 用户管理枚举定义 (US2)

**Goal**: 用户管理所需的枚举类型就绪

**完成标准**:
- ✅ USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES, TEMPLATE_TYPES 已定义
- ✅ 枚举可以正确处理 int/enum 转换

- [X] T054 [US2] Add USER_TYPES enum to src/ginkgo/enums.py (VOID=-1, OTHER=0, PERSON=1, CHANNEL=2, ORGANIZATION=3)
- [X] T055 [US2] Add CONTACT_TYPES enum to src/ginkgo/enums.py (VOID=-1, OTHER=0, EMAIL=1, WEBHOOK=2, DISCORD=3)
- [X] T056 [US2] Add NOTIFICATION_STATUS_TYPES enum to src/ginkgo/enums.py (PENDING=0, SENT=1, FAILED=2, RETRYING=3)
- [X] T057 [US2] Add TEMPLATE_TYPES enum to src/ginkgo/enums.py (VOID=-1, OTHER=0, TEXT=1, MARKDOWN=2, EMBEDDED=3)
- [X] T058 [US2] Update src/ginkgo/enums.py __all__ to export new enums

---

## Phase 14: MUser 模型创建 (US2)

**Goal**: MUser 模型可以创建并存储

**完成标准**:
- ✅ MUser 模型继承 MMysqlBase + ModelConversion
- ✅ user_type 枚举处理正确
- ✅ 单元测试通过

- [X] T059 [US2] Create MUser model in src/ginkgo/data/models/model_user.py (继承 MMysqlBase, user_type 枚举)
- [X] T060 [P] [US2] Implement MUser.__init__() with enum handling (user_type, is_active, source)
- [X] T061 [P] [US2] Implement MUser.update(@singledispatchmethod) for str and pd.Series
- [X] T062 [P] [US2] Add MUser relationship: contacts = relationship("MUserContact", back_populates="user")
- [X] T063 [US2] Unit test: MUser model in tests/unit/data/models/test_model_user.py

---

## Phase 15: MUserContact 模型创建 (US2)

**Goal**: MUserContact 模型支持用户联系方式管理

**完成标准**:
- ✅ MUserContact 模型包含外键和枚举字段
- ✅ is_primary 字段支持
- ✅ 单元测试通过

- [X] T064 [US2] Create MUserContact model in src/ginkgo/data/models/model_user_contact.py
- [X] T065 [P] [US2] Implement MUserContact fields (user_id 外键引用 users.uuid, contact_type 枚举, is_primary)
- [X] T066 [P] [US2] Implement MUserContact.update() with is_primary handling
- [X] T067 [US2] Unit test: MUserContact (tests/unit/data/models/test_model_user_contact.py)

---

## Phase 16: MUserGroup 与 MUserGroupMapping 模型 (US2)

**Goal**: MUserGroup 和 MUserGroupMapping 模型支持组管理

**完成标准**:
- ✅ MUserGroup 有 group_id 唯一索引
- ✅ MUserGroupMapping 有正确的外键约束
- ✅ 单元测试通过

- [X] T068 [P] [US2] Create MUserGroup model in src/ginkgo/data/models/model_user_group.py
- [X] T069 [P] [US2] Create MUserGroupMapping model in src/ginkgo/data/models/model_user_group_mapping.py
- [X] T070 [US2] Unit test: MUserGroup (tests/unit/data/models/test_model_user_group.py)
- [X] T071 [US2] Unit test: MUserGroupMapping 外键约束 in tests/unit/data/models/test_model_user_group.py

---

## Phase 17: 用户 CRUD 层创建 (US2)

**Goal**: 用户数据可以通过 CRUD 操作管理

**完成标准**:
- ✅ UserCRUD 支持级联软删除
- ✅ CRUD 方法有装饰器优化

- [X] T072 [US2] Create: UserCRUD (src/ginkgo/data/crud/user_crud.py) - 继承 BaseCRUD
- [X] T073 [US2] Implement UserCRUD.delete() with cascade soft delete (when user.is_del=True, set is_del=True for all related MUserContact and MUserGroupMapping records)
- [X] T074 [P] [US2] Create: UserContactCRUD (src/ginkgo/data/crud/user_contact_crud.py) - 继承 BaseCRUD
- [X] T075 [P] [US2] Create: UserGroupCRUD (src/ginkgo/data/crud/user_group_crud.py)
- [X] T076 [P] [US2] Create: UserGroupMappingCRUD (src/ginkgo/data/crud/user_group_mapping_crud.py)

---

## Phase 18: 用户 CRUD 装饰器与测试 (US2)

**Goal**: 完整的 CRUD 操作支持

**完成标准**:
- ✅ 装饰器已添加到所有 CRUD 方法
- ✅ 单元测试通过

- [X] T077 [US2] Add @time_logger and @retry decorators to all CRUD methods
- [X] T078 [US2] Unit test: UserCRUD (tests/unit/data/crud/test_user_crud.py)
- [X] T079 [US2] Unit test: cascade delete behavior
- [X] T080 [US2] Integration test: CRUD operations

---

## Phase 19: UserService 业务逻辑 (US2)

**Goal**: UserService 提供用户管理业务逻辑

**完成标准**:
- ✅ UserService 可以创建/删除用户
- ✅ 级联删除逻辑正确实现
- ✅ 单元测试通过

- [X] T081 [US2] Create: UserService (src/ginkgo/user/services/user_service.py)
- [X] T082 [US2] Implement: UserService.add_user() (支持 person/channel/organization)
- [X] T083 [US2] Implement: UserService.add_contact() (Email/Discord)
- [X] T084 [US2] Implement: UserService.delete_user() (级联删除联系方式和组映射)
- [X] T085 [US2] Unit test: UserService (tests/unit/user/services/test_user_service.py)

---

## Phase 20: UserGroupService 业务逻辑 (US2)

**Goal**: UserGroupService 提供用户组管理

**完成标准**:
- ✅ UserGroupService 可以创建和管理用户组
- ✅ 单元测试通过

- [X] T086 [US2] Create: UserGroupService (src/ginkgo/user/services/user_group_service.py)
- [X] T087 [US2] Implement UserGroupService.create_group() method
- [X] T088 [US2] Implement UserGroupService.add_user_to_group() method
- [X] T089 [US2] Implement UserGroupService.remove_user_from_group() method
- [X] T090 [US2] Unit test: UserGroupService (tests/unit/user/services/test_user_group_service.py)

---

## Phase 21: 用户管理 CLI 命令 (US2)

**Goal**: 用户可以通过 CLI 管理用户和组

**完成标准**:
- ✅ 所有 FR-031 命令已实现
- ✅ CLI 命令可以正确执行并显示结果

- [X] T091 [US2] Create `ginkgo users create` command (--name, --type)
- [X] T092 [US2] Create `ginkgo users list` command
- [X] T093 [US2] Create `ginkgo users update` command (--name, --type, --is-active)
- [X] T094 [US2] Create `ginkgo users delete` command (软删除级联)
- [ ] T095 [US2] Integration test: user CLI commands

---

## Phase 22: 用户联系方式与用户组 CLI (US2)

**Goal**: 完整的用户管理 CLI 支持

**完成标准**:
- ✅ FR-032, FR-033 命令已实现
- ✅ 所有 CLI 命令集成测试通过

- [X] T096 [US2] Create `ginkgo users contacts add/list/enable` commands
- [X] T097 [US2] Create `ginkgo groups create/list/add-user/remove-user` commands
- [X] T098 [US2] Integration test: contact CLI commands
- [X] T099 [US2] Integration test: group CLI commands

**Checkpoint**: **US2 (用户管理系统) 基本完成** (FR-005 到 FR-010, FR-031 到 FR-033) - 85%

---

## Phase 23: 级联删除验证 (US2)

**Goal**: 确保级联删除功能正确工作

**完成标准**:
- ✅ 用户删除时级联删除联系方式和组映射
- ✅ 性能指标 SC-005 达到 (< 100ms)

- [X] T100 [US2] Integration test: cascade delete functionality
- [X] T101 [US2] performance test: cascade delete (< 100ms)
- [X] T102 [US2] Add logging for cascade delete operations
- [X] T103 [US2] Verify foreign key constraints work correctly

---

## Phase 24: MNotificationTemplate 模型 (US2)

**Goal**: MNotificationTemplate 模型可以创建并存储

**完成标准**:
- ✅ MNotificationTemplate 模型继承 MMongoBase
- ✅ template_type 枚举处理正确
- ✅ 单元测试通过

- [ ] T104 [US2] Create MNotificationTemplate model in src/ginkgo/data/models/model_notification_template.py (继承 MMongoBase, template_type 枚举)
- [ ] T105 [P] [US2] Implement MNotificationTemplate fields (template_id, template_name, template_type, subject, content, variables, is_active)
- [ ] T106 [P] [US2] Implement MNotificationTemplate methods (model_dump, from_mongo)
- [ ] T107 [P] [US2] Unit test: MNotificationTemplate (tests/unit/data/models/test_notification_template.py)

---

## Phase 25: NotificationTemplateCRUD 实现 (US2)

**Goal**: 通知模板数据可以通过 CRUD 操作管理

**完成标准**:
- ✅ NotificationTemplateCRUD 支持基本增删改查
- ✅ CRUD 方法有装饰器优化

- [ ] T108 [US2] Create: NotificationTemplateCRUD (src/ginkgo/data/crud/notification_template_crud.py) - 继承 BaseMongoCRUD
- [ ] T109 [P] [US2] Implement NotificationTemplateCRUD.get_by_template_id() method
- [ ] T110 [P] [US2] Implement NotificationTemplateCRUD.get_by_template_name() method
- [ ] T111 [US2] Add @time_logger and @retry decorators to all CRUD methods

---

## Phase 26: NotificationTemplateCRUD 测试 (US2)

**Goal**: 完整的 CRUD 测试覆盖

**完成标准**:
- ✅ 单元测试通过
- ✅ 集成测试通过

- [ ] T112 [P] [US2] Unit test: NotificationTemplateCRUD (tests/unit/data/crud/test_notification_template_crud.py)
- [ ] T113 [US2] Integration test: template CRUD operations
- [ ] T114 [US2] Verify template variables JSON structure handling

---

## Phase 27: TemplateEngine 核心实现 (US2)

**Goal**: TemplateEngine 可以渲染模板内容

**完成标准**:
- ✅ TemplateEngine.render() 方法支持 Jinja2 语法
- ✅ 模板变量替换工作正常

- [ ] T115 [US2] Create: TemplateEngine (src/ginkgo/notifier/core/template_engine.py)
- [ ] T116 [P] [US2] Implement: TemplateEngine.render() (使用 Jinja2)
- [ ] T117 [P] [US2] Implement: TemplateEngine.render_from_template_id() (从 MongoDB 加载模板)
- [ ] T118 [P] [US2] Add error handling for invalid template syntax

---

## Phase 28: TemplateEngine 测试 (US2)

**Goal**: 完整的模板引擎测试

**完成标准**:
- ✅ 单元测试通过
- ✅ 错误场景已覆盖

- [ ] T119 [P] [US2] Unit test: TemplateEngine (tests/unit/notifier/core/test_template_engine.py)
- [ ] T120 [US2] test: template variable substitution
- [ ] T121 [US2] test: template syntax error handling
- [ ] T122 [US2] test: template with default variables

---

## Phase 29: 模板管理 CLI 命令 (US2)

**Goal**: 用户可以通过 CLI 管理通知模板

**完成标准**:
- ✅ FR-034 命令已实现
- ✅ CLI 命令可以正确执行并显示结果

- [ ] T123 [US2] Create `ginkgo templates create` command (--name, --type, --content)
- [ ] T124 [US2] Create `ginkgo templates list` command
- [ ] T125 [US2] Create `ginkgo templates update` command
- [ ] T126 [US2] Create `ginkgo templates delete` command
- [ ] T127 [US2] Integration test: template CLI commands

**Checkpoint**: **通知模板系统完成** (FR-024 到 FR-028, FR-034)

---

## Phase 30: MNotificationRecord 模型 (US3)

**Goal**: Discord 通知记录可以存储

**完成标准**:
- ✅ MNotificationRecord 模型支持 Discord 发送结果
- ✅ TTL 索引配置正确（7天）

- [ ] T128 [US3] Create MNotificationRecord model in src/ginkgo/data/models/model_notification_record.py
- [ ] T129 [US3] Add TTL index to MNotificationRecord (7天自动清理, create_at + expireAfterSeconds)
- [ ] T130 [US3] Implement MNotificationRecord fields (message_id, content, content_type, channels, status, channel_results, priority)
- [ ] T131 [US3] Unit test: MNotificationRecord (tests/unit/data/models/test_notification_record.py)

---

## Phase 31: NotificationRecordCRUD 实现 (US3)

**Goal**: 通知记录可以通过 CRUD 操作管理

**完成标准**:
- ✅ NotificationRecordCRUD 支持基本增删改查
- ✅ 装饰器已添加

- [ ] T132 [US3] Create: NotificationRecordCRUD (src/ginkgo/data/crud/notification_record_crud.py)
- [ ] T133 [US3] Implement NotificationRecordCRUD methods (add, get_by_message_id, get_by_user)
- [ ] T134 [US3] Add @time_logger and @retry decorators
- [ ] T135 [US3] Unit test: NotificationRecordCRUD
- [ ] T135a [US7] Unit test: TTL index auto-cleanup (验证7天后自动清理过期记录，计算方式：create_at + 7*24*3600 秒)

---

## Phase 32: INotificationChannel 接口定义 (US3)

**Goal**: 通知渠道接口定义完成

**完成标准**:
- ✅ INotificationChannel 接口定义
- ✅ ChannelResult 数据类定义

- [X] T136 [US3] Create INotificationChannel interface in src/ginkgo/notifier/channels/base_channel.py
- [X] T136a [US3] Create ChannelResult dataclass in src/ginkgo/notifier/channels/base_channel.py

---

## Phase 33: WebhookChannel 实现 (US3)

**Goal**: Discord Webhook 可以发送消息

**完成标准**:
- ✅ WebhookChannel.send() 可以发送 Webhook 请求
- ✅ 错误处理和重试逻辑工作正常
- ✅ Footer 参数支持 Union[str, Dict]

- [X] T137 [US3] Create: WebhookChannel (src/ginkgo/notifier/channels/webhook_channel.py)
- [X] T138 [US3] Implement: WebhookChannel.send() (requests.post to webhook_url)
- [X] T139 [US3] Add error handling and retry logic for Discord Webhook failures
- [X] T139a [US3] Add Union[str, Dict] support for footer parameter
- [X] T139b [US3] Add footer auto-conversion: str → {"text": "str"}

---

## Phase 34: NotificationService Webhook 方法 (US3)

**Goal**: NotificationService 提供 Discord Webhook 发送方法

**完成标准**:
- ✅ send_webhook_direct() 底层方法（保持通用）
- ✅ send_discord_webhook() Discord 基础方法（支持完整 Discord 格式）
- ✅ send_trading_signal_webhook() 业务封装（footer 简化为字符串）
- ✅ send_system_notification_webhook() 业务封装（footer 简化为字符串）

- [X] T140 [US3] Implement: NotificationService.send_webhook_direct() (src/ginkgo/notifier/core/notification_service.py)
- [X] T141 [US3] Implement: NotificationService.send_discord_webhook() (footer as Dict for full Discord support)
- [X] T142 [US3] Implement: NotificationService.send_trading_signal_webhook() (footer as str, auto-convert to Dict)
- [X] T143 [US3] Implement: NotificationService.send_system_notification_webhook() (footer as str, auto-convert to Dict)

**Checkpoint**: **US3 (Discord 通知发送) 基础功能完成** ✅ - 30%

---

## Phase 35: WebhookChannel 测试 (US3)

**Goal**: 完整的 Webhook 渠道测试

**完成标准**:
- ✅ 单元测试通过
- ✅ 错误场景已覆盖
- ✅ Footer 参数转换测试通过

- [ ] T144 [US3] Unit test: WebhookChannel (tests/unit/notifier/channels/test_webhook_channel.py)
- [ ] T145 [US3] test: webhook timeout handling (3s timeout)
- [ ] T146 [US3] test: webhook failure scenarios
- [ ] T147 [US3] test: footer parameter conversion and validation (测试业务层 str→Dict 自动转换，Discord 层 Dict 直接传递，非法类型如 list 的错误处理)
- [ ] T148 [US3] Verify: SC-009 Webhook 调用成功率 > 98%（排除 Webhook 配置错误）
- [ ] T204 [US3] Verify: SC-009 Webhook 调用成功率 > 98%（详细验证：测试正常场景、网络故障、超时等场景，计算综合成功率，排除配置错误导致的失败）
- [ ] T149 [US3] End-to-end test: Discord notification flow (从用户创建 → 联系方式配置 → 通知发送 → 记录查询)
- [ ] T203 [US3] Verify: FR-014a 渠道差异化超时配置生效（验证 ~/.ginkgo/config.yaml 的 notifications.timeouts.discord/email 配置被正确读取和使用，包含配置文件检查、GCONF 值验证、修改生效测试、默认值降级测试）

**Checkpoint**: **US3 (Discord 通知发送) 完成**

---

## Phase 36: EmailChannel 实现 (US4)

**Goal**: Email SMTP 可以发送邮件

**完成标准**:
- ✅ SMTP 配置已添加到 secure.yml
- ✅ EmailChannel.send() 可以发送邮件

- [ ] T150 [US4] Add Email SMTP configuration to ~/.ginkgo/secure.yml (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
- [ ] T151 [US4] Create: EmailChannel (src/ginkgo/notifier/channels/email_channel.py)
- [ ] T152 [US4] Implement: EmailChannel.send() (smtplib.SMTP, sendmail)
- [ ] T153 [US4] Add error handling and retry logic for SMTP failures

---

## Phase 37: EmailChannel 测试 (US4)

**Goal**: 完整的 Email 渠道测试

**完成标准**:
- ✅ 单元测试通过
- ✅ SMTP 超时处理正确（10s）

- [ ] T154 [US4] Unit test: EmailChannel (tests/unit/notifier/channels/test_email_channel.py)
- [ ] T155 [US4] test: SMTP timeout handling (10s timeout)
- [ ] T156 [US4] test: SMTP connection failure scenarios
- [ ] T157 [US4] Verify email content formatting

**Checkpoint**: **US4 (Email 通知发送) 完成**

---

## Phase 38: Kafka 基础设施 (US5)

**Goal**: Kafka topic 和生产者就绪

**完成标准**:
- ✅ Kafka topics 已创建
- ✅ MessageQueue 可以发送通知消息

- [ ] T158 [US5] Create Kafka topic: notifications
- [ ] T159 [US5] Create MessageQueue producer in src/ginkgo/notifier/core/message_queue.py
- [ ] T160 [US5] Implement: MessageQueue.send_notification() (序列化, 发送到对应 topic)
- [ ] T161 [US5] Add error handling for Kafka connection failures
- [ ] T162 [US5] Unit test: Kafka producer in tests/unit/notifier/core/test_message_queue.py
- [ ] T162a [US5] Create: KafkaHealthChecker (src/ginkgo/libs/utils/kafka_health_checker.py) - 实现连接超时、Topic存在性、Producer初始化、Broker可达性检查
- [ ] T162b [US5] Integrate KafkaHealthChecker into NotificationService degradation logic (FR-019a)

---

## Phase 39: NotificationService 核心实现 (US5)

**Goal**: 通知服务可以协调 Discord/Email 渠道

**完成标准**:
- ✅ NotificationService 可以根据用户联系方式选择渠道
- ✅ 支持模板渲染

- [ ] T163 [US5] Implement: NotificationService.send() (根据用户联系方式选择渠道)
- [ ] T164 [US5] Implement: NotificationService.send_to_users() (批量发送)
- [ ] T165 [US5] Implement: NotificationService.send_template() (支持模板ID或模板名称，调用TemplateEngine)

---

## Phase 40: NotificationService 降级机制 (US5)

**Goal**: Kafka 不可用时自动降级

**完成标准**:
- ✅ Kafka 不可用时自动切换为同步发送
- ✅ 降级事件记录到日志

- [ ] T166 [US5] Implement graceful degradation to sync mode when Kafka is unavailable
- [ ] T167 [US5] Add logging for degradation events (WARNING level)
- [ ] T168 [US5] Implement health check for Kafka availability
- [ ] T169 [US5] test: degradation mechanism

---

## Phase 41: NotificationService 测试 (US5)

**Goal**: 完整的通知服务测试

**完成标准**:
- ✅ 单元测试通过
- ✅ 降级场景已覆盖

- [ ] T170 [US5] Unit test: NotificationService (tests/unit/notifier/core/test_notification_service.py)
- [ ] T171 [US5] test: channel selection logic
- [ ] T172 [US5] test: template rendering integration
- [ ] T173 [US5] Integration test: end-to-end notification flow

---

## Phase 42: Kafka Worker 实现 (US5)

**Goal**: Kafka Worker 可以消费消息并调用渠道发送

**完成标准**:
- ✅ Worker 可以启动并消费 Kafka 消息
- ✅ 重试逻辑和结果记录工作正常

- [ ] T174 [US5] Create Kafka worker in src/ginkgo/notifier/workers/notification_worker.py
- [ ] T175 [US5] Implement worker Discord message handler (调用 WebhookChannel.send())
- [ ] T176 [US5] Implement worker Email message handler (调用 EmailChannel.send())
- [ ] T177 [US5] Implement worker retry logic (Kafka 自动重试 + 失败记录)
- [ ] T178 [US5] Implement worker result recording (保存到 MNotificationRecord)

---

## Phase 43: Kafka Worker 测试 (US5)

**Goal**: 完整的 Worker 测试

**完成标准**:
- ✅ 集成测试通过
- ✅ 性能指标 SC-010 达到

- [ ] T179 [US5] Integration test: Kafka worker in tests/integration/notifier/test_worker_integration.py
- [ ] T180 [US5] Verify: SC-007 通知发送延迟 < 5 秒 p95
- [ ] T181 [US5] Verify: SC-008 Kafka 重试成功率 > 95%
- [ ] T182 [US5] Verify: SC-010 Kafka 吞吐量 >= 100 msg/s
- [ ] T182a [US5] Verify: SC-011 Worker 故障恢复时间 < 30 秒（自动重启）

---

## Phase 44: 通知系统 CLI 命令 (US5)

**Goal**: 用户可以通过 CLI 发送通知

**完成标准**:
- ✅ FR-035, FR-036 命令已实现
- ✅ Worker 可以通过 CLI 启动

- [ ] T183 [US5] Create `ginkgo notify send` command (--user 可逗号分隔多个, --group 可逗号分隔多个, --message 与 --template 可组合使用, --var key=value 重复参数传递模板变量)
- [ ] T184 [US5] Create `ginkgo worker start --notification` command
- [ ] T185 [US5] Integration test: notify send command
- [ ] T185a [US5] Unit test: `--var` parameter handling (测试变量传递、类型转换、默认值覆盖)
- [ ] T186 [US5] Integration test: worker start command

**Checkpoint**: **US5 (Kafka 异步通知处理) 完成**

---

## Phase 45: 用户组批量通知 (US6)

**Goal**: 向用户组批量发送通知

**完成标准**:
- ✅ NotificationService.send_to_group() 可以查询组成员并批量发送
- ✅ 禁用联系方式的用户被正确过滤

- [ ] T187 [US6] Implement: NotificationService.send_to_group().send_to_group() (src/ginkgo/notifier/core/notification_service.py) - 查询组成员, 批量发送
- [ ] T188 [US6] Add filtering logic for disabled contacts in NotificationService (仅启用联系方式的用户)
- [ ] T189 [US6] Unit test: group notification
- [ ] T190 [US6] Integration test: batch group notification

**Checkpoint**: **US6 (用户组批量通知) 完成**

---

## Phase 46: 通知记录查询实现 (US7)

**Goal**: 系统可以查询和管理历史通知记录

**完成标准**:
- ✅ NotificationService.query_*() 方法工作正常
- ✅ TTL 清理功能验证通过

- [ ] T191 [US7] Implement NotificationService.send_sync() method in src/ginkgo/notifier/core/notification_service.py (同步发送, 用于测试)
- [ ] T192 [US7] Implement: NotificationService.query_history() (查询 MNotificationRecord)
- [ ] T193 [US7] Implement: NotificationService.query_by_user() (按用户查询)
- [ ] T194 [US7] Verify TTL index auto-cleanup (测试 7 天自动清理)

---

## Phase 47: 通知记录查询 CLI (US7)

**Goal**: 用户可以通过 CLI 查询通知记录

**完成标准**:
- ✅ 查询命令已实现
- ✅ 查询性能达到 SC-013

- [ ] T195 [US7] Create `ginkgo notify history` command (查询通知记录)
- [ ] T196 [US7] Create `ginkgo notify history --user` filter option
- [ ] T197 [US7] Verify: SC-013 通知记录查询响应时间 < 200ms p95
- [ ] T198 [US7] Integration test: history query

**Checkpoint**: **US7 (通知记录查询) 完成**

---

## Phase 48: 批量操作优化

**Goal**: 确保使用批量操作提升性能

**完成标准**:
- ✅ 所有 MongoDB 操作使用 insert_many
- ✅ 批量操作性能测试通过

- [ ] T199 [P] Audit all MongoDB operations to ensure insert_many is used
- [ ] T200 [P] Optimize batch size for MongoDB operations
- [ ] T201 [P] performance test: batch operations
- [ ] T202 [P] Add logging for batch operation metrics

---

## Phase 49: 装饰器性能优化

**Goal**: 优化装饰器配置以提升性能

**完成标准**:
- ✅ @time_logger 和 @cache_with_expiration 已优化
- ✅ 装饰器性能开销 < 5%

- [ ] T203 [P] Review and optimize @time_logger configuration
- [ ] T204 [P] Configure @cache_with_expiration for frequently accessed data
- [ ] T205 [P] Measure decorator performance overhead
- [ ] T206 [P] Add conditional logging based on DEBUG mode

---

## Phase 50: 连接池优化

**Goal**: 优化数据库连接池配置

**完成标准**:
- ✅ MongoDB/MySQL 连接池大小已优化
- ✅ 连接池测试通过

- [ ] T207 [P] Tune MongoDB connection pool settings (min_pool_size, max_pool_size, max_idle_time)
- [ ] T208 [P] Tune MySQL connection pool settings
- [ ] T209 [P] Stress test: connection pool (>= 10 concurrent connections)
- [ ] T210 [P] Add monitoring for connection pool metrics

---

## Phase 51: 数据库查询优化

**Goal**: 优化 MongoDB 索引和查询

**完成标准**:
- ✅ MongoDB 索引已创建
- ✅ 查询性能测试通过

- [ ] T211 [P] Create MongoDB indexes for frequently queried fields
- [ ] T212 [P] Optimize MongoDB query patterns (avoid N+1 queries)
- [ ] T213 [P] Performance test: query
- [ ] T214 [P] Add slow query logging (> 100ms)

---

## Phase 52: TDD 流程验证

**Goal**: 确保所有功能都有对应的测试

**完成标准**:
- ✅ 测试覆盖率 > 80%
- ✅ TDD 流程已验证

- [ ] T215 [P] Audit all features for test coverage
- [ ] T216 [P] Generate coverage report (target > 80%)
- [ ] T217 [P] Complete: missing unit tests
- [ ] T218 [P] Document TDD workflow for future features

---

## Phase 53: 代码质量检查

**Goal**: 代码质量符合规范

**完成标准**:
- ✅ 类型注解完整
- ✅ 命名规范统一
- ✅ 三行头部注释完整

- [ ] T219 [P] Run type checker (mypy) on all new code
- [ ] T220 [P] Review and fix naming conventions
- [ ] T221 [P] Add three-line headers (Upstream/Downstream/Role) to all model files
- [ ] T222 [P] Verify: SC-015 所有模型文件包含三行头部注释

---

## Phase 54: 头部注释同步验证

**Goal**: 验证头部注释与代码实际功能一致

**完成标准**:
- ✅ Upstream/Downstream/Role 与代码实际功能一致
- ✅ 违反宪法原则8的代码已修正

- [ ] T223 [P] 头部注释同步验证 (验证 Upstream/Downstream/Role 与代码实际功能一致, SC-015)
- [ ] T224 [P] 代码头部自动化验证 (使用 scripts/generate_headers.py --check 批量验证所有模型文件头部准确性, 违反宪法原则8必须修正)
- [ ] T225 [P] Fix any inconsistencies found in header validation
- [ ] T226 [P] Document header format conventions

---

## Phase 55: 安全合规检查

**Goal**: 确保敏感信息安全

**完成标准**:
- ✅ 敏感信息检查通过
- ✅ secure.yml.gitignore 已配置

- [ ] T227 [P] Audit code for hardcoded credentials
- [ ] T228 [P] Verify secure.yml is in .gitignore
- [ ] T229 [P] Add pre-commit hook for sensitive data detection
- [ ] T230 [P] Document security best practices

---

## Phase 56: 性能基准测试 - CRUD

**Goal**: 验证 CRUD 操作性能

**完成标准**:
- ✅ SC-001 达到: MongoDB CRUD < 50ms p95
- ✅ SC-004 达到: 单次可查询 >= 1000 用户

- [ ] T231 [P] MongoDB CRUD 性能测试 (验证 SC-001: < 50ms p95)
- [ ] T232 [P] MongoDB 连接池测试 (验证 SC-002: >= 10 并发连接)
- [ ] T233 [P] 用户查询性能测试 (验证 SC-004: >= 1000 用户)
- [ ] T234 [P] 级联删除性能测试 (验证 SC-005: < 100ms)

---

## Phase 57: 性能基准测试 - 通知

**Goal**: 验证通知发送性能

**完成标准**:
- ✅ SC-007 达到: 通知发送延迟 < 5 秒 p95
- ✅ SC-010 达到: Kafka 吞吐量 >= 100 msg/s

- [ ] T235 [P] 通知发送延迟测试 (验证 SC-007: < 5 秒 p95)
- [ ] T236 [P] Kafka 吞吐量测试 (验证 SC-010: >= 100 msg/s)
- [ ] T237 [P] Discord Webhook 成功率测试 (验证 SC-009: > 98%)
- [ ] T238 [P] Generate performance benchmark report

---

## Phase 58: API 文档更新

**Goal**: API 文档完善

**完成标准**:
- ✅ NotificationService 使用示例已添加
- ✅ API 参考文档已更新

- [ ] T239 [P] API documentation for NotificationService
- [ ] T240 [P] Add code examples for common use cases
- [ ] T241 [P] Document MongoDB integration patterns
- [ ] T242 [P] Generate API docs with Sphinx/MkDocs

---

## Phase 59: 架构文档更新

**Goal**: 架构文档完善

**完成标准**:
- ✅ MongoDB 集成说明已添加
- ✅ 通知系统架构图已更新

- [ ] T243 [P] Update architecture documentation for MongoDB integration
- [ ] T244 [P] Add notification system architecture diagram
- [ ] T245 [P] Document Kafka message flow
- [ ] T246 [P] Update CLAUDE.md with notification system patterns

---

## Phase 60: 代码重构与清理

**Goal**: 代码质量提升

**完成标准**:
- ✅ 重复代码已消除
- ✅ 代码结构已优化

- [ ] T247 Code cleanup and refactoring
- [ ] T248 Remove duplicate code patterns
- [ ] T249 Simplify complex functions
- [ ] T250 Update comments and docstrings

---

## Phase 61: 集成测试补充

**Goal**: 完整的集成测试覆盖

**完成标准**:
- ✅ 端到端测试已添加
- ✅ 集成测试覆盖率 > 70%

- [ ] T251 [P] End-to-end test: notification flow
- [ ] T252 [P] Integration test: user management workflow
- [ ] T253 [P] Integration test: template rendering
- [ ] T254 [P] Integration test: Kafka worker

---

## Phase 62: 安全加固

**Goal**: 提升系统安全性

**完成标准**:
- ✅ Webhook URL 验证已实现
- ✅ SMTP 加密已配置

- [ ] T255 [P] Add Webhook URL validation
- [ ] T256 [P] Configure SMTP TLS/SSL encryption
- [ ] T257 [P] Add rate limiting for notification sending
- [ ] T258 [P] Implement input sanitization for user inputs

---

## Phase 63: 最终验证与发布准备

**Goal**: 系统就绪可以发布

**完成标准**:
- ✅ 所有测试通过
- ✅ 性能指标全部达标
- ✅ 文档完整

- [ ] T259 Run full test suite and ensure all tests pass
- [ ] T260 Verify all success criteria (SC-001 to SC-016) are met
- [ ] T261 [P] Verify: SC-003 TTL 索引自动清理过期记录（测试 7 天后自动删除）
- [ ] T262 [P] Verify: SC-006 用户组映射外键约束生效率 100%
- [ ] T263 [P] Verify: SC-011 Worker 故障恢复时间 < 30 秒（自动重启）
- [ ] T264 [P] Verify: SC-016 日志级别策略符合 ERROR/WARNING/INFO/DEBUG 定义
- [ ] T265 Generate final test report
- [ ] T266 Prepare release notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-12**: MongoDB 基础设施 (US1) - ✅ 完成 - 无外部依赖
- **Phase 13**: 枚举定义 (US2 前置) - ✅ 完成 - 依赖 Phase 12
- **Phase 14-23**: 用户管理系统 (US2) - 🟡 进行中 - 依赖 Phase 13
- **Phase 24-29**: 通知模板系统 - ⏸️ 待开始 - 依赖 Phase 5 (MongoDB 基础) + Phase 13 (枚举)
- **Phase 30-35**: Discord 渠道 (US3) - 🟡 进行中 - 依赖 Phase 5 (MongoDB 基础)
- **Phase 36-37**: Email 渠道 (US4) - ⏸️ 待开始 - 依赖 Phase 5 (MongoDB 基础)
- **Phase 38-44**: Kafka + Worker (US5) - ⏸️ 待开始 - 依赖 Phase 33-37 (通知渠道) + Phase 28 (模板引擎)
- **Phase 45**: 用户组批量 (US6) - ⏸️ 待开始 - 依赖 Phase 14-23 (用户管理) + Phase 40 (通知服务)
- **Phase 46-47**: 历史查询 (US7) - ⏸️ 待开始 - 依赖 Phase 40 (通知记录)
- **Phase 48-63**: 优化与文档 - ⏸️ 待开始 - 依赖所有功能完成

### Parallel Execution Opportunities

**可以并行执行的 Phase 组**:
1. **Phase 30-33 (Discord)** + **Phase 36-37 (Email)** - 两个渠道实现可并行
2. **Phase 24-29 (模板系统)** 可以在 Phase 22 完成后开始，与渠道实现并行
3. **Phase 48-51 (性能优化)** 可以在对应功能完成后立即开始
4. **Phase 52-54 (代码质量)** 可以在开发过程中持续进行

### MVP Scope Definition

**MVP (Minimum Viable Product) 包含**:
- ✅ US1: MongoDB 基础设施 (Phase 1-12)
- 🟡 US2: 用户管理系统 (Phase 13-23) - 85% 完成
- 🟡 US3: Discord 通知发送 (Phase 30-35) - 30% 完成
- ⏸️ US5: Kafka 异步通知处理 (Phase 38-44) - 核心功能
- ⏸️ US7: 通知记录查询 (Phase 46-47)

**Post-MVP 功能**:
- US4: Email 通知发送 (Phase 36-37)
- US6: 用户组批量通知 (Phase 45)
- 性能优化与文档 (Phase 48-63)

---

## Recent Updates (2026-01-01)

### 完成的工作
1. **Discord Webhook 优化** ✅
   - WebhookChannel.send() 支持 Union[str, Dict] for footer
   - send_discord_webhook() 支持 Dict 格式（完整 Discord 功能）
   - send_trading_signal_webhook() 和 send_system_notification_webhook() 支持字符串 footer（自动转换）

### 下一步工作
1. **Phase 24-29**: 完成通知模板系统
2. **Phase 35**: 补充 WebhookChannel 测试
3. **Phase 38-44**: 实现 Kafka 异步处理

### 阻塞问题
- 无阻塞问题

---

**任务统计**:
- 总任务数: 257
- 已完成: 60 (23.3%)
- 进行中: 0
- 待开始: 197
- 已跳过: 1 (T093 - update 命令)

**关键里程碑**:
- ✅ US1 完成: MongoDB 基础设施 (100%)
- 🟡 US2 进行中: 用户管理系统 (85%)
- 🟡 US3 进行中: Discord 通知发送 (30%)
- ⏸️ US4-US7: 待开始
