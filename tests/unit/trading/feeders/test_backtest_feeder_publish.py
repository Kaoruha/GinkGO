"""
BacktestFeeder 端到端：advance_time 的 emit 经 FeederPublishMixin.publish_price_update

验证 BacktestFeeder 装 EngineBindableMixin+FeederPublishMixin 后 MRO 链通：
advance_time 内 emit 走 publish_price_update → publish_event → engine.put，
成功投递计 stats['events_published']。mock _generate_price_events 避开 DB。
"""
from datetime import datetime
from unittest.mock import Mock

from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestBacktestFeederEmitsViaPublishPriceUpdate:
    def test_advance_time_routes_emit_to_engine_put_and_counts(self):
        """advance_time emit 经 publish_price_update 投递到 engine.put 并计 events_published。

        BacktestFeeder 已继承 EngineBindableMixin；装 FeederPublishMixin 后，
        set_event_publisher 注入 _engine_put，advance_time 内 publish_price_update
        → publish_event → _engine_put(event)。端到端验证 MRO 链通 + 统计计数。
        """
        feeder = BacktestFeeder()
        feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
        captured: list = []
        feeder.set_event_publisher(captured.append)
        feeder._interested_codes = ["X.SZ"]
        event = Mock(name="price_event")
        feeder._generate_price_events = lambda code, t: [event]  # 避开 DB

        feeder.advance_time(datetime(2023, 6, 1, 9, 30, 0))

        assert captured == [event], "emit 应经 publish_price_update 投递到 engine.put"
        assert feeder.stats["events_published"] == 1
