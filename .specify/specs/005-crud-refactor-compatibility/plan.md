# Implementation Plan: Data Services & CLI Compatibility Fix

**Branch**: `fix/005-crud-refactor-compatibility` | **Date**: 2025-11-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-crud-refactor-compatibility/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本修复项目专注于先优化BarService本身，使其成为完美的参考标准，然后再基于优化后的BarService来统一其他data service。

**Phase 1**: BarService标准化 (已完成)
1. ✅ **统一命名规则**: 按面向对象原则重命名方法，避免服务名+对象名重复
2. ✅ **标准方法实现**: 实现sync_range/sync_batch/sync_smart, get/count/validate/check_integrity
3. ✅ **ServiceResult统一**: 所有方法返回ServiceResult格式
4. ✅ **依赖注入优化**: 修复构造函数中的硬编码依赖
5. ✅ **数据同步幂等性**: 智能增量同步，避免重复数据
6. ✅ **错误处理和日志**: 统一错误分类和@time_logger/@retry装饰器优化

**Phase 2**: 基于BarService统一其他data service (进行中)
1. 🔄 **TickService重构**: 按照统一命名规则和ServiceResult格式重构
   - sync_date (单日同步)
   - sync_range (日期范围同步)
   - sync_smart (智能同步)
   - sync_batch (批量同步)
2. ⏳ **StockinfoService重构**: 统一命名和ServiceResult
3. ⏳ **AdjustfactorService重构**: 统一命名和ServiceResult

**第二阶段**: 基于优化后的BarService统一其他data service (TickService、StockinfoService、AdjustfactorService等)

**第三阶段**: 修复CLI命令兼容性，支持新的ServiceResult格式

## Technical Context

**优化目标**: BarService作为所有data service的参考标准

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse (存储), Typer (CLI), Rich (进度条), pandas (数据处理), Pydantic (数据验证)
**Storage**: ClickHouse作为主要数据存储，支持时序数据高效查询
**Testing**: pytest with TDD workflow，真实环境测试（无Mock），按unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: Service Layer Optimization (服务层优化)
**Performance Goals**:
- 数据同步延迟 <5秒 (小批量<1000条记录)
- 批量数据处理 >1,000 records/sec
- 内存使用优化 <2GB
- CLI启动时间 <2秒

**约束条件**:
- 必须启用debug模式进行数据库操作
- 遵循TDD流程，每个测试用例需用户确认
- 禁止使用Mock数据，使用真实环境测试
- 必须使用ServiceResult统一返回格式
- 必须使用@time_logger、@retry装饰器优化

**技术挑战**:
- **依赖注入重构**: 修复构造函数中的硬编码AdjustfactorService创建
- **幂等性实现**: 智能增量同步，避免重复数据
- **方法重命名**: 保持向后兼容性的同时统一命名规范
- **性能优化**: 批量操作和缓存策略

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
- [ ] 每个测试用例设计完成后等待用户确认
- [ ] 测试按unit、integration、database、network、financial标记分类
- [ ] 数据库测试使用测试数据库，避免影响生产数据
- [ ] 禁止使用Mock数据，所有测试必须使用真实数据源和环境
- [ ] 每次测试用例讨论控制在20行以内

### 性能原则 (Performance Excellence)
- [ ] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [ ] 合理使用多级缓存 (Redis + Memory + Method级别)
- [ ] 使用懒加载机制优化启动时间

### 文档原则 (Documentation Excellence)
- [ ] 文档和注释使用中文
- [ ] 核心API提供详细使用示例和参数说明
- [ ] 重要组件有清晰的架构说明和设计理念文档

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
| 向后兼容性破坏 | 统一方法命名和接口规范 | 保持旧方法会增加代码复杂性和维护成本，不利于长期架构统一 |
| 构造函数依赖注入重构 | 符合依赖注入原则，便于测试 | 硬编码依赖违反了SOLID原则和可测试性要求 |

## Constitution Check - Post Design

