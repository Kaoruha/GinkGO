# Implementation Plan: MongoDB 基础设施与通知系统

**Branch**: `006-notification-system` | **Date**: 2025-12-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-notification-system/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本特性旨在为 Ginkgo 量化交易库创建完整的 MongoDB 基础设施层，使其与 ClickHouse 和 MySQL 并列为第一等公民数据库。同时实现基于 MongoDB 的通知系统，支持 Webhook（Discord、钉钉、企业微信等）和 Email 渠道，用户管理使用 MySQL。

**阶段组织策略**:
- 本特性共 262 个任务，分为 61 个 Phase（每个阶段 3-5 个任务）
- Phase 1-12: MongoDB 基础设施（US1）
- Phase 13-23: 用户管理系统（US2）
- Phase 24-29: 通知模板系统
- Phase 30-35: Webhook + Email 渠道（US3, US4）
- Phase 36-42: Kafka 异步处理（US5）
- Phase 43-45: 用户组批量 + 查询（US6, US7）
- Phase 46-61: 优化与文档
- 每个 Phase 完成后立即清理已完成任务，保持活跃任务列表简洁（符合章程第6条"每阶段最多5个活跃任务"）

**核心需求**:
1. **MongoDB 基础设施**: 创建 MMongoBase 模型、GinkgoMongo 驱动和 BaseMongoCRUD，支持 PyMongo 连接池和 Pydantic ODM 模式
2. **用户管理系统**: 支持 MUser/MUserContact/MUserGroup 模型，管理通知接收者及其联系方式（Email/Webhook（Discord/钉钉/企业微信等））
3. **通知发送**: 通过 Webhook（Discord/钉钉/企业微信等）和 Email SMTP 发送通知，支持 Jinja2 模板引擎和变量替换
4. **Kafka 异步处理**: 使用 Kafka 异步队列处理通知发送，单一 topic（ginkgo.alerts），Worker 根据 contact_type 路由，支持自动重试和降级策略
5. **通知记录**: 使用 MongoDB 存储通知记录，支持 7 天 TTL 自动清理

