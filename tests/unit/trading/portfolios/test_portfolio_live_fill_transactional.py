"""
PortfolioLive.on_order_partially_filled fill 应用事务性测试 (#6741)

验证 snapshot-restore 保证 fill 应用原子性：
- AC1: LONG 分支 deduct_from_frozen 异常 → 全回滚 + CRITICAL + re-raise
- AC2: pos.deal 异常 → _positions 深拷贝回滚生效（浅拷贝实现必败）
- AC3: SHORT 分支异常 → 全回滚 + CRITICAL + re-raise
- AC4: 正常路径行为不变
- AC5: re-raise 不崩 worker（PortfolioProcessor 主循环兜底）
- AC6: SHORT 无持仓（pos None）→ raise + 全回滚（修正原静默 ERROR 半应用资金）
"""
import sys
import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.entities.order import Order
from ginkgo.entities.position import Position
from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


def _make_portfolio(name="Portfolio", **kwargs):
    p = PortfolioLive(name=name, use_default_analyzers=False, **kwargs)
    # ContextMixin 的 engine_id/task_id 由 _context 提供（LONG 分支创建 Position 需非空）
    mock_ctx = Mock()
    mock_ctx.engine_id = "eid"
    mock_ctx.task_id = "rid"
    mock_ctx.portfolio_id = p.uuid
    p._context = mock_ctx
    return p


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=Decimal("10.0"), **overrides):
    defaults = dict(
        portfolio_id="pid", engine_id="eid", task_id="rid",
        code=code, direction=direction, order_type=ORDER_TYPES.LIMITORDER,
        status=ORDERSTATUS_TYPES.NEW, volume=volume,
        limit_price=limit_price, frozen_money=volume * limit_price,
    )
    defaults.update(overrides)
    return Order(**defaults)


def _make_fill_event(order, filled_quantity=100, fill_price=Decimal("10.0"),
                     commission=Decimal("5"), portfolio_id="pid"):
    return EventOrderPartiallyFilled(
        order=order, filled_quantity=filled_quantity,
        fill_price=fill_price, commission=commission,
        portfolio_id=portfolio_id, engine_id="eid", task_id="rid",
    )


