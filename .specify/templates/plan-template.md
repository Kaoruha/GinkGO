# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

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
- [ ] 所有代码提交前已进行敏感文件检查
- [ ] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [ ] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [ ] 设计遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- [ ] 使用ServiceHub统一访问服务，通过`from ginkgo import service_hub`访问服务组件
- [ ] 严格分离数据层、策略层、执行层、分析层和服务层职责

### 代码质量原则 (Code Quality)
- [ ] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [ ] 提供类型注解，支持静态类型检查
- [ ] 禁止使用hasattr等反射机制回避类型错误
- [ ] 遵循既定命名约定 (CRUD前缀、模型继承等)

### 测试原则 (Testing Excellence)
- [ ] 遵循TDD流程，先写测试再实现功能
- [ ] 测试按unit、integration、database、network标记分类
- [ ] 数据库测试使用测试数据库，避免影响生产数据

### 性能原则 (Performance Excellence)
- [ ] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [ ] 合理使用多级缓存 (Redis + Memory + Method级别)
- [ ] 使用懒加载机制优化启动时间

### 任务管理原则 (Task Management Excellence)
- [ ] 任务列表限制在最多5个活跃任务
- [ ] 已完成任务立即从活跃列表移除
- [ ] 任务优先级明确，高优先级任务优先显示
- [ ] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [ ] 文档和注释使用中文
- [ ] 核心API提供详细使用示例和参数说明
- [ ] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [ ] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [ ] 修改模块依赖关系时，更新Upstream/Downstream描述
- [ ] 代码审查过程中检查头部信息的准确性
- [ ] 定期运行`scripts/verify_headers.py`检查头部一致性
- [ ] CI/CD流程包含头部准确性检查
- [ ] 使用`scripts/generate_headers.py --force`批量更新头部

### 验证完整性原则 (Verification Integrity)
- [ ] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [ ] 验证配置文件包含对应配置项（如 grep config.yml notifications.timeout）
- [ ] 验证值从配置文件读取，而非代码默认值（打印原始配置内容）
- [ ] 验证用户可通过修改配置文件改变行为（修改配置后重新运行）
- [ ] 验证缺失配置时降级到默认值（删除配置项后验证）
- [ ] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [ ] 禁止仅因默认值/Mock使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [ ] 所有Kafka消息发送使用DTO包装（ControlCommandDTO等）
- [ ] 发送端使用DTO.model_dump_json()序列化
- [ ] 接收端使用DTO(**data)反序列化
- [ ] 使用DTO.Commands常量类定义命令/事件类型
- [ ] 使用DTO.is_xxx()方法进行类型判断
- [ ] 禁止直接发送字典或裸JSON字符串到Kafka
- [ ] DTO使用Pydantic BaseModel实现类型验证

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
