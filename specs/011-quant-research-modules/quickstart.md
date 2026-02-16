# Quickstart: Ginkgo 量化研究功能模块

**Date**: 2026-02-16
**Feature**: 011-quant-research-modules

## 安装

```bash
# 核心功能
pip install ginkgo

# 可选：参数优化高级功能
pip install ginkgo[optimization]
```

## 策略生命周期完整流程

```python
from ginkgo import services

# 1. 回测阶段（使用现有回测引擎）
engine = services.trading.engines.historic()
portfolio = services.trading.portfolios.base()
portfolio.add_strategy(my_strategy)
result = engine.run()

# 2. 样本外验证（使用历史预留数据）
# ... 省略 ...

# 3. Paper Trading（使用实盘数据）
# 4. 实盘交易
```

---

## P0 - Paper Trading

### 启动 Paper Trading

```python
from ginkgo import services

# 加载已回测的 Portfolio
portfolio = services.trading.portfolios.load("my_portfolio_001")

# 启动 Paper Trading
paper = services.trading.paper.engine()
paper.start(portfolio)

# 查看状态
status = paper.get_status()
print(f"状态: {status.status}")
print(f"当前资金: {status.current_capital}")
print(f"累计收益: {status.total_return}")
```

### CLI 方式

```bash
# 启动 Paper Trading
ginkgo paper start my_portfolio_001

# 查看状态
ginkgo paper status my_portfolio_001

# 查看与回测对比
ginkgo paper compare my_portfolio_001 --backtest bt_001

# 停止
ginkgo paper stop my_portfolio_001
```

### 对比分析

```python
from ginkgo import services

# 获取对比结果
result = services.trading.paper.compare(
    paper_id="paper_001",
    backtest_id="bt_001"
)

print(f"回测收益: {result.backtest_return:.2%}")
print(f"模拟收益: {result.total_return:.2%}")
print(f"差异: {result.difference_pct:.2%}")
print(f"是否可接受: {result.is_acceptable}")
```

---

## P0 - 回测对比

```python
from ginkgo import services

# 对比多个回测
comparator = services.trading.comparison.backtest()
result = comparator.compare(["bt_001", "bt_002", "bt_003"])

# 查看对比表格
print(result.metrics_table)
# {
#   "total_return": {"bt_001": 0.25, "bt_002": 0.18, "bt_003": 0.22},
#   "sharpe_ratio": {"bt_001": 1.5, "bt_002": 1.2, "bt_003": 1.8},
#   ...
# }

# 查看最佳表现
print(result.best_performers)
# {"total_return": "bt_001", "sharpe_ratio": "bt_003", ...}

# 获取净值曲线数据
net_values = result.net_values
```

### CLI 方式

```bash
ginkgo compare bt_001 bt_002 bt_003 --output comparison_report.html
```

---

## P1 - IC 分析

```python
from ginkgo import services

# 准备数据
factor_df = ...  # columns: [date, code, factor_value]
return_df = ...  # columns: [date, code, return]

# IC 分析
analyzer = services.research.ic_analyzer()
result = analyzer.analyze(
    factor_data=factor_df,
    return_data=return_df,
    periods=[1, 5, 10, 20]
)

# 查看统计指标
print(result.statistics[5])
# ICStatistics(
#   mean=0.05, std=0.15, icir=0.33,
#   t_stat=2.1, p_value=0.03, pos_ratio=0.55
# )
```

### CLI 方式

```bash
ginkgo research ic --factor MOM_20 --start 20230101 --end 20231231
```

---

## P1 - 因子分层

```python
from ginkgo import services

# 因子分层
layering = services.research.layering()
result = layering.run(
    factor_data=factor_df,
    return_data=return_df,
    n_groups=5
)

# 查看各组收益
for group, returns in result.group_returns.items():
    print(f"{group}: 累计收益 {returns.sum():.2%}")

# 查看多空收益
print(f"多空收益: {result.long_short_return.sum():.2%}")
print(f"单调性 R²: {result.statistics.monotonicity_r2:.3f}")
```

