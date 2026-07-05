"""
BacktestFeeder 端到端：advance_time 的 emit 经 FeederPublishMixin.publish_price_update

验证 BacktestFeeder 装 EngineBindableMixin+FeederPublishMixin 后 MRO 链通：
advance_time 内 emit 走 publish_price_update → publish_event → engine.put，
成功投递计 stats['events_published']。

#6587 重构后 advance_time 取数从单股 _generate_price_events 改为批量
_compute_feedable_codes（∩ available）+ _fetch_day_bars_batch（code=None 全市场）。
本契约测试 mock 经 public collaborator bar_service（DI seam）让新路径产出当日 bar，
验证 emit 经 publish seam 投递并计数——不 mock feeder 内部方法（实现细节，重构即坏）。
"""
from datetime import datetime
from unittest.mock import Mock, patch

import ginkgo.data.mappers as mappers_mod
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.time.providers import LogicalTimeProvider


def _make_bar(code: str) -> Bar:
    """构造真实 Bar entity（避免 mock 导致 EventPriceUpdate 构造失败）。"""
    return Bar(
        code=code,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        volume=10000,
        amount=1000000.0,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=datetime(2023, 6, 1, 9, 30),
    )


class TestBacktestFeederEmitsViaPublishPriceUpdate:
    def test_advance_time_routes_emit_to_engine_put_and_counts(self):
        """advance_time emit 经 publish_price_update 投递到 engine.put 并计 events_published。

        BacktestFeeder 已继承 EngineBindableMixin；装 FeederPublishMixin 后，
        set_event_publisher 注入 _engine_put，advance_time 内构造 EventPriceUpdate
        → publish_price_update → publish_event → _engine_put(event)。
        端到端验证 MRO 链通 + 投递 + 计数。

        mock 经 public collaborator bar_service（DI）让 #6587 重构后的批量取数路径
        产出当日 bar；不 mock feeder 内部方法（实现细节，重构即坏）。
        """
        feeder = BacktestFeeder()
        feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
        captured: list = []
        feeder.set_event_publisher(captured.append)
        feeder._interested_codes = ["X.SZ"]

        # mock bar_service（DI seam）让新取数路径产出当日 X.SZ bar：
        #   get_available_codes 返 ["X.SZ"]（_compute_feedable_codes 交集非空）
        #   get(code=None, ...) 返 ModelList（_fetch_day_bars_batch 批量取当日 bar）
        bar_x = _make_bar("X.SZ")
        mock_bs = Mock()
        mock_bs.get_available_codes.return_value = ServiceResult(
            success=True, data=["X.SZ"]
        )
        feeder.bar_service = mock_bs

        with patch.object(
            mappers_mod.BarMapper, "from_models", return_value=[bar_x]
        ):
            feeder.advance_time(datetime(2023, 6, 1, 9, 30, 0))

        # emit 经 publish_price_update 投递到 engine.put
        assert len(captured) == 1, "emit 应经 publish_price_update 投递到 engine.put"
        assert isinstance(captured[0], EventPriceUpdate)
        assert captured[0].payload is bar_x, "投递的应是当日 bar 包成的 EventPriceUpdate"
        assert captured[0].source == SOURCE_TYPES.BACKTESTFEEDER
        assert feeder.stats["events_published"] == 1
