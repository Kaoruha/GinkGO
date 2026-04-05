# Analysis Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified post-backtest analysis module that reads analyzer/signal/order/position data from ClickHouse, computes metrics via pure functions, and outputs structured reports via API/Python/CLI.

**Architecture:** Metric pure functions declare data dependencies via `requires`, AnalysisEngine checks availability and executes matching metrics, results assemble into Report objects with three output adapters.

**Tech Stack:** Python 3.12, pandas, numpy, ClickHouse (read-only), Rich (CLI), existing Ginkgo services

---

## File Structure

```
src/ginkgo/trading/analysis/
├── metrics/             # NEW
│   ├── __init__.py
│   ├── base.py          # Metric Protocol + DataProvider
│   ├── portfolio.py     # 组合级指标
│   ├── signal.py        # 信号级指标
│   ├── order.py         # 订单级指标
│   ├── position.py      # 持仓级指标
│   └── cross_source.py  # 跨数据源指标
├── reports/             # NEW
│   ├── __init__.py
│   ├── base.py          # AnalysisReport base
│   ├── single.py        # 单次回测报告
│   ├── comparison.py    # 多策略对比
│   ├── segment.py       # 时间分段归因
│   └── rolling.py       # 滚动窗口
├── engine.py            # NEW, AnalysisEngine
├── analyzers/           # EXISTING, no change
└── backtest_result_aggregator.py  # EXISTING, no change

tests/unit/trading/analysis/
├── metrics/             # NEW
│   ├── test_base.py
│   ├── test_portfolio.py
│   ├── test_signal.py
│   ├── test_order.py
│   ├── test_position.py
│   └── test_cross_source.py
├── reports/             # NEW
│   ├── test_single.py
│   ├── test_comparison.py
│   ├── test_segment.py
│   └── test_rolling.py
└── test_engine.py       # NEW
```

## Existing Code to Reuse

- `ResultService.get_signals(run_id)` → `src/ginkgo/data/services/result_service.py:345`
- `ResultService.get_orders(run_id)` → `src/ginkgo/data/services/result_service.py:392`
- `ResultService.get_positions(run_id)` → `src/ginkgo/data/services/result_service.py:433`
- `AnalyzerService.get_by_run_id(run_id, analyzer_name)` → `src/ginkgo/data/services/analyzer_service.py:95`
- `container.result_service()` / `container.analyzer_service()` → `src/ginkgo/data/containers.py`
- All backtest records have `run_id` field via `MBacktestRecordBase` → `src/ginkgo/data/models/model_backtest_record_base.py`

---

### Task 1: Metric Protocol + DataProvider

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/__init__.py`
- Create: `src/ginkgo/trading/analysis/metrics/base.py`
- Create: `tests/unit/trading/analysis/metrics/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/trading/analysis/metrics/test_base.py
import pytest
import pandas as pd
from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry


class FakeMetric(Metric):
    name = "fake"
    requires = ["net_value"]
    params = {}

    def compute(self, data: dict) -> float:
        return data["net_value"]["value"].iloc[-1]


