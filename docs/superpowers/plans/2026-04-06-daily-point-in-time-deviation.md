# Daily Point-in-Time Deviation Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable daily deviation checking that works at any day (not only after full slice completion), so Paper/Live trading can be monitored from day 1.

**Architecture:** Add a `daily_curves` structure to the monitoring baseline (per-day reference distributions from backtest slices). Add `check_point_in_time()` to `LiveDeviationDetector` that compares live day-N metrics against backtest day-N distributions. Worker calls this daily; slice completion still triggers the existing deep check.

**Tech Stack:** Python 3.12.8, pandas, numpy, Redis, ClickHouse, pytest

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py` | Add `_extract_daily_curves()` and include `daily_curves` in baseline |
| `src/ginkgo/trading/analysis/evaluation/live_deviation_detector.py` | Add `check_point_in_time()` and `current_day_index` tracking |
| `src/ginkgo/trading/analysis/evaluation/deviation_checker.py` | Add `run_daily_point_check()` method |
| `src/ginkgo/workers/paper_trading_worker.py` | Wire daily check into `_run_deviation_check()`, supplement `_load_today_records()` |
| `tests/unit/trading/analysis/test_daily_deviation.py` | New test file for daily curves and point-in-time check |

---

## Background: Current vs Proposed

**Current flow (Mode B only):**
```
Day 1..29: accumulate data, no check
Day 30: slice completes → check_deviation_on_slice_complete() → alert
Day 31..59: accumulate, no check
Day 60: slice completes → check again
```

**Proposed flow (Mode A + B):**
```
Day 1: check_point_in_time(day=1) → compare live day-1 vs backtest day-1 distribution
Day 2: check_point_in_time(day=2) → compare live day-2 vs backtest day-2 distribution
...
Day 30: check_point_in_time(day=30) + check_deviation_on_slice_complete() (deep check)
Day 31: reset, check_point_in_time(day=1) again
```

---

### Task 1: Add daily curves to monitoring baseline

**Files:**
- Modify: `src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py:285-317`
- Modify: `src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py:56-150`
- Test: `tests/unit/trading/analysis/test_daily_deviation.py`

**Context:** `_create_monitoring_baseline()` currently receives `slice_metrics` (aggregated per-slice values) and produces `baseline_stats` (mean/std per metric). We need per-day reference data. The raw slice DataFrames (with daily records) are available in `balanced_slices` but lost when `_calculate_slice_metrics()` aggregates them.

- [ ] **Step 1: Write failing test for daily curves in baseline**

```python
# tests/unit/trading/analysis/test_daily_deviation.py
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestExtractDailyCurves:
    """_extract_daily_curves 单元测试"""

    def test_extracts_per_day_values_from_slices(self):
        """应从切片数据中提取每个指标每天的值"""
        from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator

        evaluator = BacktestEvaluator()

        # 构造 2 个切片，每个 3 天，2 个指标
        day_base = datetime(2026, 1, 1)
        slices = []
        for slice_idx in range(2):
            records = []
            for day_offset in range(3):
                day = day_base + timedelta(days=day_offset)
                records.append({
                    "timestamp": day,
                    "name": "net_value",
                    "value": 1.0 + slice_idx * 0.1 + day_offset * 0.01,
                })
                records.append({
                    "timestamp": day,
                    "name": "profit",
                    "value": 0.0 + slice_idx * 0.05 + day_offset * 0.005,
                })
            df = pd.DataFrame(records)
            slices.append({"analyzer_data": df, "signal_data": pd.DataFrame(), "order_data": pd.DataFrame()})

        result = evaluator._extract_daily_curves(slices)

        assert "net_value" in result
        assert len(result["net_value"]) == 3  # 3 days
        assert len(result["net_value"][1]) == 2  # 2 slices
        # slice 0 day 0: 1.00, slice 1 day 0: 1.10
        assert result["net_value"][1][0] == pytest.approx(1.00)
        assert result["net_value"][1][1] == pytest.approx(1.10)

    def test_handles_empty_analyzer_data(self):
        """空数据应返回空字典"""
        from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator

        evaluator = BacktestEvaluator()
        slices = [{"analyzer_data": pd.DataFrame(), "signal_data": pd.DataFrame(), "order_data": pd.DataFrame()}]
        result = evaluator._extract_daily_curves(slices)
        assert result == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestExtractDailyCurves -v`
Expected: FAIL — `AttributeError: 'BacktestEvaluator' object has no attribute '_extract_daily_curves'`

- [ ] **Step 3: Implement _extract_daily_curves()**

In `src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py`, add method after `_create_monitoring_baseline()` (after line 317):

```python
    def _extract_daily_curves(self, slices: List[Dict]) -> Dict[str, Dict[int, List[float]]]:
        """
        从切片数据中提取每个指标每天的值分布（用于点时对比）

        Args:
            slices: 切片列表，每个切片包含 analyzer_data DataFrame

        Returns:
            Dict: {metric_name: {day_index: [value_from_slice_1, value_from_slice_2, ...]}}
            day_index 从 1 开始
        """
        daily_curves: Dict[str, Dict[int, List[float]]] = {}

        for slice_data in slices:
            df = slice_data.get("analyzer_data")
            if df is None or df.empty or "timestamp" not in df.columns:
                continue

            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")

            # 计算每天在该切片内的偏移量
            if len(df) == 0:
                continue
            start_time = df["timestamp"].min()

            for _, row in df.iterrows():
                metric_name = row["name"]
                day_offset = (row["timestamp"] - start_time).days + 1  # 1-indexed

                if metric_name not in daily_curves:
                    daily_curves[metric_name] = {}

                if day_offset not in daily_curves[metric_name]:
                    daily_curves[metric_name][day_offset] = []

                daily_curves[metric_name][day_offset].append(float(row["value"]))

        return daily_curves