*GATE: Design must comply with all constitution principles*

### 安全与合规原则 (Security & Compliance)
- [x] 敏感文件检查 - 代码重构不涉及敏感信息
- [x] 配置管理 - 使用现有环境变量和配置文件

### 架构设计原则 (Architecture Excellence)
- [x] 事件驱动架构 - BarService作为数据层服务，符合架构
- [x] ServiceHub统一访问 - 通过service_hub.data.services.bar_service()访问
- [x] 职责分离 - 数据同步、验证、完整性检查职责明确

### 代码质量原则 (Code Quality)
- [x] 装饰器优化 - 所有方法使用@time_logger、@retry
- [x] 类型注解 - 完整的类型注解支持
- [x] 禁止hasattr - 新代码避免使用反射机制
- [x] 命名约定 - 按CRUD标准模式命名

### 测试原则 (Testing Excellence)
- [x] TDD流程 - 遵循先测试后实现
- [x] 测试分类 - 按unit/integration/database/network/financial标记
- [x] 真实环境测试 - 禁止Mock数据
- [x] 用户确认机制 - 每个测试用例需用户确认

### 性能原则 (Performance Excellence)
- [x] 批量操作 - 使用add_batch而非单条插入
- [x] 多级缓存 - 实现智能缓存策略
- [x] 懒加载 - 优化启动性能

### 文档原则 (Documentation Excellence)
- [x] 中文文档 - 所有文档使用中文
- [x] API文档 - 详细的data-model.md和quickstart.md
- [x] 架构文档 - 完整的研究和设计文档

**GATE STATUS**: ✅ PASSED - Design fully complies with constitution principles

## 项目结构

### 文档结构（已生成）

```text
specs/005-crud-refactor-compatibility/
├── plan.md                    # 实施计划（本文件）
├── spec.md                    # 功能规范
├── research.md                # Phase 0: 研究结果
├── data-model.md              # Phase 1: 数据模型设计
├── quickstart.md              # Phase 1: 快速开始指南
└── contracts/                 # Phase 1: API契约
    └── bar_service_api.md       # BarService API契约
```

### 源代码结构（需要重构）

```text
src/ginkgo/data/services/
├── bar_service.py             # 需要重构的主要文件
├── base_service.py           # 基类（已存在）
├── stockinfo_service.py       # 第二阶段重构目标
├── tick_service.py           # 第二阶段重构目标
├── adjustfactor_service.py    # 第二阶段重构目标
└── ...                       # 其他服务

# 新增通用Result类（第一阶段实施）
src/ginkgo/data/models/results/
├── __init__.py
├── data_validation_result.py
├── data_integrity_result.py
├── data_sync_result.py
└── base_result.py
```

## 实施阶段总结

### Phase 0 - 研究阶段 ✅
- [x] 完成依赖注入重构最佳实践研究
- [x] 完成方法命名标准化策略研究
- [x] 完成数据同步幂等性实现研究
- [x] 完成数据完整性检查机制研究

### Phase 1 - 设计阶段 ✅
- [x] 完成通用数据模型设计（data-model.md）
- [x] 完成API契约定义（contracts/）
- [x] 完成快速开始指南（quickstart.md）
- [x] 验证设计符合章程要求

### Phase 2 - 准备就绪
- [x] 架构设计完成
- [x] 数据模型标准化
- [x] 方法命名规范制定
- [x] 错误处理框架设计
- [ ] 待实施：BarService重构
- [ ] 待实施：通用Result类实现
- [ ] 待实施：TDD测试用例编写
- [ ] 待实施：CLI命令更新

## 下一步

1. **生成任务列表**: 运行 `/speckit.tasks` 创建详细的实施任务
2. **开始实施**: 按照TDD流程，先写测试，再实现BarService重构
3. **统一其他service**: 基于优化后的BarService统一TickService、StockinfoService等
4. **更新CLI**: 修复CLI命令以支持新的ServiceResult格式