---

## P2 - 参数优化

```python
from ginkgo import services

# 定义参数范围
param_ranges = {
    "fast_period": (5, 20, 1),      # min, max, step
    "slow_period": (20, 60, 5),
}

# 网格搜索
optimizer = services.trading.optimization.grid_search()
result = optimizer.optimize(
    strategy_class=MyStrategy,
    param_ranges=param_ranges,
    data=bar_data,
    target="sharpe_ratio"
)

# 查看最优参数
print(f"最优参数: {result.best_params}")
print(f"最优夏普: {result.best_score:.3f}")

# 查看所有结果
for point in result.results[:10]:
    print(f"{point.params}: 夏普={point.score:.3f}")
```

### CLI 方式

```bash
# 网格搜索
ginkgo optimize grid --strategy MyStrategy --params fast:5:20 slow:20:60

# 遗传算法
ginkgo optimize genetic --strategy MyStrategy --population 50 --generations 20
```

---

## P2 - 走步验证

```python
from ginkgo import services

# 走步验证
validator = services.validation.walk_forward()
result = validator.validate(
    strategy_class=MyStrategy,
    parameters={"fast_period": 10, "slow_period": 30},
    data=bar_data,
    train_size=252,
    test_size=63,
    step_size=21
)

# 查看结果
print(f"平均训练收益: {result.avg_train_return:.2%}")
print(f"平均测试收益: {result.avg_test_return:.2%}")
print(f"退化程度: {result.degradation:.2%}")
print(f"稳定性得分: {result.stability_score:.3f}")

if result.degradation > 0.5:
    print("警告: 可能存在过拟合!")
```

---

## P2 - 蒙特卡洛模拟

```python
from ginkgo import services

# 蒙特卡洛模拟
simulator = services.validation.monte_carlo()
result = simulator.run(
    returns=historical_returns,
    n_simulations=10000,
    confidence_level=0.95
)

# 查看结果
print(f"均值: {result.mean:.4f}")
print(f"标准差: {result.std:.4f}")
print(f"95% VaR: {result.var:.4f}")
print(f"95% CVaR: {result.cvar:.4f}")
```

---

## 服务访问汇总

```python
from ginkgo import services

# P0 核心功能
services.trading.paper.engine()           # Paper Trading 引擎
services.trading.comparison.backtest()    # 回测对比器

# P1 因子研究
services.research.ic_analyzer()           # IC 分析
services.research.layering()              # 因子分层
services.research.factor_comparator()     # 因子对比
services.research.orthogonalizer()        # 正交化
services.research.decay_analyzer()        # 衰减分析
services.research.turnover_analyzer()     # 换手率分析

# P2 策略验证
services.trading.optimization.grid_search()      # 网格搜索
services.trading.optimization.genetic()          # 遗传算法
services.trading.optimization.bayesian()         # 贝叶斯优化
services.validation.walk_forward()               # 走步验证
services.validation.monte_carlo()                # 蒙特卡洛
services.validation.sensitivity()                # 敏感性分析
services.validation.cross_validation()           # 交叉验证

# P3 高级功能
services.portfolio.factor_builder()       # 因子组合
```

---

## CLI 命令汇总

```bash
# Paper Trading
ginkgo paper start <portfolio_id>
ginkgo paper status <portfolio_id>
ginkgo paper compare <portfolio_id> --backtest <id>
ginkgo paper stop <portfolio_id>

# 回测对比
ginkgo compare <backtest_ids...>

# 因子研究
ginkgo research ic --factor <name> --start <date> --end <date>
ginkgo research layering --factor <name> --groups 5
ginkgo research compare --factors <names...>
ginkgo research orthogonalize --factors <names...> --method pca

# 策略验证
ginkgo optimize grid --strategy <name> --params <ranges>
ginkgo optimize genetic --strategy <name> --population 50
ginkgo validate walk-forward --strategy <name>
ginkgo validate monte-carlo --returns <file>
```