@pytest.mark.unit
@pytest.mark.live
class TestFillTransactional:
    """fill 应用事务性：异常全回滚 + CRITICAL + re-raise。"""

    def test_long_deduct_from_frozen_failure_full_rollback(self):
        """AC1: LONG deduct_from_frozen 抛异常 → 全回滚 + CRITICAL + raise。

        settle 已先执行改 order 状态，回滚须还原 order 成交字段。
        """
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        order = _make_order(portfolio_id=p.uuid)

        entry_cash = p.cash
        entry_frozen = p.frozen
        entry_fee = p.fee
        entry_tv = order.transaction_volume
        entry_remain = order.remain

        with patch.object(p, 'deduct_from_frozen',
                          side_effect=ValueError("Insufficient frozen funds")), \
             patch('ginkgo.trading.portfolios.portfolio_live.GLOG') as mock_glog, \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            with pytest.raises(ValueError):
                p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        # 全回滚：settle 已改 order，必须还原
        assert p.cash == entry_cash
        assert p.frozen == entry_frozen
        assert p.fee == entry_fee
        assert order.transaction_volume == entry_tv
        assert order.remain == entry_remain
        # CRITICAL 告警（非静默 ERROR）
        assert mock_glog.CRITICAL.called

    def test_pos_deal_failure_positions_deepcopied(self):
        """AC2: pos.deal 改 position 后抛异常 → _positions 深拷贝回滚（浅拷贝必败）。"""
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", task_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
        )
        p.add_position(pos)
        entry_pos_volume = pos.volume
        entry_pos_cost = pos.cost

        order = _make_order(portfolio_id=p.uuid)

        original_deal = pos.deal

        def deal_mutate_then_explode(*args, **kwargs):
            original_deal(*args, **kwargs)  # 真实 _bought 原地改 position 对象
            raise RuntimeError("deal exploded after mutation")

        with patch.object(pos, 'deal', side_effect=deal_mutate_then_explode), \
             patch('ginkgo.trading.portfolios.portfolio_live.GLOG') as mock_glog, \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            with pytest.raises(RuntimeError):
                p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        # 深拷贝回滚：portfolio 持有入口快照副本，position 内容回入口值
        restored = p.get_position("000001.SZ")
        assert restored is not pos
        assert restored.volume == entry_pos_volume
        assert restored.cost == entry_pos_cost
        assert mock_glog.CRITICAL.called

    def test_short_add_cash_failure_full_rollback(self):
        """AC3: SHORT 分支 add_cash 抛异常 → 全回滚 + CRITICAL + raise。"""
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", task_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
        )
        p.add_position(pos)
        order = _make_order(direction=DIRECTION_TYPES.SHORT, portfolio_id=p.uuid)

        entry_cash = p.cash
        entry_fee = p.fee
        entry_tv = order.transaction_volume

        with patch.object(p, 'add_cash', side_effect=RuntimeError("add_cash exploded")), \
             patch('ginkgo.trading.portfolios.portfolio_live.GLOG') as mock_glog, \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            with pytest.raises(RuntimeError):
                p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        assert p.cash == entry_cash
        assert p.fee == entry_fee
        assert order.transaction_volume == entry_tv
        assert mock_glog.CRITICAL.called

    def test_short_no_position_raises_and_rolls_back(self):
        """AC6: SHORT 无持仓（pos None）→ raise + 全回滚 + CRITICAL。

        SHORT 收到 fill 但无持仓属业务异常：add_cash/add_fee 已执行，须被事务回滚，
        CRITICAL + re-raise，不再静默 ERROR 半应用资金（#6739 审计 flag）。
        """
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        # 故意不建 SHORT 持仓 → get_position 返回 None
        order = _make_order(direction=DIRECTION_TYPES.SHORT, portfolio_id=p.uuid)

        entry_cash = p.cash
        entry_fee = p.fee
        entry_tv = order.transaction_volume

        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG') as mock_glog, \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            with pytest.raises(ValueError, match="no position found"):
                p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        # add_cash(proceeds)/add_fee(fee) 已执行但被 snapshot-restore 回滚
        assert p.cash == entry_cash
        assert p.fee == entry_fee
        assert order.transaction_volume == entry_tv  # settle 改的也被回滚
        assert mock_glog.CRITICAL.called

    def test_normal_fill_long_behavior_unchanged(self):
        """AC4: 正常路径无异常 → fill 应用行为与改前一致（事务机制不改变正常语义）。"""
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        order = _make_order(portfolio_id=p.uuid)

        entry_fee = p.fee

        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        # position 创建 + 加仓
        assert "000001.SZ" in p.positions
        assert p.positions["000001.SZ"].volume == 100
        # order 成交累计
        assert order.transaction_volume == 100
        # fee 累加
        assert p.fee == entry_fee + Decimal("5")
        # is_final（qty=volume）→ release_frozen 清零 remain
        assert order.remain == Decimal("0")

    def test_reraise_does_not_crash_worker(self):
        """AC5: re-raise 经 _route_event 内层 except + 主循环兜底，worker 不退出。

        构造 PortfolioProcessor（mock Kafka），注入会抛异常的 fill 事件，
        断言：主循环处理完异常事件后继续处理下一事件（continue）、is_running 仍 True
        （worker 存活）、该 fill 被 CRITICAL 记录、fill 状态全回滚。
        """
        import time as _time
        from queue import Queue
        from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor

        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        order = _make_order(portfolio_id=p.uuid)
        entry_tv = order.transaction_volume

        in_q = Queue()
        out_q = Queue()

        with patch.object(p, 'deduct_from_frozen', side_effect=ValueError("Insufficient frozen funds")), \
             patch('ginkgo.workers.execution_node.portfolio_processor.GinkgoConsumer', MagicMock()), \
             patch('ginkgo.workers.execution_node.portfolio_processor.GCONF', MagicMock()), \
             patch('ginkgo.workers.execution_node.portfolio_processor.KafkaTopics', MagicMock()), \
             patch('ginkgo.trading.portfolios.portfolio_live.GLOG') as mock_live_glog, \
             patch('ginkgo.workers.execution_node.portfolio_processor.GLOG', MagicMock()):
            proc = PortfolioProcessor(p, in_q, out_q)
            proc._control_consumer = None  # 禁 Kafka poll，_process_control_commands 直接 return
            proc.start()
            try:
                # 注入两笔会抛异常的 fill（on_order_partially_filled → 回滚 + CRITICAL + re-raise）
                in_q.put(_make_fill_event(order, portfolio_id=p.uuid))
                in_q.put(_make_fill_event(order, portfolio_id=p.uuid))

                # 等主循环处理完两笔（轮询 processed_count，超时 3s 兜底）
                deadline = _time.time() + 3.0
                while _time.time() < deadline and proc.processed_count < 2:
                    _time.sleep(0.01)

                # 主循环 continue：两笔异常事件都被路由处理（_route_event 吞 re-raise）
                assert proc.processed_count >= 2
                # worker 存活：is_running 仍 True（主循环外层 except 兜底，未退出）
                assert proc.is_running is True
                # 该 fill 被 portfolio_live 层 CRITICAL 记录（非静默 ERROR）
                assert mock_live_glog.CRITICAL.called
                # 事务回滚生效：order 成交字段未被两笔失败 fill 污染
                assert order.transaction_volume == entry_tv
            finally:
                proc.stop()
                proc.join(timeout=2.0)

    def test_short_fill_clears_flat_position(self):
        """AC7: SHORT 有持仓全部成交 → clean_positions 移除空持仓 + cash 到账。

        覆盖 BUG-1 自然路径（不 mock 任何方法）：position 已冻结待卖（frozen_volume=100，
        volume=0），SHORT fill 100 股 → _sold 清空 frozen → total_position=0 →
        clean_positions 删除该 position。修复前此处抛 AttributeError 触发全回滚，
        券商卖了票但 cash 未到账、position 未清理；修复后 fill 正常落地。
        """
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        # 模拟下单冻结后的 position：volume 已转 frozen_volume（_sold 只减 frozen）
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", task_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=0, frozen_volume=100,
        )
        p.add_position(pos)
        order = _make_order(
            direction=DIRECTION_TYPES.SHORT, volume=100, portfolio_id=p.uuid,
        )

        entry_cash = p.cash

        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            p.on_order_partially_filled(_make_fill_event(order, portfolio_id=p.uuid))

        # proceeds = 10*100 - 5 = 995 到账（无回滚）
        assert p.cash == entry_cash + Decimal("995")
        # 空持仓被 clean_positions 移除
        assert "000001.SZ" not in p.positions
        # order 成交累计
        assert order.transaction_volume == 100

    def test_short_partial_fill_keeps_residual_position(self):
        """AC8: SHORT 部分成交（有残留）→ position 保留，frozen_volume 正确扣减。

        frozen_volume=100 卖 30 → 残留 frozen_volume=70，total_position=70 > 0，
        clean_positions 不移除。证明清理条件精确（仅清完全平仓），不误删残留持仓。
        """
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", task_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=0, frozen_volume=100,
        )
        p.add_position(pos)
        order = _make_order(
            direction=DIRECTION_TYPES.SHORT, volume=100, portfolio_id=p.uuid,
        )

        entry_cash = p.cash

        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            p.on_order_partially_filled(
                _make_fill_event(order, filled_quantity=30, portfolio_id=p.uuid)
            )

        # proceeds = 10*30 - 5 = 295 到账
        assert p.cash == entry_cash + Decimal("295")
        # 残留持仓保留，frozen_volume 扣减到 70
        assert "000001.SZ" in p.positions
        assert p.positions["000001.SZ"].frozen_volume == 70
        assert order.transaction_volume == 30