```

- [ ] **Step 4: Modify _create_monitoring_baseline() to include daily curves**

Change the signature of `_create_monitoring_baseline()` (line 285) to accept `slices`:

```python
    def _create_monitoring_baseline(self,
                                  slice_metrics: Dict[str, List[float]],
                                  slice_period_days: int,
                                  slices: List[Dict] = None) -> Dict:
```

Add at the end of the method, before the return statement (after line 316):

```python
        # 提取每日曲线数据（用于点时对比）
        daily_curves = {}
        if slices:
            daily_curves = self._extract_daily_curves(slices)
```

Add `'daily_curves': daily_curves` to the return dict (modify line 312-316):

```python
        return {
            'slice_period_days': slice_period_days,
            'baseline_stats': baseline_stats,
            'daily_curves': daily_curves,
            'creation_time': clock_now().isoformat(),
            'total_slices': len(next(iter(slice_metrics.values()))) if slice_metrics else 0
        }
```

- [ ] **Step 5: Update the caller in evaluate_backtest_stability()**

In `evaluate_backtest_stability()` around line 119, pass `balanced_slices` to `_create_monitoring_baseline()`:

```python
            monitoring_baseline = self._create_monitoring_baseline(slice_metrics, optimal_period, balanced_slices)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestExtractDailyCurves -v`
Expected: PASS

- [ ] **Step 7: Run existing tests to verify no regression**

Run: `python -m pytest tests/unit/workers/test_paper_trading_worker.py tests/unit/client/test_paper_trading_cli.py -p no:logging -q`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py tests/unit/trading/analysis/test_daily_deviation.py
git commit -m "feat: add daily curves to monitoring baseline for point-in-time deviation check"
```

---

### Task 2: Add check_point_in_time() to LiveDeviationDetector

**Files:**
- Modify: `src/ginkgo/trading/analysis/evaluation/live_deviation_detector.py`
- Test: `tests/unit/trading/analysis/test_daily_deviation.py`

**Context:** `LiveDeviationDetector` currently only checks deviation when a slice completes. We add `check_point_in_time(day_index, current_metrics)` that works at any day using `daily_curves` from the baseline.

- [ ] **Step 1: Write failing test**

Add to `tests/unit/trading/analysis/test_daily_deviation.py`:

