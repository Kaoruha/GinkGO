# 回测分析模块设计

## 背景

当前 Ginkgo 只有逐步记录的实时分析器和回测结束后的简单汇总（BacktestResultAggregator），缺少一个统一的、可扩展的事后分析模块。用户需要：单次回测综合报告、多策略对比、时间分段归因、滚动窗口分析、信号级/订单级深度分析，并支持 API/Python/CLI 三端消费。

## 核心设计

### 1. ID 体系

- `task_id` — 回测配置（策略+参数+时间范围），BacktestTask 的 UUID
- `run_id` — 一次具体执行，由 task_id + 执行时间戳生成
- 一个 task 可以有多个 run，分析以 run_id 为主键
- 当前 1:1 向后兼容（run_id = task_id）

### 2. 数据源

分析模块读取 ClickHouse 中四个已有数据源，不新增表：

| 数据源 | 表 | 关键字段 |
|--------|-----|---------|
| 分析器时间序列 | `analyzer_record` | run_id, name, value, timestamp |
| 信号明细 | `signal` | run_id, code, direction, timestamp |
| 订单明细 | `order_record` | run_id, code, direction, volume, limit_price, transaction_price, status, timestamp |
| 持仓变化 | `position_record` | run_id, code, cost, volume, price, timestamp |

### 3. 指标函数（Metric）— 纯函数层

所有指标计算是接收时间序列的纯函数，可独立测试和组合：

```python
class Metric(Protocol):
    name: str
    requires: List[str]           # 需要哪些数据源标识
    params: Dict[str, Any]        # 参数（窗口大小、置信度等）
    def compute(self, data: Dict[str, pd.DataFrame]) -> Any: ...
```

- `requires` 用数据源名称标识：`"net_value"`, `"signal"`, `"order"`, `"position"`
- `params` 支持同一函数不同参数（如 window=20 vs window=60 的波动率）
- 引擎根据 `requires` 检查数据是否可用，可用就执行，不可用就跳过
- 用户自定义 Metric 通过 MFile 加载（FILE_TYPES.ANALYZER），自动注册

### 4. 内置 Metric 分类

**组合级（requires=["net_value"]）：**
- 年化收益、波动率、Sharpe、Sortino、Calmar
- 最大回撤、回撤恢复天数、水下时间
- 滚动版（window 参数可配）

**信号级（requires=["signal"]）：**
- 信号总量、日均信号数、多空比例

**订单级（requires=["order"]）：**
- 成交率、平均滑点、撤单率

**持仓级（requires=["position"]）：**
- 最大持仓数、持仓集中度、换手率

**跨数据源：**
- 信号→订单转化率（requires=["signal", "order"]）
- 信号有效性/IC（requires=["signal", "net_value"]）
- 持仓收益贡献（requires=["position", "net_value"]）

### 5. AnalysisEngine — 统一入口

```python
class AnalysisEngine:
    def __init__(self, analyzer_service, order_crud, signal_crud, position_crud):
        self._services = {...}
        self._metrics: List[Metric] = []  # 内置 + 用户自定义

    def analyze(self, run_id: str, portfolio_id: str) -> AnalysisReport
    def compare(self, run_ids: List[str]) -> ComparisonReport
    def time_segments(self, run_id: str, freq="M") -> SegmentReport
    def rolling(self, run_id: str, window=60) -> RollingReport
```

**analyze 流程：**
1. 查询 run_id 下四个数据源的可用数据
2. 扫描所有已注册 Metric，检查 requires 是否满足
3. 满足的 Metric 传入数据执行 compute()
4. 结果组装为 AnalysisReport

### 6. AnalysisReport — 输出适配

```python
class AnalysisReport:
    summary: Dict[str, Any]       # 总览指标
    signal_analysis: Dict          # 信号级分析
    order_analysis: Dict           # 订单级分析
    position_analysis: Dict        # 持仓级分析
    custom_metrics: Dict           # 用户自定义分析器数据
    time_series: Dict[str, pd.DataFrame]  # 原始时间序列

    def to_dict(self) -> dict       # API 消费
    def to_dataframe() -> pd.DataFrame  # Python 消费
    def to_rich() -> Table          # CLI/TUI 消费
```

### 7. 数据缺失处理

- `net_value` 必须存在，否则报错（收益类指标全部无法计算）
- 其余数据源缺失时，对应 Metric 跳过，报告中该区域标 N/A
- 用户自定义分析器数据缺失时同样跳过

### 8. 不改变现有组件

- 不改变现有分析器、BacktestResultAggregator、回测流程
- 不改变数据存储方式
- 纯粹新增：AnalysisEngine + Metric 纯函数 + Report 类
- Web UI / API 需要综合分析时调 AnalysisEngine.analyze()

## 文件结构

```
src/ginkgo/trading/analysis/
├── analyzers/           # 现有，不改
├── metrics/             # 新增
│   ├── __init__.py
│   ├── base.py          # Metric Protocol 定义
│   ├── portfolio.py     # 组合级指标（Sharpe, MaxDD 等）
│   ├── signal.py        # 信号级指标
│   ├── order.py         # 订单级指标
│   ├── position.py      # 持仓级指标
│   └── cross_source.py  # 跨数据源指标（IC, 转化率等）
├── reports/             # 新增
│   ├── __init__.py
│   ├── base.py          # AnalysisReport 基类
│   ├── single.py        # 单次回测报告
│   ├── comparison.py    # 多策略对比报告
│   ├── segment.py       # 时间分段报告
│   └── rolling.py       # 滚动窗口报告
├── engine.py            # 新增，AnalysisEngine
└── backtest_result_aggregator.py  # 现有，不改
```

## 验证方式

1. 单元测试：每个 Metric 纯函数传入测试 DataFrame 验证计算结果
2. 集成测试：AnalysisEngine.analyze() 传入真实 run_id，验证报告生成
3. CLI 测试：`ginkgo analysis report --run-id xxx` 验证 Rich 输出
