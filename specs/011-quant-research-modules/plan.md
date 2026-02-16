# Implementation Plan: Ginkgo 量化研究功能模块

**Branch**: `011-quant-research-modules` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-quant-research-modules/spec.md`

## Summary

为 Ginkgo 量化交易库添加 14 个核心功能模块，覆盖 Paper Trading、因子研究、策略验证和因子组合四大领域。新模块复用现有 data 模块 CRUD 层和 ServiceHub 架构，通过 Container 注入服务，独立于现有核心代码开发。

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic, scipy, scikit-learn
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存)
**Testing**: pytest with TDD workflow, @pytest.mark.unit/integration/database/network/financial 标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: single (Python量化交易库)
**Performance Goals**: IC分析 < 10秒 (1000股票×500日), 分层回测 < 30秒, 参数优化 > 1000组合
**Constraints**: 复用 data 模块 CRUD, 遵循 ServiceHub 模式, 新增代码独立目录
**Scale/Scope**: 14个功能模块, ~4600行新增代码, 3个文件小改 (services, cli, pyproject.toml)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [x] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (Paper Trading 复用回测引擎事件流)
- [x] 使用ServiceHub统一访问服务，新模块通过 Container 注册
- [x] 严格分离数据层、研究层、验证层和服务层职责

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查
- [x] 禁止使用hasattr等反射机制回避类型错误
- [x] 遵循既定命名约定 (CRUD前缀、模型继承等)

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [x] 测试按unit、integration、database、network、financial标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 (复用现有 CRUD)
- [x] 合理使用多级缓存 (Redis + Memory + Method级别)
- [x] 使用懒加载机制优化启动时间

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 按优先级 P0→P1→P2→P3 组织任务

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心API提供详细使用示例和参数说明
- [x] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述
- [x] 新文件必须包含三行头部注释

### 验证完整性原则 (Verification Integrity)
- [x] 功能验证包含数据源检查、路径验证和可修改性验证
- [x] 禁止仅因默认值/Mock使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [x] Paper Trading 状态变更如需 Kafka 通知，使用 DTO 包装
- [x] 禁止直接发送字典或裸JSON字符串到Kafka

## Project Structure

### Documentation (this feature)

```text
specs/011-quant-research-modules/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output (Python API contracts)
```

### Source Code (repository root)

```text
src/ginkgo/
├── research/                        # [P1] 因子研究模块 (新增)
│   ├── __init__.py
│   ├── containers.py               # 模块容器
│   ├── ic_analysis.py              # IC 分析
│   ├── layering.py                 # 因子分层
│   ├── factor_comparison.py        # 因子对比
│   ├── orthogonalization.py        # 正交化
│   ├── decay_analysis.py           # 衰减分析
│   └── turnover_analysis.py        # 换手率分析
│
├── validation/                      # [P2] 策略验证模块 (新增)
│   ├── __init__.py
│   ├── containers.py
│   ├── walk_forward.py             # 走步验证
│   ├── monte_carlo.py              # 蒙特卡洛
│   ├── sensitivity.py              # 敏感性分析
│   └── cross_validation.py         # 交叉验证
│
├── trading/
│   ├── paper/                       # [P0] Paper Trading (新增)
│   │   ├── __init__.py
│   │   ├── containers.py
│   │   ├── paper_engine.py         # Paper Trading 引擎
│   │   └── slippage_models.py      # 滑点模型
│   │
│   ├── comparison/                  # [P0] 回测对比 (新增)
│   │   ├── __init__.py
│   │   ├── containers.py
│   │   └── backtest_comparator.py  # 回测对比器
│   │
│   └── optimization/                # [P2] 参数优化 (新增)
│       ├── __init__.py
│       ├── containers.py
│       ├── base_optimizer.py       # 优化器基类
│       ├── grid_search.py          # 网格搜索
│       ├── genetic_optimizer.py    # 遗传算法
│       └── bayesian_optimizer.py   # 贝叶斯优化
│
├── portfolio/                       # [P3] 因子组合 (扩展)
│   └── factor_portfolio.py         # 因子组合管理
│
├── service_hub.py                   # (修改) 注册新容器
└── client/                          # (修改) 添加新CLI命令
    └── research_cli.py              # 因子研究命令

tests/
├── research/                        # 因子研究测试 (新增)
├── validation/                      # 策略验证测试 (新增)
├── trading/
│   ├── paper/                       # Paper Trading 测试 (新增)
│   ├── comparison/                  # 回测对比测试 (新增)
│   └── optimization/                # 参数优化测试 (新增)
└── portfolio/                       # 因子组合测试 (新增)
```

**Structure Decision**: 新模块独立目录，通过 Container 注册到 ServiceHub，复用现有 data 模块 CRUD，最小化对现有代码的修改。

## Complexity Tracking

> No violations - all new code follows existing patterns

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| 独立目录 | research/, validation/, trading/paper/, trading/comparison/, trading/optimization/ | 职责分离，不影响现有代码 |
| Container 注入 | 每个模块独立 Container | 复用 ServiceHub 模式，支持懒加载 |
| 复用 CRUD | 直接使用 data 模块 | 无需新数据源抽象，减少复杂度 |
| TDD 测试 | 新增 tests/ 子目录 | 独立测试，不影响现有测试 |