**技术方案**:
- **MongoDB 集成**: 使用 PyMongo 连接池（max=10, min=2），Pydantic 模型 + PyMongo 手动映射，TTL 索引自动清理
- **Kafka 可靠性**: acks=all + 幂等性 + 手动提交 offset，确保消息不丢失
- **降级策略**: Kafka 不可用时自动降级为同步发送（直接调用 WebhookChannel/EmailChannel）
- **模板引擎**: Jinja2 + StrictUndefined，支持变量缺失检测和默认值回退
- **渠道差异化超时**: Webhook（Discord）3s 超时，Email 10s 超时

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存)
**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: single (Python量化交易库)
**Performance Goals**: 高频数据处理 (<100ms延迟), 批量数据操作 (>10K records/sec), 内存优化 (<2GB)
**Constraints**: 必须启用debug模式进行数据库操作, 遵循事件驱动架构, 支持分布式worker
**Scale/Scope**: 支持多策略并行回测, 处理千万级历史数据, 实时风控监控

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查（MongoDB 凭证、SMTP 密码存储在 `~/.ginkgo/secure.yml`，已添加到 .gitignore）
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（Webhook URL（Discord/钉钉/企业微信等）、SMTP 凭证存储在 secure.yml）
- [x] 敏感配置文件已添加到.gitignore（`~/.ginkgo/secure.yml`）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构（通知系统通过 Kafka 事件驱动，异步处理通知发送）
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import services`访问服务组件（NotificationService、UserCRUD、TemplateCRUD 等）
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责（数据层：MongoDB/MySQL 模型，服务层：NotificationService，执行层：Worker）

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器（MongoDB CRUD 操作、Kafka 生产者/消费者、Webhook（Discord/钉钉/企业微信等）/Email 渠道）
- [x] 提供类型注解，支持静态类型检查（所有 Pydantic 模型、CRUD 类、服务类）
- [x] 禁止使用hasattr等反射机制回避类型错误（使用正确的类型检查和 Optional 类型）
- [x] 遵循既定命名约定（MUser/MUserContact/MUserGroup MySQL 模型，MNotificationTemplate/MNotificationRecord MongoDB 模型，CRUD 操作前缀 add_/get_/update_/delete_）

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能（使用 `@pytest.mark.tdd` 标记，先写失败测试再实现）
- [x] 测试按unit、integration、database、network标记分类（MongoDB 测试 @pytest.mark.database，Kafka 测试 @pytest.mark.network，Webhook（Discord/钉钉/企业微信等）/Email 测试 @pytest.mark.network）
- [x] 数据库测试使用测试数据库，避免影响生产数据（使用独立的测试数据库 `ginkgo_test`）

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法（MongoDB 批量插入通知记录，批量查询用户联系方式）
- [x] 合理使用多级缓存（Redis 缓存用户联系方式、模板内容，方法级缓存 @cache_with_expiration）
- [x] 使用懒加载机制优化启动时间（MongoDB 连接懒加载，Kafka 消费者懒加载）

### 任务管理原则 (Task Management Excellence)
- [x] 采用分阶段管理策略，每个阶段最多5个活跃任务（257个任务分为61个阶段，每阶段3-5个任务）
- [x] 已完成任务立即从活跃列表移除（完成一个任务后立即标记完成并移除）
- [x] 任务优先级明确，高优先级任务优先显示（P1 MongoDB 基础设施、P1 用户管理、P2 通知发送）
- [x] 任务状态实时更新，确保团队协作效率（使用 tasks.md 跟踪任务状态）

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文（spec.md、plan.md、research.md、data-model.md、quickstart.md 全部使用中文）
- [x] 核心API提供详细使用示例和参数说明（quickstart.md 包含完整的 CLI 和 Python API 示例）
- [x] 重要组件有清晰的架构说明和设计理念文档（research.md 包含 MongoDB 集成、Kafka 异步处理、Jinja2 模板引擎等技术决策）

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述（MUser/MUserContact/MUserGroup/MNotificationTemplate/MNotificationRecord 等模型）
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述（GinkgoMongo 驱动、NotificationService、WebhookChannel/EmailChannel）
- [x] 代码审查过程中检查头部信息的准确性（CI/CD 流程包含头部检查）
- [x] 定期运行`scripts/verify_headers.py`检查头部一致性（每次提交前运行）
- [x] CI/CD流程包含头部准确性检查（GitHub Actions 集成）
- [x] 使用`scripts/generate_headers.py --force`批量更新头部（重构代码后运行）

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# Ginkgo 量化交易库结构
src/
├── ginkgo/                          # 主要库代码
│   ├── core/                        # 核心组件
│   │   ├── engines/                 # 回测引擎
│   │   ├── events/                  # 事件系统
│   │   ├── portfolios/              # 投资组合管理
│   │   ├── risk/                    # 风险管理
│   │   └── strategies/              # 策略基类
│   ├── data/                        # 数据层
│   │   ├── models/                  # 数据模型 (MBar, MTick, MStockInfo)
│   │   ├── sources/                 # 数据源适配器
│   │   ├── services/                # 数据服务
│   │   └── cruds/                   # CRUD操作
│   ├── trading/                     # 交易执行层
│   │   ├── brokers/                 # 券商接口
│   │   ├── orders/                  # 订单管理
│   │   └── positions/               # 持仓管理
│   ├── analysis/                    # 分析模块
│   │   ├── analyzers/               # 分析器
│   │   └── reports/                 # 报告生成
│   ├── client/                      # CLI客户端
│   │   ├── *_cli.py                 # 各种CLI命令
│   └── libs/                        # 工具库
│       ├── logging/                 # 日志工具
│       ├── decorators/              # 装饰器
│       └── utils/                   # 工具函数

tests/                               # 测试目录
├── unit/                            # 单元测试
├── integration/                     # 集成测试
├── database/                        # 数据库测试
└── network/                         # 网络测试
```

**Structure Decision**: 采用量化交易库的单一项目结构，按功能模块分层组织代码，支持事件驱动架构和依赖注入模式。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
