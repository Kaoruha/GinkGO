"""
性能: 单文件秒级, 覆盖 avg_holding_period 业务时间修复(#G1)
"""

import unittest
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

from ginkgo.trading.analysis.analyzers.avg_holding_period import AvgHoldingPeriod
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class FakePosition:
    """鸭子类型持仓:只提供分析器用到的字段"""

    def __init__(self, total_position=0, business_timestamp=None, init_time=None):
        self.uuid = str(uuid_lib.uuid4())
        self.total_position = total_position
        self.business_timestamp = business_timestamp
        self.init_time = init_time


class TestAvgHoldingPeriod(unittest.TestCase):
    """
    测试平均持仓周期分析器
    """

    def setUp(self):
        self.analyzer = AvgHoldingPeriod("test_avg_holding")
        self.test_time = datetime(2024, 1, 1, 15, 0, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_avg_holding_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _info(self, positions, now):
        return {"now": now, "positions": positions}

    def test_init(self):
        """测试初始化"""
        analyzer = AvgHoldingPeriod()
        self.assertEqual(analyzer._name, "avg_holding_period")
        self.assertEqual(analyzer.avg_days, 0.0)
        self.assertEqual(analyzer.total_trades, 0)
        self.assertIn(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, analyzer.active_stage)
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_no_time_no_op(self):
        """now/current_time 缺失时安全返回"""
        self.analyzer.activate(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, {"positions": {}})
        self.assertEqual(self.analyzer.total_trades, 0)

    def test_regression_aware_now_naive_init(self):
        """回归: aware now(引擎 LogicalTimeProvider UTC) - naive init_time(墙钟)
        修复前抛 TypeError 被上层吞掉, 恒 0"""
        naive_init = datetime(2024, 1, 1, 9, 30, 0)  # 模拟 TimeMixin 墙钟
        pos = FakePosition(total_position=0, business_timestamp=None, init_time=naive_init)
        now = datetime(2024, 1, 31, 15, 0, 0, tzinfo=timezone.utc)  # 模拟 provider.now()

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertEqual(self.analyzer.total_trades, 1)
        self.assertEqual(self.analyzer.avg_days, 30.0)

    def test_business_timestamp_preferred_over_init_time(self):
        """业务时间优先: business_timestamp 是回测时钟, init_time 是现实墙钟"""
        real_wall_clock = datetime(2026, 8, 15, 10, 0, 0)  # 回测进程运行时刻
        biz_open = datetime(2024, 1, 10, 9, 30, 0)
        pos = FakePosition(total_position=0, business_timestamp=biz_open, init_time=real_wall_clock)
        now = datetime(2024, 1, 20, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        # 应按业务时间算 10 天, 而非墙钟差(负数)
        self.assertEqual(self.analyzer.avg_days, 10.0)

    def test_aware_both_sides(self):
        """两侧均 tz-aware 时同样可算"""
        start = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        pos = FakePosition(total_position=0, business_timestamp=start)
        now = datetime(2024, 1, 4, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertEqual(self.analyzer.avg_days, 3.0)

    def test_same_day_close_counts_as_one_day(self):
        """同日开平 delta=0 → max(delta, 1) 兜成 1 天"""
        day = datetime(2024, 1, 5, 9, 30, 0)
        pos = FakePosition(total_position=0, business_timestamp=day)
        now = datetime(2024, 1, 5, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertEqual(self.analyzer.avg_days, 1.0)

    def test_open_position_not_counted(self):
        """未平仓(total_position > 0)不计"""
        pos = FakePosition(total_position=1000, business_timestamp=datetime(2024, 1, 1))
        now = datetime(2024, 2, 1, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertEqual(self.analyzer.total_trades, 0)
        self.assertEqual(self.analyzer.avg_days, 0.0)

    def test_no_duplicate_counting(self):
        """同一持仓(清仓后仍留在快照里)只计一次"""
        pos = FakePosition(total_position=0, business_timestamp=datetime(2024, 1, 1))
        now = datetime(2024, 1, 11, 15, 0, 0, tzinfo=timezone.utc)

        for _ in range(3):
            self.analyzer.activate(
                RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
            )
        self.assertEqual(self.analyzer.total_trades, 1)
        self.assertEqual(self.analyzer.avg_days, 10.0)

    def test_multiple_positions_average(self):
        """多笔持仓取平均: 10 天与 30 天 → 20 天"""
        p1 = FakePosition(total_position=0, business_timestamp=datetime(2024, 1, 1))
        p2 = FakePosition(total_position=0, business_timestamp=datetime(2024, 1, 21))
        now = datetime(2024, 1, 31, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED,
            self._info({p1.uuid: p1, p2.uuid: p2}, now),
        )
        self.assertEqual(self.analyzer.total_trades, 2)
        self.assertEqual(self.analyzer.avg_days, 20.0)

    def test_none_start_skipped(self):
        """business_timestamp 与 init_time 均为 None 时跳过不崩"""
        pos = FakePosition(total_position=0, business_timestamp=None, init_time=None)
        now = datetime(2024, 1, 31, 15, 0, 0, tzinfo=timezone.utc)

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertEqual(self.analyzer.total_trades, 0)

    def test_data_recorded_via_add_data(self):
        """activate 后数据进 data 序列(ENDDAY record 可落库的前提)"""
        pos = FakePosition(total_position=0, business_timestamp=datetime(2024, 1, 1))
        now = datetime(2024, 1, 6, 15, 0, 0, tzinfo=timezone.utc)
        self.analyzer.advance_time(now.replace(tzinfo=None))

        self.analyzer.activate(
            RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self._info({pos.uuid: pos}, now)
        )
        self.assertGreater(len(self.analyzer.data), 0)


if __name__ == '__main__':
    unittest.main()
