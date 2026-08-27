# Issue: 回测 /positions 返回的是持仓变更流水，序列化曾按持仓快照计算
# Upstream: api.api.backtest.get_backtest_positions → BacktestTaskService.list_positions
# Downstream: ResultService.get_positions（CH position_record，volume 为带符号 delta）
# Role: 契约——SELL 行盈亏符号、市值非负、timestamp 用事件时间

"""
持仓流水序列化语义测试

修复的三个缺陷（读时计算层，一处修复旧数据即刻受益）：
1. profit 符号反：SELL 行 volume<0，直接 (price-cost)*volume 会把亏损算成盈利
2. market_value 负市值：price*volume 对 SELL 行得出负数
3. timestamp 全为写入时刻：CH 记录的 timestamp 是回测结束落库时间，
   事件时间在 business_timestamp，主显字段应优先后者
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService


def _make_service():
    """绕过 __init__（需 crud_repo 依赖），直接构造实例 + stub _resolve_task_id。"""
    svc = object.__new__(BacktestTaskService)
    svc._resolve_task_id = lambda uuid: ("task-1", "pf-1", None)
    return svc


_DEFAULT_TS = object()  # 哨兵：区分「未传」与「显式传 None」（缺失场景）


def _make_flow(cost=12.06, volume=-2000, price=11.4, fee=5,
               business_timestamp=_DEFAULT_TS, write_timestamp=_DEFAULT_TS):
    """构造一条 CH 持仓变更流水记录（volume 带符号：卖出为负）。"""
    p = MagicMock()
    p.uuid = "p1"; p.portfolio_id = "pf"; p.engine_id = "e"; p.task_id = "t"
    p.code = "000001.SZ"; p.cost = cost; p.volume = volume
    p.frozen_volume = 0; p.price = price; p.fee = fee
    p.direction = 2 if volume < 0 else 1
    p.business_timestamp = datetime(2025, 9, 19) if business_timestamp is _DEFAULT_TS else business_timestamp
    p.timestamp = datetime(2026, 8, 16, 22, 25, 10) if write_timestamp is _DEFAULT_TS else write_timestamp
    return p


def _run(svc, flows):
    mock_rs = MagicMock()
    mock_rs.get_positions.return_value = MagicMock(
        is_success=lambda: True, data={"data": flows, "total": len(flows)}
    )
    with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
        return svc.list_positions("x")


class TestSellFlowProfit:
    def test_sell_loss_is_negative(self):
        """清仓亏损：cost 12.06 卖 11.4 × 2000 股 → -1320-fee（旧实现 +1315）"""
        item = _run(_make_service(), [_make_flow(volume=-2000)]).data[0]
        assert item.profit == pytest.approx((11.4 - 12.06) * 2000 - 5)

    def test_sell_market_value_non_negative(self):
        """市值按变更规模计（price*|volume|），不得为负"""
        item = _run(_make_service(), [_make_flow(volume=-2000)]).data[0]
        assert item.market_value == pytest.approx(11.4 * 2000)
        assert item.market_value >= 0

    def test_sell_profit_pct_non_zero(self):
        """旧实现 cost_basis=cost*volume<0 被守卫吞成 0，修正后应有值"""
        item = _run(_make_service(), [_make_flow(volume=-2000)]).data[0]
        assert item.profit_pct == pytest.approx(((11.4 - 12.06) * 2000 - 5) / (12.06 * 2000))

    def test_buy_profit_is_none(self):
        """BUY 行无盈亏语义(2026-08-17 定稿):cost=成交后加权均价,
        (price-cost)*vol 是均价漂移残差(首仓=-fee、加仓=无含义偏离),
        profit/profit_pct 恒 None 供前端显示 '-'"""
        item = _run(_make_service(), [_make_flow(volume=1000, cost=12.06, price=12.06)]).data[0]
        assert item.profit is None
        assert item.profit_pct is None

    def test_buy_add_position_profit_is_none(self):
        """加仓行同无盈亏:新均价被本笔拉偏,数值无金融语义"""
        item = _run(_make_service(), [_make_flow(volume=1000, cost=11.0, price=12.0)]).data[0]
        assert item.profit is None
        assert item.profit_pct is None


class TestTimestampUsesEventTime:
    def test_timestamp_prefers_business_timestamp(self):
        """主显时间应为事件时间（business_timestamp），非写入时刻"""
        item = _run(_make_service(), [_make_flow()]).data[0]
        assert item.timestamp.startswith("2025-09-19")
        assert not item.timestamp.startswith("2026-08-16")

    def test_falls_back_to_write_time_when_business_missing(self):
        """business_timestamp 缺失时回退写入时刻，不得为空"""
        item = _run(_make_service(), [_make_flow(business_timestamp=None)]).data[0]
        assert item.timestamp.startswith("2026-08-16")
