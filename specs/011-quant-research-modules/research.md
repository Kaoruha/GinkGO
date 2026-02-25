# Research: Ginkgo 量化研究功能模块

**Date**: 2026-02-16
**Feature**: 011-quant-research-modules

## 1. Paper Trading 数据获取方式

**Decision**: 复用 data 模块 CRUD 层，无需独立数据源抽象

**Rationale**:
- data 模块已提供完整的 CRUD 接口 (bar_crud, tick_crud 等)
- Paper Trading 盘后直接调用 `bar_crud.get_bars(date=today)` 获取当日日K
- 盘中实时数据可未来扩展，当前可跳过或使用分钟线
- 避免引入新的抽象层，保持架构简洁

**Alternatives Considered**:
- 创建独立 PaperDataSource 抽象 → 拒绝：增加复杂度，复用 CRUD 更简洁
- 直接访问数据库 → 拒绝：绕过 CRUD 会丢失装饰器优化和缓存

## 2. Paper Trading 与回测引擎关系

**Decision**: 复用回测引擎的成交逻辑，独立运行管理

**Rationale**:
- 回测引擎已有完整的订单撮合、滑点、手续费计算逻辑
- Paper Trading 需要额外的：按日推进、状态持久化、与回测对比
- 不直接继承回测引擎，而是调用其成交逻辑方法

**Alternatives Considered**:
- 完全继承回测引擎 → 拒绝：Paper Trading 有独特的运行模式
- 完全重写成交流程 → 拒绝：重复代码，维护成本高

## 3. 因子研究模块数据格式

**Decision**: 使用 pandas DataFrame，标准三列格式 (date, code, factor_value)

**Rationale**:
- 与现有 features 模块输出格式一致
- pandas 是量化研究的事实标准
- 便于与 scipy、scikit-learn 集成

**Data Format**:
```python
# 因子数据
factor_df: pd.DataFrame  # columns: [date, code, factor_value]

# 收益数据
return_df: pd.DataFrame  # columns: [date, code, return]
```

## 4. Container 设计模式

**Decision**: 每个新模块独立 Container，注册到 ServiceHub

**Rationale**:
- 符合现有架构模式 (data, trading 已有 Container)
- 支持懒加载，避免循环依赖
- 便于测试时 Mock

**Pattern**:
```python
# ginkgo/research/containers.py
from dependency_injector import containers, providers

class ResearchContainer(containers.DeclarativeContainer):
    ic_analyzer = providers.Singleton(ICAnalyzer)
    layering = providers.Singleton(FactorLayering)
    # ...

research_container = ResearchContainer()

# ginkgo/service_hub.py
class ServiceHub:
    @property
    def research(self):
        if 'research' not in self._module_cache:
            from ginkgo.research.containers import research_container
            self._module_cache['research'] = research_container
        return self._module_cache['research']
```

## 5. TDD 测试策略

**Decision**: 新模块独立测试目录，复用现有测试装饰器和标记

**Rationale**:
- 现有测试框架已成熟 (conftest.py, CRUD_TEST_CONFIG, check_debug_mode)
- 新增 @pytest.mark.financial 用于量化精度测试
- 独立目录避免影响现有测试

**Test Structure**:
```
tests/
├── research/           # IC分析、分层等测试
├── validation/         # 走步验证、蒙特卡洛等测试
├── trading/
│   ├── paper/         # Paper Trading 测试
│   └── comparison/    # 回测对比测试
```

## 6. 参数优化器设计

**Decision**: 策略模式，基类定义接口，多种优化器实现

**Rationale**:
- 不同优化算法有不同适用场景
- 网格搜索适合小参数空间，遗传算法适合大参数空间
- 统一接口便于切换和对比

**Interface**:
```python
class BaseOptimizer(ABC):
    @abstractmethod
    def optimize(self, strategy_class, param_ranges, data) -> OptimizationResult:
        pass

class GridSearchOptimizer(BaseOptimizer): ...
class GeneticOptimizer(BaseOptimizer): ...
class BayesianOptimizer(BaseOptimizer): ...
```

## 7. 滑点模型设计

**Decision**: 策略模式，复用回测引擎滑点逻辑

**Rationale**:
- 回测引擎已有成熟实现
- Paper Trading 复用相同逻辑确保对比公平
- 支持多种滑点模式 (固定、百分比、无)

**Models**:
- FixedSlippage: 固定滑点 (如 0.01 元)
- PercentageSlippage: 百分比滑点 (如 0.1%)
- NoSlippage: 无滑点 (用于测试)

## 8. CLI 命令组织

**Decision**: 新增命令组，遵循现有 CLI 模式

**Rationale**:
- 现有 CLI 使用 Typer，组织良好
- 新命令组保持一致性

**Commands**:
```bash
ginkgo paper start <portfolio_id>     # Paper Trading
ginkgo paper status <portfolio_id>
ginkgo research ic <factor>           # IC 分析
ginkgo research layering <factor>     # 分层回测
ginkgo validate walk-forward          # 走步验证
ginkgo compare <backtest_ids>         # 回测对比
```

## 9. 依赖管理

**Decision**: 新增依赖标记为可选，避免强制安装

**Rationale**:
- optuna (贝叶斯优化) 和 deap (遗传算法) 不是所有用户都需要
- 核心功能只需 scipy、scikit-learn
- pyproject.toml 中使用 extras 配置

**Dependencies**:
```toml
[project.optional-dependencies]
optimization = ["optuna>=3.3.0", "deap>=1.4.0"]
```

## 10. 状态持久化

**Decision**: Paper Trading 状态存储在数据库 (MySQL/MongoDB)

**Rationale**:
- Portfolio 状态需要持久化，支持重启恢复
- MySQL 适合结构化数据，MongoDB 适合复杂文档
- 复用现有数据库连接

**State Structure**:
```python
# Paper Trading 状态
{
    "portfolio_id": str,
    "status": "running" | "paused" | "stopped",
    "current_date": date,
    "positions": Dict[str, Position],
    "daily_signals": List[Signal],
    "performance": {...}
}
```

## Summary

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 数据获取 | 复用 CRUD | 简洁，避免新抽象 |
| 成交逻辑 | 复用回测引擎 | 保持对比公平 |
| 数据格式 | pandas DataFrame | 量化标准 |
| Container | 每模块独立 | 支持懒加载 |
| 测试策略 | 独立目录 + 复用框架 | 不影响现有 |
| 优化器 | 策略模式 | 便于扩展 |
| 滑点模型 | 复用 + 策略模式 | 一致性 |
| CLI | 新命令组 | 保持一致 |
| 依赖 | 可选安装 | 降低门槛 |
| 持久化 | 数据库 | 支持恢复 |