```python
class TestCheckPointInTime:
    """check_point_in_time 单元测试"""

    def _make_detector(self, daily_curves=None):
        """创建带 daily_curves baseline 的 detector"""
        from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector

        baseline_stats = {
            "net_value": {"mean": 1.05, "std": 0.03, "values": [1.05, 1.08, 1.03]},
        }
        if daily_curves is None:
            daily_curves = {
                "net_value": {1: [1.00, 1.01, 0.99], 2: [1.02, 1.03, 1.00]},
            }

        detector = LiveDeviationDetector(
            baseline_stats=baseline_stats,
            slice_period_days=2,
        )
        detector._daily_curves = daily_curves
        return detector

    def test_normal_deviation(self):
        """正常范围内的值应返回 NORMAL"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"net_value": 1.00})
        assert result["status"] == "completed"
        assert result["overall_level"] == "NORMAL"

    def test_severe_deviation(self):
        """严重偏离应返回 SEVERE"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"net_value": 1.20})
        assert result["overall_level"] == "SEVERE"
        assert "net_value" in result["deviations"]

    def test_unknown_day_index_returns_no_data(self):
        """超出 daily_curves 范围的 day_index 应返回 no_data"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=99, current_metrics={"net_value": 1.00})
        assert result["status"] == "no_data"

    def test_unknown_metric_is_skipped(self):
        """baseline 中不存在的指标应被跳过"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"unknown_metric": 1.0})
        assert result["status"] == "completed"
        assert len(result["deviations"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestCheckPointInTime -v`
Expected: FAIL — `AttributeError: 'LiveDeviationDetector' object has no attribute 'check_point_in_time'`

- [ ] **Step 3: Implement check_point_in_time()**

In `src/ginkgo/trading/analysis/evaluation/live_deviation_detector.py`, add `_daily_curves` to `__init__()` (after line 55):

```python
        self._daily_curves: Dict[str, Dict[int, List[float]]] = {}
```

Add the method after `check_deviation_on_slice_complete()` (after line 154):

```python
    def check_point_in_time(self, day_index: int, current_metrics: Dict[str, float]) -> Dict:
        """
        点时偏差检测：比较当前天的指标与回测同日分布

        Args:
            day_index: 当前切片内的天数（从 1 开始）
            current_metrics: 当前指标值，如 {"net_value": 1.05, "profit": 0.03}

        Returns:
            Dict: 偏差结果，与 check_deviation_on_slice_complete 格式一致
        """
        if not self._daily_curves:
            return {"status": "no_data"}

        if not current_metrics:
            return {"status": "no_data"}

        deviation_results = {}
        overall_level = "NORMAL"

        for metric_name, current_value in current_metrics.items():
            if metric_name not in self._daily_curves:
                continue

            day_map = self._daily_curves[metric_name]
            if day_index not in day_map:
                continue

            ref_values = day_map[day_index]
            if not ref_values:
                continue

            ref_mean = np.mean(ref_values)
            ref_std = np.std(ref_values, ddof=1) if len(ref_values) > 1 else 0

            if ref_std == 0:
                continue

            # 复用已有的偏差计算逻辑
            deviation_info = self._calculate_metric_deviation(
                metric_name, current_value, {"mean": ref_mean, "std": ref_std, "values": ref_values}
            )
            deviation_results[metric_name] = deviation_info

            if deviation_info["level"] == "SEVERE":
                overall_level = "SEVERE"
            elif deviation_info["level"] == "MODERATE" and overall_level == "NORMAL":
                overall_level = "MODERATE"

        if not deviation_results:
            return {"status": "no_data"}

        return {
            "status": "completed",
            "overall_level": overall_level,
            "metrics": current_metrics,
            "deviations": deviation_results,
            "day_index": day_index,
        }
```

- [ ] **Step 4: Update create_live_monitor() to accept daily_curves**

In `src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py`, modify `create_live_monitor()` (line 152) to pass daily curves:

