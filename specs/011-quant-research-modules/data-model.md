# Data Model: Ginkgo 量化研究功能模块

**Date**: 2026-02-17
**Feature**: 011-quant-research-modules

## 实体概览

| 实体 | 模块 | 存储位置 | 描述 |
|------|------|----------|------|
| MBacktestTask | P0 | MySQL | 回测任务（原 MRunRecord） |
| MEngine | P0 | MySQL | 引擎配置模板 |
| PaperTradingState | P0 | MySQL | Paper Trading 运行状态 |
| PaperTradingSignal | P0 | MySQL | Paper Trading 信号记录 |
| ICAnalysisResult | P1 | Memory/Redis | IC 分析结果 |
| LayeringResult | P1 | Memory | 分层回测结果 |
| OptimizationResult | P2 | Memory | 参数优化结果 |
| WalkForwardResult | P2 | Memory | 走步验证结果 |
| MonteCarloResult | P2 | Memory | 蒙特卡洛结果 |
| ComparisonResult | P0 | Memory | 回测对比结果 |

---

## P0 - 回测任务实体

### MBacktestTask

> **Note**: 原名 `MRunRecord`，重命名为 `MBacktestTask` 以更清晰表达业务语义。
> 详见 [backtest-task-model.md](./backtest-task-model.md)

```python
@dataclass
class MBacktestTask:
    """回测任务：记录每次回测执行的完整信息"""

    # 标识
    uuid: str                              # 任务唯一标识
    task_id: str                           # 任务会话ID（唯一）
    engine_id: str                         # 所属引擎ID
    portfolio_id: str                      # 关联投资组合ID

    # 执行信息
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    status: Literal["running", "completed", "failed", "stopped"]
    error_message: Optional[str]

    # 业务统计
    total_orders: int
    total_signals: int
    total_positions: int
    total_events: int

    # 性能指标
    final_portfolio_value: str
    total_pnl: str
    max_drawdown: str
    avg_event_processing_ms: str

    # 配置快照
    config_snapshot: str                   # JSON
    environment_info: str                  # JSON
```

**存储**: MySQL `backtest_task` 表（原 `run_record`）

### MEngine

```python
@dataclass
class MEngine:
    """引擎配置：可复用的回测配置模板"""

    uuid: str
    name: str
    config_hash: str                       # 配置哈希
    config_snapshot: str                   # 配置快照JSON
    current_run_id: str                    # 当前运行的任务ID
    run_count: int                         # 累计执行次数
    backtest_start_date: Optional[datetime]
    backtest_end_date: Optional[datetime]
    is_live: bool
    status: ENGINESTATUS_TYPES
```

**关系**:
- `MEngine` 1:N `MBacktestTask`
- 一个引擎配置可以执行多次回测，产生多个任务记录

---

## P0 - Paper Trading 实体

### PaperTradingState

```python
@dataclass
class PaperTradingState:
    """Paper Trading 运行状态"""

    # 标识
    portfolio_id: str                    # 关联的 Portfolio ID
    paper_id: str                        # Paper Trading 实例 ID

    # 状态
    status: Literal["running", "paused", "stopped"]
    started_at: datetime
    current_date: Optional[date]         # 当前回放日期

    # 配置
    initial_capital: Decimal
    slippage_model: str                  # "fixed" | "percentage" | "none"
    slippage_value: Decimal
    commission_rate: Decimal
    commission_min: Decimal

    # 表现
    current_capital: Decimal
    total_return: Decimal
    daily_returns: List[Decimal]

    # 时间戳
    created_at: datetime
    updated_at: datetime
```

**存储**: MySQL `paper_trading_states` 表

### PaperTradingSignal

```python
@dataclass
class PaperTradingSignal:
    """Paper Trading 信号记录"""

    signal_id: str
    paper_id: str                        # 关联 PaperTradingState
    date: date

    # 信号内容
    code: str                            # 股票代码
    direction: DIRECTION_TYPES           # LONG/SHORT
    reason: str                          # 信号原因

    # 成交信息
    order_price: Optional[Decimal]
    executed_price: Optional[Decimal]
    volume: Optional[int]
    slippage: Optional[Decimal]
    commission: Optional[Decimal]

    status: Literal["pending", "executed", "failed"]
    created_at: datetime
```

**存储**: MySQL `paper_trading_signals` 表

### PaperTradingResult

```python
@dataclass
class PaperTradingResult:
    """Paper Trading 结果（用于对比）"""

    paper_id: str
    portfolio_id: str

    # 表现指标
    total_return: Decimal
    annual_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal

    # 与回测对比
    backtest_return: Decimal
    difference: Decimal                  # paper - backtest
    difference_pct: Decimal              # 差异百分比
    is_acceptable: bool                  # 差异 < 10%

    # 运行信息
    trading_days: int
    total_signals: int
    executed_signals: int
```

**存储**: 内存计算，可选持久化

---

## P0 - 回测对比实体

### ComparisonResult

