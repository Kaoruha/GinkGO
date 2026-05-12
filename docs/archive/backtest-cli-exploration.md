# CLI 回测流程探索记录

> 日期: 2026-05-06
> 目标: 通过 ginkgo CLI 构建稳定盈利策略，不修改源码

## 回测流程

### 可用路径: `backtest create + run`

```
1. ginkgo portfolio create  (❌ 有 bug，见下方)
2. ginkgo portfolio bind-component <portfolio> <strategy_id> -t strategy
3. ginkgo portfolio bind-component <portfolio> <risk_id> -t risk
4. ginkgo backtest create -p <portfolio> --start ... --end ...
5. ginkgo backtest run <task_id>
```

### 不可用路径: `engine create + bind-portfolio + run`

engine list 和 engine bind-portfolio 均有 bug。

## 已发现的问题

### 问题 1: `ginkgo engine list` - 崩溃
- **错误**: `name 'result' is not defined`
- **严重度**: 高 (完全不可用)
- **影响**: 无法通过 CLI 查看引擎列表

### 问题 2: `ginkgo result list --help` - 参数冲突
- **错误**: `-p` 同时用于 `--portfolio` 和 `--page`
- **严重度**: 中 (功能冲突)
- **影响**: 无法同时按 portfolio 筛选并指定分页

### 问题 3: `ginkgo portfolio create` - 方法名不匹配
- **错误**: `'PortfolioService' object has no attribute 'create'`
- **原因**: CLI 调用 `portfolio_service.create()`，但 PortfolioService 的方法名是 `add()`
- **严重度**: 高 (无法通过 CLI 创建 portfolio)
- **影响**: 必须使用已有 portfolio 或通过 API 创建

### 问题 4: `ginkgo data get day` - 未实现
- **错误**: `Bar data get not yet implemented`
- **严重度**: 中 (无法查看 K 线数据)
- **影响**: 无法确认数据可用性

### 问题 5: `ginkgo data status` - 未实现
- **错误**: `Data status check not yet implemented`
- **严重度**: 低
- **影响**: 无法查看数据同步状态

### 问题 6: `ginkgo backtest list` - progress 异常
- **现象**: progress 显示 980%/990% (超过 100%)
- **严重度**: 中 (显示错误)
- **影响**: 无法通过 progress 判断回测是否正常完成

### 问题 7: `ginkgo engine bind-portfolio` - 崩溃
- **错误**: `name 'Table' is not defined`
- **原因**: 缺少 `from rich.table import Table` 导入
- **严重度**: 高 (无法绑定 portfolio 到 engine)

### 问题 8: 信号→订单转化失败 (核心问题)
- **现象**: 回测产生 ~260 个信号，但订单数为 0，净值不变
- **严重度**: 关键 (回测产出无意义)
- **可能原因**:
  - portfolio 没有 stocklist/interested_codes，策略不知道交易哪些股票
  - sizer 组件配置问题
  - portfolio 状态不正确
- **详情**: 见下方尝试记录

## 回测尝试记录

### 尝试 1: MA Crossover (2024-01-01 ~ 2025-01-01)
- **Portfolio**: test (422d189ae2b44fff82ef93d7540df000)
- **策略**: moving_average_crossover + random_signal_strategy
- **风控**: loss_limit_risk + position_ratio_risk + no_risk
- **资金**: 100,000
- **结果**: 信号 260+，订单 0，年化收益 0%
- **问题**: 信号产生了但未转化为订单
- **分析**: portfolio 可能缺少 stocklist/interested_codes 配置

## 不便之处

1. **UUID 截断**: `backtest list` 和 `portfolio list` 表格中 UUID 被截断，复制后无法直接使用
2. **无 `--raw` 输出**: `backtest list` 不支持 `--raw` 参数获取完整 UUID
3. **交互式分页**: `data get stockinfo` 默认进入交互式分页模式，在脚本中使用不便
4. **result show 每次显示 50 条**: 无法一眼看全貌，需要 `--limit` 参数但默认只展示尾部
5. **无汇总摘要**: 回测完成后没有打印关键指标汇总（如年化收益、最大回撤、夏普比），需要逐个 analyzer 查询
6. **组件冗余**: database 中有大量 `strategy_config.ini`、`my_custom_strategy` 等测试/模板组件，有效组件难以筛选
7. **backtest create 默认绑定所有组件**: 创建回测时自动加载了 `random_signal_strategy` 和 `no_risk`，无法在 CLI 指定只用特定组件