```python
    def create_live_monitor(self,
                          monitoring_baseline: Dict,
                          confidence_levels: List[float] = [0.68, 0.95, 0.99]) -> LiveDeviationDetector:
        GLOG.info("创建实盘监控器")

        baseline_stats = monitoring_baseline.get('baseline_stats', {})
        slice_period = monitoring_baseline.get('slice_period_days', 30)
        daily_curves = monitoring_baseline.get('daily_curves', {})

        monitor = LiveDeviationDetector(
            baseline_stats=baseline_stats,
            slice_period_days=slice_period,
            confidence_levels=confidence_levels
        )
        monitor._daily_curves = daily_curves

        GLOG.info(f"实盘监控器创建完成，切片周期: {slice_period}天")
        return monitor
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestCheckPointInTime -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/trading/analysis/evaluation/live_deviation_detector.py src/ginkgo/trading/analysis/evaluation/backtest_evaluator.py tests/unit/trading/analysis/test_daily_deviation.py
git commit -m "feat: add check_point_in_time() for daily deviation monitoring"
```

---

### Task 3: Wire daily check into DeviationChecker and Worker

**Files:**
- Modify: `src/ginkgo/trading/analysis/evaluation/deviation_checker.py`
- Modify: `src/ginkgo/workers/paper_trading_worker.py:288-309`
- Test: `tests/unit/trading/analysis/test_daily_deviation.py`

**Context:** `DeviationChecker.run_deviation_check()` currently only calls `detector.check_deviation_on_slice_complete()` when a slice is done. We add `run_daily_point_check()` that always calls `check_point_in_time()`. Worker calls both: daily point check every day, deep check on slice completion.

- [ ] **Step 1: Write failing test for DeviationChecker daily point check**

Add to `tests/unit/trading/analysis/test_daily_deviation.py`:

```python
class TestDeviationCheckerDaily:
    """DeviationChecker.run_daily_point_check() 测试"""

    def test_calls_check_point_in_time(self):
        """应调用 detector 的 check_point_in_time"""
        from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker

        mock_detector = MagicMock()
        mock_detector.check_point_in_time.return_value = {"status": "no_data"}

        checker = DeviationChecker()
        checker._detectors = {"pid-1": mock_detector}

        result = checker.run_daily_point_check("pid-1", day_index=5, current_metrics={"net_value": 1.05})

        mock_detector.check_point_in_time.assert_called_once_with(5, {"net_value": 1.05})

    def test_handles_deviation_result(self):
        """检测到偏离时应调用 handle_deviation_result"""
        from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker

        mock_detector = MagicMock()
        mock_detector.check_point_in_time.return_value = {
            "status": "completed",
            "overall_level": "SEVERE",
            "deviations": {"net_value": {"level": "SEVERE", "z_score": 3.0}},
            "metrics": {"net_value": 1.20},
        }

        mock_handle = MagicMock()
        checker = DeviationChecker()
        checker._detectors = {"pid-1": mock_detector}
        checker.handle_deviation_result = mock_handle

        checker.run_daily_point_check("pid-1", day_index=1, current_metrics={"net_value": 1.20})

        mock_handle.assert_called_once()
        call_args = mock_handle.call_args[0]
        assert call_args[0] == "pid-1"
        assert call_args[1]["overall_level"] == "SEVERE"

    def test_skips_when_no_detector(self):
        """无 detector 时应返回 None"""
        from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker

        checker = DeviationChecker()
        result = checker.run_daily_point_check("unknown-pid", day_index=1, current_metrics={})
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestDeviationCheckerDaily -v`
Expected: FAIL — `AttributeError: 'DeviationChecker' object has no attribute 'run_daily_point_check'`

- [ ] **Step 3: Add run_daily_point_check() to DeviationChecker**

In `src/ginkgo/trading/analysis/evaluation/deviation_checker.py`, add after `run_deviation_check()` (after line 121):

```python
    def run_daily_point_check(self, portfolio_id: str, day_index: int,
                               current_metrics: Dict[str, float]) -> Optional[Dict]:
        """
        每日点时偏差检测（不依赖切片完成）

        Args:
            portfolio_id: 组合ID
            day_index: 当前切片内的天数（从 1 开始）
            current_metrics: 当前指标值

        Returns:
            检测结果或 None
        """
        detector = self._detectors.get(portfolio_id)
        if not detector:
            return None

        try:
            result = detector.check_point_in_time(day_index, current_metrics)
            if result and result.get("status") == "completed":
                config = self.get_deviation_config(portfolio_id)
                self.handle_deviation_result(
                    portfolio_id, result,
                    auto_takedown=config.get("auto_takedown", False),
                )
            return result
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Daily point check error for {portfolio_id[:8]}: {e}")
            return None
```

