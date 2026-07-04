# Upstream: BacktestFeeder, bar_service.get_available_codes, BarMapper
# Downstream: -
# Role: #6586 验证无数据 code 过滤下沉到 feeder（预过滤 + 批量取 bar + WARN 去重）
"""
BacktestFeeder 预过滤 / 批量 / WARN 去重测试（#6586）。

把"剔除 DB 中无 bar 数据的 code"从 selector 下沉到 feeder：
  - feeder 喂数据前用 bar_service.get_available_codes 与 _interested_codes 取交集
  - 按日批量取当日复权 bar（一次查询，消除逐股 N+1）
  - 同一 code 的 "No bar data" WARN 在整个回测内至多一次
"""
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

import ginkgo.data.mappers as mappers_mod
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.time.providers import LogicalTimeProvider


def _make_bar(code: str, day: int = 1) -> Bar:
    """构造真实 Bar entity（避免 mock 导致 EventPriceUpdate 构造失败）。"""
    return Bar(
        code=code,
        open=100.0 + day,
        high=101.0 + day,
        low=99.0 + day,
        close=100.0 + day,
        volume=10000,
        amount=1000000.0,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=datetime(2023, 6, day, 9, 30),
    )


@pytest.mark.unit
@pytest.mark.backtest
class TestBacktestFeederPrefilter:
    """#6586：无数据 code 过滤下沉到 feeder。"""

    def test_advance_time_drops_codes_without_bar_data(self):
        """interested 含全无数据 code（不在 get_available_codes）时，feeder 预过滤剔除它：
        不为其发事件；当日 bar 走批量查询（bar_service.get 全市场一次），非逐股 N+1。"""
        feeder = BacktestFeeder()
        feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
        feeder._interested_codes = ["A.SZ", "NODATA.SZ"]

        mock_bs = Mock()
        # 只有 A 在 DB 有 bar 数据，NODATA 被预过滤剔除
        mock_bs.get_available_codes.return_value = ServiceResult(
            success=True, data=["A.SZ"]
        )
        feeder.bar_service = mock_bs

        captured: list = []
        feeder.set_event_publisher(captured.append)

        bar_a = _make_bar("A.SZ")
        with patch.object(mappers_mod.BarMapper, "from_models", return_value=[bar_a]):
            feeder.advance_time(datetime(2023, 6, 1, 9, 30))

        # 只为 A 发事件，NODATA 被预过滤剔除不发事件
        assert len(captured) == 1, "NODATA 应被预过滤剔除，只为 A 发事件"
        assert isinstance(captured[0], EventPriceUpdate)
        assert captured[0].source == SOURCE_TYPES.BACKTESTFEEDER
        # 批量取 bar：bar_service.get 一次（code=None 全市场当日），非逐股 N 次
        assert mock_bs.get.call_count == 1, "应批量取 bar 一次，非逐股 N+1"
        _args, kwargs = mock_bs.get.call_args
        assert kwargs.get("code") is None, "批量取 bar 应传 code=None（全市场当日复权）"

    def test_warn_no_data_deduplicated_across_days(self):
        """feedable code 当日无 bar（停牌等）时，跨多日 advance_time 该 code 的
        No-bar WARN 整个回测内至多一次（#6586 刷屏根因）。"""
        feeder = BacktestFeeder()
        feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
        feeder._interested_codes = ["A.SZ"]

        mock_bs = Mock()
        # A 在 DB 有数据（进 feedable），但当日批量查询返回空（停牌）
        mock_bs.get_available_codes.return_value = ServiceResult(
            success=True, data=["A.SZ"]
        )
        mock_bs.get.return_value = ServiceResult(success=True, data=[])
        feeder.bar_service = mock_bs

        captured: list = []
        feeder.set_event_publisher(captured.append)

        # 跨 3 个交易日推进，每日 A 都"无当日 bar"
        for day in (1, 2, 3):
            feeder.advance_time(datetime(2023, 6, day, 9, 30))

        # 3 日均无当日 bar，但 WARN 去重：_warned_no_data 只记 A 一次
        assert feeder._warned_no_data == {"A.SZ"}, (
            "同一 code 整个回测内 WARN 至多一次，跨日不重复"
        )
        # 无 bar 不发事件
        assert captured == []

    def test_fallback_to_all_interested_when_available_codes_unavailable(self):
        """get_available_codes 失败时，feeder 降级为全 interested 喂数据，不阻断回测。"""
        feeder = BacktestFeeder()
        feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
        feeder._interested_codes = ["A.SZ", "B.SZ"]

        mock_bs = Mock()
        # available 查询失败 → 降级为全 interested（A、B 都喂）
        mock_bs.get_available_codes.return_value = ServiceResult(success=False, error="db down")
        bar_a = _make_bar("A.SZ")
        bar_b = _make_bar("B.SZ")
        feeder.bar_service = mock_bs

        captured: list = []
        feeder.set_event_publisher(captured.append)

        with patch.object(
            mappers_mod.BarMapper, "from_models", return_value=[bar_a, bar_b]
        ):
            feeder.advance_time(datetime(2023, 6, 1, 9, 30))

        # 降级后 A、B 都被喂数据（不因 available 查询失败而阻断）
        assert len(captured) == 2, "available 失败应降级为全 interested，不阻断回测"