def test_data_provider_holds_data():
    dp = DataProvider(net_value=pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
    assert "net_value" in dp.available
    assert dp.get("net_value") is not None


def test_data_provider_missing_key_returns_none():
    dp = DataProvider()
    assert dp.get("nonexistent") is None
    assert "nonexistent" not in dp.available


def test_metric_requires_check():
    m = FakeMetric()
    dp = DataProvider(net_value=pd.DataFrame({"value": [1.0]}))
    assert m.can_compute(dp) is True
    assert m.can_compute(DataProvider()) is False


def test_metric_compute():
    m = FakeMetric()
    dp = DataProvider(net_value=pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
    result = m.compute(dp)
    assert result == 3.0


def test_metric_compute_with_params():
    class WindowedMetric(Metric):
        name = "windowed"
        requires = ["net_value"]
        params = {"window": 2}

        def compute(self, data: dict) -> float:
            w = self.params["window"]
            return data["net_value"]["value"].tail(w).mean()

    m = WindowedMetric()
    m.params = {"window": 2}
    dp = DataProvider(net_value=pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
    assert m.compute(dp) == 2.5


def test_metric_registry():
    reg = MetricRegistry()
    reg.register(FakeMetric)
    assert "fake" in reg.list_metrics()
    assert reg.get("fake") is FakeMetric


def test_metric_registry_check_availability():
    reg = MetricRegistry()
    reg.register(FakeMetric)
    dp = DataProvider(net_value=pd.DataFrame({"value": [1.0]}))
    available, missing = reg.check_availability(dp)
    assert "fake" in available
    assert len(missing) == 0

    available, missing = reg.check_availability(DataProvider())
    assert "fake" in missing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/metrics/test_base.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write Metric Protocol + DataProvider + MetricRegistry**

```python
# src/ginkgo/trading/analysis/metrics/__init__.py
from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry

__all__ = ["Metric", "DataProvider", "MetricRegistry"]
```

```python
# src/ginkgo/trading/analysis/metrics/base.py
from typing import Protocol, Dict, List, Any, Optional, Type, runtime_checkable
import pandas as pd


@runtime_checkable
class Metric(Protocol):
    """指标计算协议 — 纯函数，声明依赖和计算逻辑。"""

    name: str
    requires: List[str]
    params: Dict[str, Any]

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any: ...


class DataProvider:
    """统一数据访问层，封装各数据源的 DataFrame。"""

    def __init__(self, **kwargs):
        self._data: Dict[str, pd.DataFrame] = {}

    def add(self, key: str, df: pd.DataFrame) -> None:
        self._data[key] = df

    def get(self, key: str) -> Optional[pd.DataFrame]:
        return self._data.get(key)

    @property
    def available(self) -> List[str]:
        return list(self._data.keys())


class MetricRegistry:
    """指标注册中心。"""

    def __init__(self):
        self._metrics: Dict[str, Type[Metric]] = {}

    def register(self, metric_cls: Type[Metric]) -> None:
        name = metric_cls.name
        self._metrics[name] = metric_cls

    def get(self, name: str) -> Optional[Type[Metric]]:
        return self._metrics.get(name)

    def list_metrics(self) -> List[str]:
        return list(self._metrics.keys())

    def check_availability(self, data: DataProvider) -> tuple:
        available = []
        missing = []
        for name, cls in self._metrics.items():
            if all(r in data.available for r in cls.requires):
                available.append(name)
            else:
                missing.append(name)
        return available, missing

    def instantiate(self, name: str, **params) -> Optional[Metric]:
        cls = self._metrics.get(name)
        if cls is None:
            return None
        instance = cls.__new__(cls)
        instance.params = params
        instance.name = name
        return instance
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/trading/analysis/metrics/test_base.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/analysis/metrics/ tests/unit/trading/analysis/metrics/
git commit -m "feat: add Metric Protocol, DataProvider, and MetricRegistry"
```

---

### Task 2: Portfolio-level Metrics

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/portfolio.py`
- Create: `tests/unit/trading/analysis/metrics/test_portfolio.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/metrics/test_portfolio.py
import pytest
import pandas as pd
import numpy as np
from ginkgo.trading.analysis.metrics.base import DataProvider

# Import each metric class individually after implementation
NAV = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]


def _nav_dp(nav=None):
    nav = nav or NAV
    return DataProvider(net_value=pd.DataFrame({"value": nav}))


def test_annualized_return():
    from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn
    m = AnnualizedReturn()
    result = m.compute(_nav_dp())
    # 252 trading days, 10 data points = 10/252 years
    expected = (110 / 100) ** (252 / 10) - 1
    assert abs(result - expected) < 0.01


def test_max_drawdown():
    from ginkgo.trading.analysis.metrics.portfolio import MaxDrawdown
    m = MaxDrawdown()
    result = m.compute(_nav_dp())
    # peak=100, trough=101 after peak 102, then 110
    # actual max drawdown: (101-102)/102 = -0.0098
    assert result <= 0


def test_sharpe_ratio():
    from ginkgo.trading.analysis.metrics.portfolio import SharpeRatio
    m = SharpeRatio()
    result = m.compute(_nav_dp())
    assert isinstance(result, float)


def test_sortino_ratio():
    from ginkgo.trading.analysis.metrics.portfolio import SortinoRatio
    m = SortinoRatio()
    result = m.compute(_nav_dp())
    assert isinstance(result, float)


def test_volatility():
    from ginkgo.trading.analysis.metrics.portfolio import Volatility
    m = Volatility()
    result = m.compute(_nav_dp())
    assert result > 0


def test_calmar_ratio():
    from ginkgo.trading.analysis.metrics.portfolio import CalmarRatio
    m = CalmarRatio()
    result = m.compute(_nav_dp())
    assert isinstance(result, float)


def test_rolling_sharpe():
    from ginkgo.trading.analysis.metrics.portfolio import RollingSharpe
    m = RollingSharpe()
    m.params = {"window": 5}
    result = m.compute(_nav_dp())
    assert isinstance(result, pd.Series)
    assert len(result) == len(NAV)


def test_rolling_volatility():
    from ginkgo.trading.analysis.metrics.portfolio import RollingVolatility
    m = RollingVolatility()
    m.params = {"window": 5}
    result = m.compute(_nav_dp())
    assert isinstance(result, pd.Series)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/metrics/test_portfolio.py -v`
Expected: FAIL

- [ ] **Step 3: Implement portfolio metrics**

Create `src/ginkgo/trading/analysis/metrics/portfolio.py` with 8 metric classes. Each implements the Metric protocol with `requires=["net_value"]`. Key formulas:

- **AnnualizedReturn**: `(final / initial) ** (252 / n) - 1`
- **MaxDrawdown**: `(nav - cummax) / cummax` min value
- **SharpeRatio**: `(returns.mean() - rf/252) / returns.std() * sqrt(252)`, rf=0.03 default
- **SortinoRatio**: same but `returns.std()` only for `returns < 0`
- **Volatility**: `returns.std() * sqrt(252)`
- **CalmarRatio**: `annualized_return / abs(max_drawdown)`
- **RollingSharpe**: same as Sharpe but applied to `returns.rolling(window)`
- **RollingVolatility**: same as Volatility but rolling

Helper: all compute daily returns first via `nav.pct_change().dropna()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/trading/analysis/metrics/test_portfolio.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/analysis/metrics/portfolio.py tests/unit/trading/analysis/metrics/test_portfolio.py
git commit -m "feat: add portfolio-level metrics (Sharpe, MaxDD, Volatility, etc.)"
```

---

### Task 3: Signal-level Metrics

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/signal.py`
- Create: `tests/unit/trading/analysis/metrics/test_signal.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/metrics/test_signal.py
import pytest
import pandas as pd
from ginkgo.trading.analysis.metrics.base import DataProvider


def _signal_df():
    return pd.DataFrame({
        "code": ["000001", "000002", "000001", "000003", "000001"],
        "direction": [1, 1, -1, 1, -1],
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
    })


def _signal_dp():
    return DataProvider(signal=_signal_df())


def test_signal_count():
    from ginkgo.trading.analysis.metrics.signal import SignalCount
    m = SignalCount()
    result = m.compute(_signal_dp())
    assert result == 5


def test_long_short_ratio():
    from ginkgo.trading.analysis.metrics.signal import LongShortRatio
    m = LongShortRatio()
    result = m.compute(_signal_dp())
    assert result == 3 / 2  # 3 long, 2 short


def test_daily_signal_freq():
    from ginkgo.trading.analysis.metrics.signal import DailySignalFreq
    m = DailySignalFreq()
    result = m.compute(_signal_dp())
    assert isinstance(result, (int, float))
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement signal.py** — 3 metrics: SignalCount, LongShortRatio, DailySignalFreq
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit**

---

### Task 4: Order-level Metrics

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/order.py`
- Create: `tests/unit/trading/analysis/metrics/test_order.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/metrics/test_order.py
import pytest
import pandas as pd
from ginkgo.trading.analysis.metrics.base import DataProvider

ORDER_COLS = ["order_id", "code", "direction", "status", "volume", "limit_price", "transaction_price"]


def _order_df():
    return pd.DataFrame([
        ["o1", "000001", 1, 1, 100, 10.0, 10.1],  # filled
        ["o2", "000002", 1, 0, 200, 20.0, 0.0],     # cancelled
        ["o3", "000001", -1, 1, 50, 10.2, 10.0],    # filled
    ], columns=ORDER_COLS)


def _order_dp():
    return DataProvider(order=_order_df())


def test_fill_rate():
    from ginkgo.trading.analysis.metrics.order import FillRate
    m = FillRate()
    result = m.compute(_order_dp())
    assert result == 2 / 3


def test_avg_slippage():
    from ginkgo.trading.analysis.metrics.order import AvgSlippage
    m = AvgSlippage()
    result = m.compute(_order_dp())
    # slippage = limit_price - transaction_price for filled orders
    # o1: 10.0 - 10.1 = -0.1, o3: 10.2 - 10.0 = 0.2, avg = 0.05
    assert abs(result - 0.05) < 0.001


def test_cancel_rate():
    from ginkgo.trading.analysis.metrics.order import CancelRate
    m = CancelRate()
    result = m.compute(_order_dp())
    assert result == 1 / 3
```

- [ ] **Step 2-5: Same TDD cycle** — 3 metrics: FillRate, AvgSlippage, CancelRate. Slippage = `limit_price - transaction_price` for filled orders only.

---

### Task 5: Position-level Metrics

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/position.py`
- Create: `tests/unit/trading/analysis/metrics/test_position.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/metrics/test_position.py
import pytest
import pandas as pd
from ginkgo.trading.analysis.metrics.base import DataProvider

POS_COLS = ["code", "volume", "cost", "price"]


def test_max_positions():
    from ginkgo.trading.analysis.metrics.position import MaxPositions
    dp = DataProvider(position=pd.DataFrame({
        "code": ["A", "B", "A", "C"],
        "volume": [100, 200, 0, 50],
        "cost": [10.0, 20.0, 10.0, 5.0],
        "price": [10.0, 20.0, 10.0, 5.0],
    }))
    m = MaxPositions()
    result = m.compute(dp)
    assert result == 3  # A, B, C at peak


def test_concentration_top_n():
    from ginkgo.trading.analysis.metrics.position import ConcentrationTopN
    dp = DataProvider(position=pd.DataFrame({
        "code": ["A", "B", "C"],
        "volume": [600, 300, 100],
        "cost": [10.0, 10.0, 10.0],
        "price": [10.0, 10.0, 10.0],
    }))
    m = ConcentrationTopN()
    m.params = {"n": 2}
    result = m.compute(dp)
    assert abs(result - 0.9) < 0.01  # top 2 = 900/1000
```

- [ ] **Step 2-5: Same TDD cycle** — 2 metrics: MaxPositions, ConcentrationTopN

---

### Task 6: Cross-source Metrics

**Files:**
- Create: `src/ginkgo/trading/analysis/metrics/cross_source.py`
- Create: `tests/unit/trading/analysis/metrics/test_cross_source.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/metrics/test_cross_source.py
import pytest
import pandas as pd
import numpy as np
from ginkgo.trading.analysis.metrics.base import DataProvider


def test_signal_order_conversion():
    from ginkgo.trading.analysis.metrics.cross_source import SignalOrderConversion
    dp = DataProvider(
        signal=pd.DataFrame({"code": ["A", "A", "B"], "timestamp": pd.date_range("2024-01-01", periods=3)}),
        order=pd.DataFrame({"code": ["A", "C"], "timestamp": pd.date_range("2024-01-01", periods=2)}),
    )
    m = SignalOrderConversion()
    result = m.compute(dp)
    # 2 unique codes in signals, 1 converted to order = 50%
    assert result == 0.5


def test_signal_ic():
    from ginkgo.trading.analysis.metrics.cross_source import SignalIC
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    dp = DataProvider(
        signal=pd.DataFrame({
            "timestamp": dates,
            "code": ["A"] * 5,
            "direction": [1, 1, -1, 1, -1],  # 3 long, 2 short
        }),
        net_value=pd.DataFrame({
            "timestamp": dates,
            "value": [100, 102, 99, 103, 97],
        }),
    )
    m = SignalIC()
    result = m.compute(dp)
    assert isinstance(result, float)
    assert -1 <= result <= 1  # correlation range
```

- [ ] **Step 2-5: Same TDD cycle** — 2 metrics: SignalOrderConversion (signal codes intersect order codes / signal unique codes), SignalIC (daily aggregate signal direction vs next-day return, Spearman correlation)

---

### Task 7: AnalysisReport Base + Single Report

**Files:**
- Create: `src/ginkgo/trading/analysis/reports/__init__.py`
- Create: `src/ginkgo/trading/analysis/reports/base.py`
- Create: `src/ginkgo/trading/analysis/reports/single.py`
- Create: `tests/unit/trading/analysis/reports/test_single.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/reports/test_single.py
import pytest
import pandas as pd
from ginkgo.trading.analysis.metrics.base import MetricRegistry, DataProvider
from ginkgo.trading.analysis.reports.base import AnalysisReport
from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown


class FakeMetric:
    name = "fake"
    requires = ["nonexistent"]
    params = {}
    def compute(self, data):
        return 42.0


def test_report_to_dict():
    reg = MetricRegistry()
    reg.register(AnnualizedReturn)
    reg.register(MaxDrawdown)
    dp = DataProvider(net_value=pd.DataFrame({"value": [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]}))
    report = AnalysisReport(run_id="test_run", registry=reg, data=dp)
    d = report.to_dict()
    assert "run_id" in d
    assert "summary" in d
    assert isinstance(d["summary"], dict)


def test_report_to_dataframe():
    reg = MetricRegistry()
    reg.register(AnnualizedReturn)
    dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
    report = AnalysisReport(run_id="test", registry=reg, data=dp)
    df = report.to_dataframe()
    assert isinstance(df, pd.DataFrame)


def test_report_missing_metric_n_a():
    reg = MetricRegistry()
    reg.register(FakeMetric)
    dp = DataProvider()
    report = AnalysisReport(run_id="test", registry=reg, data=dp)
    d = report.to_dict()
    assert d["metrics"]["fake"] == "N/A"


def test_report_custom_analyzer_data():
    reg = MetricRegistry()
    dp = DataProvider(
        net_value=pd.DataFrame({"value": [100, 105]}),
        my_custom=pd.DataFrame({"value": [1, 2]}),
    )
    report = AnalysisReport(run_id="test", registry=reg, data=dp)
    d = report.to_dict()
    assert "my_custom" in d["custom_metrics"]
```

- [ ] **Step 2-5: Same TDD cycle** — `AnalysisReport` base class stores run_id, computes all available metrics, organizes into summary/custom_metrics/time_series sections. `to_dict()` / `to_dataframe()` / `to_rich()` adapters.

---

### Task 8: Comparison + Segment + Rolling Reports

**Files:**
- Create: `src/ginkgo/trading/analysis/reports/comparison.py`
- Create: `src/ginkgo/trading/analysis/reports/segment.py`
- Create: `src/ginkgo/trading/analysis/reports/rolling.py`
- Create: `tests/unit/trading/analysis/reports/test_comparison.py`
- Create: `tests/unit/trading/analysis/reports/test_segment.py`
- Create: `tests/unit/trading/analysis/reports/test_rolling.py`

- [ ] **Step 1: Write failing tests for all three report types**
- [ ] **Step 2: Implement ComparisonReport** — takes multiple AnalysisReport instances, produces side-by-side metrics table
- [ ] **Step 3: Implement SegmentReport** — splits net_value by time frequency (M/Q/Y), computes metrics per segment
- [ ] **Step 4: Implement RollingReport** — applies metrics over sliding window on net_value series
- [ ] **Step 5: Run all tests to verify they pass**
- [ ] **Step 6: Commit**

---

### Task 9: AnalysisEngine

**Files:**
- Create: `src/ginkgo/trading/analysis/engine.py`
- Create: `tests/unit/trading/analysis/test_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/trading/analysis/test_engine.py
import pytest
from unittest.mock import MagicMock, patch
from ginkgo.trading.analysis.engine import AnalysisEngine


def test_engine_analyze_missing_net_value_raises():
    engine = AnalysisEngine.__new__(AnalysisEngine)
    engine._result_service = MagicMock()
    engine._analyzer_service = MagicMock()
    # Mock: net_value query returns empty
    engine._analyzer_service.get_by_run_id.return_value = MagicMock(
        is_success=lambda: False, data=None
    )
    with pytest.raises(ValueError, match="net_value"):
        engine.analyze("run_1", "portfolio_1")


def test_engine_analyze_returns_report():
    engine = AnalysisEngine.__new__(AnalysisEngine)
    # Mock all data sources to return valid DataFrames
    with patch.object(engine, '_load_data') as mock_load:
        mock_load.return_value = MagicMock(
            available=["net_value", "signal", "order", "position"],
            get=lambda key: MagicMock(
                is_success=lambda: True,
                data=type('D', (), {'value': [100, 102, 101]})()
            )
        )
        report = engine.analyze("run_1", "portfolio_1")
        assert report.run_id == "run_1"
```

- [ ] **Step 2-5: Same TDD cycle** — AnalysisEngine:
  - `__init__(result_service, analyzer_service)` — receives services from container
  - `_load_data(run_id, portfolio_id)` → queries 4 data sources via ResultService/AnalyzerService, returns DataProvider
  - `analyze(run_id, portfolio_id)` → checks net_value exists, runs all metrics, returns AnalysisReport
  - `compare(run_ids)` → runs analyze() for each, builds ComparisonReport
  - `time_segments(run_id, freq)` → splits data by freq, runs metrics per segment
  - `rolling(run_id, window)` → runs rolling metrics, returns RollingReport

- [ ] **Step 6: Commit**

---

### Task 10: Module Exports + Integration

**Files:**
- Modify: `src/ginkgo/trading/analysis/__init__.py` — add exports for engine, metrics, reports
- Create: `tests/unit/trading/analysis/test_integration.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/unit/trading/analysis/test_integration.py
def test_module_imports():
    from ginkgo.trading.analysis.engine import AnalysisEngine
    from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry
    from ginkgo.trading.analysis.reports.base import AnalysisReport
    from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown
    assert True
```

- [ ] **Step 2: Update analysis/__init__.py** to export new modules
- [ ] **Step 3: Run integration test**
- [ ] **Step 4: Commit**