- [ ] **Step 4: Modify Worker._run_deviation_check() to call both modes**

In `src/ginkgo/workers/paper_trading_worker.py`, modify `_run_deviation_check()` (around line 288):

```python
    def _run_deviation_check(self) -> None:
        """遍历所有 portfolio 执行偏差检测（点时 + 切片完成）"""
        if not self.deviation_checker._detectors:
            return

        for portfolio in self._engine.portfolios:
            try:
                records = self._load_today_records(portfolio.portfolio_id)

                # Mode A: 每日点时对比
                try:
                    day_index = self._get_day_index(portfolio)
                    current_metrics = self._extract_current_metrics(records)
                    if day_index and current_metrics:
                        self.deviation_checker.run_daily_point_check(
                            portfolio.portfolio_id, day_index, current_metrics
                        )
                except Exception as e:
                    GLOG.ERROR(f"[PAPER-WORKER] Daily point check error: {e}")

                # Mode B: 切片完成深度对比
                result = self.deviation_checker.run_deviation_check(
                    portfolio.portfolio_id, records
                )
                if result:
                    config = self._get_deviation_config(portfolio.portfolio_id)
                    self.deviation_checker.handle_deviation_result(
                        portfolio.portfolio_id, result,
                        auto_takedown=config.get("auto_takedown", False),
                    )
            except Exception as e:
                GLOG.ERROR(
                    f"[PAPER-WORKER] Deviation check error for "
                    f"{portfolio.portfolio_id[:8]}: {e}"
                )

    def _get_day_index(self, portfolio) -> Optional[int]:
        """计算当前 portfolio 在切片周期内的天数"""
        try:
            detector = self.deviation_checker._detectors.get(portfolio.portfolio_id)
            if not detector or not detector.current_slice_data.get("start_date"):
                return None
            start = detector.current_slice_data["start_date"]
            now = datetime.now()
            return (now - start).days + 1
        except Exception:
            return None

    def _extract_current_metrics(self, records: Dict) -> Dict[str, float]:
        """从当日记录中提取最新指标值"""
        metrics = {}
        for record in records.get("analyzers", []):
            name = record.get("name", "")
            value = record.get("value", 0)
            # 保留最后一个值（如果是同一指标的多次记录）
            metrics[name] = float(value)
        return metrics
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py tests/unit/workers/test_paper_trading_worker.py tests/unit/client/test_paper_trading_cli.py -p no:logging -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/trading/analysis/evaluation/deviation_checker.py src/ginkgo/workers/paper_trading_worker.py tests/unit/trading/analysis/test_daily_deviation.py
git commit -m "feat: wire daily point-in-time deviation check into DeviationChecker and Worker"
```

---

### Task 4: Supplement _load_today_records with signal/order data

**Files:**
- Modify: `src/ginkgo/workers/paper_trading_worker.py:311-336`
- Test: `tests/unit/workers/test_paper_trading_worker.py`

**Context:** `_load_today_records()` currently only queries analyzer records. Signal and order data are always empty `[]`, limiting deviation analysis to analyzer metrics only.

- [ ] **Step 1: Write failing test**

Add to `tests/unit/trading/analysis/test_daily_deviation.py`:

```python
class TestLoadTodayRecords:
    """_load_today_records 补充 signal/order 数据测试"""

    @patch("ginkgo.workers.paper_trading_worker.GLOG")
    def test_loads_signal_and_order_records(self, mock_glog):
        """应查询并返回 signal 和 order 记录"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test")

        mock_signal_record = MagicMock()
        mock_signal_record.portfolio_id = "pid-1"
        mock_signal_record.code = "000001.SZ"
        mock_signal_record.direction = 1

        mock_order_record = MagicMock()
        mock_order_record.portfolio_id = "pid-1"
        mock_order_record.code = "000001.SZ"
        mock_order_record.volume = 100

        mock_signal_crud = MagicMock()
        mock_signal_crud.find.return_value = [mock_signal_record]
        mock_order_crud = MagicMock()
        mock_order_crud.find.return_value = [mock_order_record]

        with patch("ginkgo.services") as mock_services:
            mock_services.data.cruds.signal.return_value = mock_signal_crud
            mock_services.data.cruds.order_record.return_value = mock_order_crud
            mock_services.data.services.analyzer_service.return_value.get_by_run_id.return_value = MagicMock(
                is_success=True, data=[]
            )

            records = worker._load_today_records("pid-1")

        assert len(records["signals"]) == 1
        assert len(records["orders"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestLoadTodayRecords -v`
