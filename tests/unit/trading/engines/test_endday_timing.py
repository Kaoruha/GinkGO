# Upstream: TimeControlledEventEngine._handle_time_advance_event（ENDDAY 上提至引擎层）
# Downstream: PortfolioBase.end_day（D 日日终入口）
# Role: ENDDAY 触发时机回归 — 推时钟前触发、时钟=old_time(D)、每交易日一次、模式守卫
"""
ENDDAY 触发时机（引擎层日终）测试

原缺陷：ENDDAY 钩子在 t1backtest.advance_time 内触发，位于引擎 set_current_time(D+1)
与 D+1 价格重标记之后 → 分析器记录戳晚一天、worth=D 账本×D+1 价混合体。
修复：引擎在 _handle_time_advance_event 推时钟**前**调用 portfolio.end_day()。
"""

import datetime

import pytest

from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.time.providers import LogicalTimeProvider

D = datetime.datetime(2024, 1, 2, 9, 31)          # 交易日 D 开盘
NEXT_D = datetime.datetime(2024, 1, 3, 9, 31)     # 交易日 D+1 开盘
INTRADAY = datetime.datetime(2024, 1, 2, 10, 31)  # 同日盘中
PRE_CLOSE = datetime.datetime(2024, 1, 2, 14, 59)
POST_CLOSE = datetime.datetime(2024, 1, 2, 15, 1)
EVENING = datetime.datetime(2024, 1, 2, 15, 30)


class FakePortfolio:
    """鸭子类型 portfolio：只提供 end_day，记录触发时的共享时钟"""

    def __init__(self, name: str = "fake_portfolio"):
        self.name = name
        self.engine = None
        self.fired_at = []

    def end_day(self) -> None:
        self.fired_at.append(self.engine._time_provider.now())


def _make_engine(portfolios, mode: EXECUTION_MODE = EXECUTION_MODE.BACKTEST,
                 initial_time: datetime.datetime = D) -> TimeControlledEventEngine:
    engine = TimeControlledEventEngine(name="test_endday_engine", mode=mode)
    engine._time_provider = LogicalTimeProvider(initial_time)
    engine._portfolios = list(portfolios)
    for p in portfolios:
        p.engine = engine
    return engine


@pytest.mark.unit
@pytest.mark.backtest
class TestEnddayTiming:
    """ENDDAY 触发时机测试"""

    def test_cross_day_fires_before_clock_advance(self):
        """跨日推进：end_day 触发且触发时共享时钟仍为 D（非 D+1）"""
        p = FakePortfolio()
        engine = _make_engine([p])

        engine._handle_time_advance_event(EventTimeAdvance(NEXT_D))

        assert len(p.fired_at) == 1, "end_day 应恰触发一次"
        assert p.fired_at[0].replace(tzinfo=None) == D, "触发时共享时钟应仍为 D"
        assert engine._time_provider.now().replace(tzinfo=None) == NEXT_D

    def test_same_day_advance_does_not_fire(self):
        """同日盘中推进：不触发日终"""
        p = FakePortfolio()
        engine = _make_engine([p])

        engine._handle_time_advance_event(EventTimeAdvance(INTRADAY))

        assert p.fired_at == []

    def test_minute_crossing_close_fires_once(self):
        """分钟级跨 15:00 收盘触发一次；随后同日跨夜不重复触发（每交易日一次）"""
        p = FakePortfolio()
        engine = _make_engine([p], initial_time=PRE_CLOSE)

        engine._handle_time_advance_event(EventTimeAdvance(POST_CLOSE))  # 跨收盘 → D 日终
        engine._handle_time_advance_event(EventTimeAdvance(EVENING))     # 盘后同日 → 不触发
        engine._handle_time_advance_event(EventTimeAdvance(NEXT_D))      # 跨夜但旧日已日终 → 不触发

        assert len(p.fired_at) == 1
        assert p.fired_at[0].replace(tzinfo=None) == PRE_CLOSE

    def test_live_mode_does_not_fire(self):
        """LIVE 墙钟心跳跨日不触发（LIVE 日终走预留事件化体系）"""
        p = FakePortfolio()
        engine = _make_engine([p], mode=EXECUTION_MODE.LIVE)

        engine._handle_time_advance_event(EventTimeAdvance(NEXT_D))

        assert p.fired_at == []

    def test_paper_mode_fires(self):
        """PAPER 走逻辑时钟驱动，保留每日记录（与 advance_time_to 模式集一致）"""
        p = FakePortfolio()
        engine = _make_engine([p], mode=EXECUTION_MODE.PAPER)

        engine._handle_time_advance_event(EventTimeAdvance(NEXT_D))

        assert len(p.fired_at) == 1
        assert p.fired_at[0].replace(tzinfo=None) == D

    def test_all_portfolios_called(self):
        """多 portfolio 挂载时逐一触发"""
        p1, p2 = FakePortfolio("pf1"), FakePortfolio("pf2")
        engine = _make_engine([p1, p2])

        engine._handle_time_advance_event(EventTimeAdvance(NEXT_D))

        assert len(p1.fired_at) == 1 and len(p2.fired_at) == 1
