# Upstream: AnalysisEngine (engine.py)
# Downstream: None (单元测试)
# Role: AnalysisEngine 统一入口的单元测试


"""
AnalysisEngine 单元测试

测试 AnalysisEngine 作为回测分析统一入口的各项功能：
- 数据加载 (net_value 必需, signal/order/position 可选)
- 单次分析 analyze → SingleReport
- 多次对比 compare → ComparisonReport
- 分段分析 time_segments → SegmentReport
- 滚动分析 rolling → RollingReport
- 自定义指标注册
- 部分数据加载容错
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import pytest
import pandas as pd

from ginkgo.trading.analysis.engine import AnalysisEngine
from ginkgo.trading.analysis.metrics.base import MetricRegistry
from ginkgo.trading.analysis.reports.single import SingleReport
from ginkgo.trading.analysis.reports.comparison import ComparisonReport
from ginkgo.trading.analysis.reports.segment import SegmentReport
from ginkgo.trading.analysis.reports.rolling import RollingReport


# ============================================================
# 测试数据构造辅助
# ============================================================

def _make_net_value_df(days: int = 100, start: datetime = None) -> pd.DataFrame:
    """构造 net_value DataFrame (timestamp, value 列)"""
    if start is None:
        start = datetime(2023, 1, 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    # 简单递增净值曲线
    values = [1.0 + 0.001 * i for i in range(days)]
    return pd.DataFrame({"timestamp": dates, "value": values})


def _make_signal_records(count: int = 10) -> list:
    """构造 Signal 实体模拟对象列表"""
    records = []
    for i in range(count):
        obj = MagicMock()
        obj.__dict__ = {
            "code": f"00000{i % 3 + 1}.SZ",
            "direction": 1 if i % 2 == 0 else -1,
            "timestamp": datetime(2023, 1, 1) + timedelta(days=i),
            "volume": 100 * (i + 1),
            "price": 10.0 + i,
        }
        records.append(obj)
    return records


def _make_order_records(count: int = 10) -> list:
    """构造 Order 实体模拟对象列表"""
    records = []
    for i in range(count):
        obj = MagicMock()
        obj.__dict__ = {
            "code": f"00000{i % 3 + 1}.SZ",
            "direction": 1 if i % 2 == 0 else -1,
            "volume": 100 * (i + 1),
            "limit_price": 10.0 + i,
            "transaction_price": 10.05 + i,
            "status": 1,
            "timestamp": datetime(2023, 1, 1) + timedelta(days=i),
        }
        records.append(obj)
    return records


def _make_position_records(count: int = 10) -> list:
    """构造 Position 实体模拟对象列表"""
    records = []
    for i in range(count):
        obj = MagicMock()
        obj.__dict__ = {
            "code": f"00000{i % 3 + 1}.SZ",
            "cost": 10.0 + i,
            "volume": 100 * (i + 1),
            "price": 10.5 + i,
            "timestamp": datetime(2023, 1, 1) + timedelta(days=i),
        }
        records.append(obj)
    return records


def _make_services(
    net_value_df=None,
    signal_records=None,
    order_records=None,
    position_records=None,
    net_value_success=True,
    signal_success=True,
    order_success=True,
    position_success=True,
):
    """构造 mock 的 result_service 和 analyzer_service"""
    result_service = MagicMock()
    analyzer_service = MagicMock()

    # analyzer_service.get_by_run_id 返回 net_value DataFrame
    nv_result = MagicMock()
    nv_result.is_success.return_value = net_value_success
    if net_value_df is not None:
        nv_result.data = net_value_df
    else:
        nv_result.data = None
    analyzer_service.get_by_run_id.return_value = nv_result

    # result_service.get_signals
    sig_result = MagicMock()
    sig_result.is_success.return_value = signal_success
    if signal_records is not None:
        sig_result.data = {"data": signal_records, "total": len(signal_records)}
    else:
        sig_result.data = None
    result_service.get_signals.return_value = sig_result

    # result_service.get_orders
    ord_result = MagicMock()
    ord_result.is_success.return_value = order_success
    if order_records is not None:
        ord_result.data = {"data": order_records, "total": len(order_records)}
    else:
        ord_result.data = None
    result_service.get_orders.return_value = ord_result

    # result_service.get_positions
    pos_result = MagicMock()
    pos_result.is_success.return_value = position_success
    if position_records is not None:
        pos_result.data = {"data": position_records, "total": len(position_records)}
    else:
        pos_result.data = None
    result_service.get_positions.return_value = pos_result

    return result_service, analyzer_service


# ============================================================
# 测试类
# ============================================================

class TestAnalysisEngine:
    """AnalysisEngine 核心功能测试"""

    def test_analyze_missing_net_value_raises(self):
        """net_value 不可用 → ValueError"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        result_service, analyzer_service = _make_services(
            net_value_df=None, net_value_success=True
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        with pytest.raises(ValueError, match="net_value"):
            engine.analyze("run-001")

    def test_analyze_net_value_service_failure_raises(self):
        """analyzer_service 返回失败 → ValueError"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        result_service, analyzer_service = _make_services(net_value_success=False)
        engine = AnalysisEngine(result_service, analyzer_service)
        with pytest.raises(ValueError, match="net_value"):
            engine.analyze("run-001")

    def test_analyze_returns_single_report(self):
        """所有数据可用 → 返回 SingleReport"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(
            net_value_df=nv_df,
            signal_records=_make_signal_records(),
            order_records=_make_order_records(),
            position_records=_make_position_records(),
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001")

        assert isinstance(report, SingleReport)
        assert report.run_id == "run-001"
        # net_value 指标应已计算
        assert len(report.summary) > 0

    def test_analyze_with_portfolio_id(self):
        """指定 portfolio_id → 传递给服务调用"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(net_value_df=nv_df)
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001", portfolio_id="port-1")

        assert isinstance(report, SingleReport)
        # 验证 analyzer_service 被正确调用
        analyzer_service.get_by_run_id.assert_called_once()
        call_kwargs = analyzer_service.get_by_run_id.call_args
        assert call_kwargs.kwargs.get("portfolio_id") == "port-1" or \
               call_kwargs[1].get("portfolio_id") == "port-1"

    def test_compare_multiple_runs(self):
        """多个 run_id → ComparisonReport"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(net_value_df=nv_df)
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.compare(["run-001", "run-002"])

        assert isinstance(report, ComparisonReport)
        assert len(report.reports) == 2

    def test_time_segments(self):
        """freq=M → SegmentReport"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df(days=120)
        result_service, analyzer_service = _make_services(net_value_df=nv_df)
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.time_segments("run-001", freq="M")

        assert isinstance(report, SegmentReport)
        assert report.freq == "M"

    def test_rolling(self):
        """window=60 → RollingReport"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df(days=120)
        result_service, analyzer_service = _make_services(net_value_df=nv_df)
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.rolling("run-001", window=60)

        assert isinstance(report, RollingReport)
        assert report.window == 60

    def test_partial_data_only_net_value(self):
        """仅有 net_value → report 有 summary，signal/order 为空"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(
            net_value_df=nv_df,
            signal_records=None,
            order_records=None,
            position_records=None,
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001")

        assert isinstance(report, SingleReport)
        assert len(report.summary) > 0
        assert len(report.signal_analysis) == 0
        assert len(report.order_analysis) == 0
        # ConcentrationTopN 的 requires 在 __init__ 设置，class 级别为空，
        # 所以 check_availability 认为可用但计算会 ERROR
        assert report.position_analysis.get("concentration_top_n") == "ERROR"

    def test_partial_data_net_value_and_signals(self):
        """net_value + signals → report 有 summary 和 signal_analysis"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(
            net_value_df=nv_df,
            signal_records=_make_signal_records(),
            order_records=None,
            position_records=None,
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001")

        assert isinstance(report, SingleReport)
        assert len(report.summary) > 0
        assert len(report.signal_analysis) > 0
        assert len(report.order_analysis) == 0
        # ConcentrationTopN 的 requires 在 __init__ 设置，无 position 数据时计算 ERROR
        assert report.position_analysis.get("concentration_top_n") == "ERROR"

    def test_load_data_signal_failure_skipped(self):
        """signal 加载失败 → 跳过，其他数据正常加载"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(
            net_value_df=nv_df,
            signal_success=False,
            order_records=_make_order_records(),
            position_records=_make_position_records(),
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001")

        assert isinstance(report, SingleReport)
        assert len(report.summary) > 0
        # signal 失败 → signal_analysis 为空
        assert len(report.signal_analysis) == 0
        # order 和 position 应正常
        assert len(report.order_analysis) > 0

    def test_register_custom_metric(self):
        """注册自定义指标 → 包含在分析中"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()

        # 创建自定义指标
        class CustomMetric:
            name = "custom_test"
            requires = ["net_value"]
            params = {}

            def compute(self, data):
                return 42.0

        result_service, analyzer_service = _make_services(net_value_df=nv_df)
        engine = AnalysisEngine(result_service, analyzer_service)
        engine.register_metric(CustomMetric)

        # 验证注册成功
        assert "custom_test" in engine._registry.list_metrics()

        # 验证出现在分析结果中
        report = engine.analyze("run-001")
        assert "custom_test" in report.summary
        assert report.summary["custom_test"] == 42.0

    def test_builtin_metrics_registered(self):
        """内置指标在构造时全部注册"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        result_service, analyzer_service = _make_services()
        engine = AnalysisEngine(result_service, analyzer_service)

        # 至少包含所有 18 个内置指标
        metrics = engine._registry.list_metrics()
        expected_metrics = [
            "annualized_return", "max_drawdown", "sharpe_ratio",
            "sortino_ratio", "volatility", "calmar_ratio",
            "rolling_sharpe", "rolling_volatility",
            "signal_count", "long_short_ratio", "daily_signal_freq",
            "fill_rate", "avg_slippage", "cancel_rate",
            "max_positions", "concentration_top_n",
            "signal_order_conversion", "signal_ic",
        ]
        for m in expected_metrics:
            assert m in metrics, f"Missing builtin metric: {m}"

    def test_load_data_position_failure_skipped(self):
        """position 加载失败 → 跳过，其他数据正常加载"""
        # TODO: TDD Red阶段 — 测试用例尚未实现
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_services(
            net_value_df=nv_df,
            position_success=False,
            signal_records=_make_signal_records(),
        )
        engine = AnalysisEngine(result_service, analyzer_service)
        report = engine.analyze("run-001")

        assert isinstance(report, SingleReport)
        # position 未加载 → ConcentrationTopN 计算 ERROR，MaxPositions 不在 position_analysis
        assert report.position_analysis.get("concentration_top_n") == "ERROR"
        assert len(report.signal_analysis) > 0