Expected: FAIL — `assert len(records["signals"]) == 1` (signals is empty list)

- [ ] **Step 3: Add signal and order queries to _load_today_records()**

In `src/ginkgo/workers/paper_trading_worker.py`, modify `_load_today_records()` (line 311-336). Replace the return statement area with:

```python
        records = {"analyzers": [], "signals": [], "orders": []}

        try:
            analyzer_service = services.data.services.analyzer_service()
            result = analyzer_service.get_by_run_id(
                run_id="paper",
                portfolio_id=portfolio_id,
            )
            if result.is_success() and result.data:
                for r in result.data:
                    ts = str(getattr(r, 'timestamp', ''))[:10]
                    if ts == today:
                        records["analyzers"].append({
                            "name": getattr(r, 'name', ''),
                            "value": float(getattr(r, 'value', 0)),
                        })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load analyzer records: {e}")

        # 补充 signal 记录
        try:
            signal_crud = services.data.cruds.signal()
            signal_records = signal_crud.find(
                filters={"portfolio_id": portfolio_id}
            )
            for r in (signal_records or []):
                ts = str(getattr(r, 'timestamp', ''))[:10]
                if ts == today:
                    records["signals"].append({
                        "code": getattr(r, 'code', ''),
                        "direction": getattr(r, 'direction', 0),
                        "volume": getattr(r, 'volume', 0),
                    })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load signal records: {e}")

        # 补充 order 记录
        try:
            order_crud = services.data.cruds.order_record()
            order_records = order_crud.find(
                filters={"portfolio_id": portfolio_id}
            )
            for r in (order_records or []):
                ts = str(getattr(r, 'timestamp', ''))[:10]
                if ts == today:
                    records["orders"].append({
                        "code": getattr(r, 'code', ''),
                        "volume": getattr(r, 'volume', 0),
                        "price": float(getattr(r, 'transaction_price', 0)),
                    })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load order records: {e}")

        return records
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/trading/analysis/test_daily_deviation.py::TestLoadTodayRecords tests/unit/workers/test_paper_trading_worker.py -p no:logging -q`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/workers/paper_trading_worker.py tests/unit/trading/analysis/test_daily_deviation.py
git commit -m "feat: supplement _load_today_records with signal and order data"
```

---

### Task 5: Update project memory

- [ ] **Step 1: Update deviation detection memory file**

Update `/home/kaoru/.claude/projects/-home-kaoru-Ginkgo/memory/project_deviation_detection.md` to reflect:
- Mode A (daily point-in-time) is now implemented
- `_load_today_records` now includes signal and order data
- CLI tests are fixed
- DeviationChecker supports both `run_daily_point_check()` and `run_deviation_check()`

---

## Self-Review Checklist

**1. Spec coverage:**
- Daily point-in-time comparison → Task 2
- Works from day 1, no slice wait → Task 2 (check_point_in_time)
- Uses same z-score classification → Task 2 (reuses _calculate_metric_deviation)
- Slice completion still triggers deep check → Task 3 (both modes called)
- Signal/order data gap → Task 4

**2. Placeholder scan:**
- No TBD/TODO found
- All test code is concrete with actual assertions
- All file paths are explicit

**3. Type consistency:**
- `_daily_curves` structure: `{metric_name: {day_index: [values]}}` — consistent across Task 1, 2, 3
- `check_point_in_time(day_index, current_metrics)` signature — consistent in tests and implementation
- `run_daily_point_check(portfolio_id, day_index, current_metrics)` — consistent in DeviationChecker and Worker