```python
@dataclass
class ComparisonResult:
    """回测对比结果"""

    comparison_id: str
    backtest_ids: List[str]

    # 对比表格
    metrics_table: Dict[str, Dict[str, float]]
    # {metric: {backtest_id: value}}
    # 例: {"sharpe_ratio": {"bt_001": 1.5, "bt_002": 1.2}}

    # 最佳表现
    best_performers: Dict[str, str]
    # {metric: best_backtest_id}

    # 净值曲线数据
    net_values: Dict[str, List[Tuple[date, float]]]
    # {backtest_id: [(date, net_value), ...]}

    created_at: datetime
```

**存储**: 内存计算

---

## P1 - 因子研究实体

### ICAnalysisResult

```python
@dataclass
class ICAnalysisResult:
    """IC 分析结果"""

    factor_name: str
    periods: List[int]                   # [1, 5, 10, 20]
    date_range: Tuple[date, date]

    # IC 时序
    ic_series: Dict[int, pd.Series]
    # {period: Series of IC values}

    rank_ic_series: Dict[int, pd.Series]

    # 统计指标
    statistics: Dict[int, ICStatistics]
    # {period: ICStatistics}

@dataclass
class ICStatistics:
    """IC 统计指标"""
    mean: float
    std: float
    icir: float                          # mean / std
    t_stat: float
    p_value: float
    pos_ratio: float                     # 正 IC 占比
    abs_mean: float
```

**存储**: 内存计算，可选导出

### LayeringResult

```python
@dataclass
class LayeringResult:
    """分层回测结果"""

    factor_name: str
    n_groups: int
    date_range: Tuple[date, date]

    # 各组收益
    group_returns: Dict[str, pd.Series]
    # {group_name: returns}

    # 多空收益
    long_short_return: pd.Series         # 最高组 - 最低组

    # 统计指标
    statistics: LayeringStatistics

@dataclass
class LayeringStatistics:
    """分层统计指标"""
    long_short_total_return: float
    long_short_sharpe: float
    max_drawdown: float
    monotonicity_r2: float               # 单调性得分 (0-1)
    turnover: float
```

---

## P2 - 策略验证实体

### OptimizationResult

```python
@dataclass
class OptimizationResult:
    """参数优化结果"""

    strategy_name: str
    optimizer_type: str                  # "grid" | "genetic" | "bayesian"

    # 参数空间
    param_ranges: Dict[str, ParameterRange]

    # 结果列表
    results: List[OptimizationPoint]
    # 按目标指标排序

    # 最优参数
    best_params: Dict[str, Any]
    best_score: float

    # 优化信息
    total_combinations: int
    evaluated_combinations: int
    elapsed_time: float

@dataclass
class OptimizationPoint:
    """单个参数组合结果"""
    params: Dict[str, Any]
    score: float
    metrics: Dict[str, float]            # 收益率、夏普等

@dataclass
class ParameterRange:
    """参数范围"""
    name: str
    min: Union[int, float]
    max: Union[int, float]
    step: Optional[Union[int, float]]
    values: Optional[List[Any]]          # 离散值
```

### WalkForwardResult

```python
@dataclass
class WalkForwardResult:
    """走步验证结果"""

    strategy_name: str
    train_size: int
    test_size: int
    step_size: int

    # 各 fold 结果
    folds: List[WalkForwardFold]

    # 汇总
    avg_train_return: float
    avg_test_return: float
    degradation: float                   # (train - test) / train
    stability_score: float

@dataclass
class WalkForwardFold:
    """单个 fold 结果"""
    fold_num: int
    train_period: Tuple[date, date]
    test_period: Tuple[date, date]
    train_return: float
    test_return: float
    parameters: Dict[str, Any]
```

### MonteCarloResult

```python
@dataclass
class MonteCarloResult:
    """蒙特卡洛模拟结果"""

    n_simulations: int
    confidence_level: float

    # 模拟路径 (可选存储)
    paths: Optional[np.ndarray]          # (n_simulations, n_periods)

    # 统计指标
    mean: float
    std: float
    percentiles: Dict[str, float]        # {"p5": ..., "p95": ...}

    # 风险指标
    var: float                           # Value at Risk
    cvar: float                          # Conditional VaR
```

---

## 数据流转

```
┌─────────────────────────────────────────────────────────────┐
│                        数据流转                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  data 模块 CRUD                                              │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │因子研究 │───▶│策略验证 │───▶│ Paper   │                 │
│  │(P1)     │    │(P2)     │    │ Trading │                 │
│  └─────────┘    └─────────┘    └─────────┘                 │
│       │              │              │                       │
│       ▼              ▼              ▼                       │
│  ICAnalysisResult  OptimizationResult  PaperTradingResult  │
│  LayeringResult    WalkForwardResult   ComparisonResult    │
│                    MonteCarloResult                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 验证规则

| 实体 | 验证规则 |
|------|----------|
| PaperTradingState | portfolio_id 必须存在，initial_capital > 0 |
| ICAnalysisResult | periods 必须为正整数，date_range 有效 |
| LayeringResult | n_groups >= 2，group_returns 长度 = n_groups |
| OptimizationResult | param_ranges 非空，best_params 在范围内 |
| WalkForwardResult | train_size > 0, test_size > 0 |
| MonteCarloResult | n_simulations > 0, 0 < confidence_level < 1 |
