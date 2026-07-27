# Upstream: src/ginkgo/workers/execution_node/node.py (_consume_order_feedback)
# Role: review #6778 问题③ — partial fill 多笔回报不能 pop 注册表

"""review #6778 问题③: partial fill 多笔回报不能 pop 注册表。

真实 broker 常分多笔回报 (如 1000 手拆 500+300+200)。旧代码
``_pending_orders.pop(dto.order_id)`` 在第一笔就移除 entry → 第二笔 pop
返回 None → GLOG.ERROR 丢弃 → 持仓错账。正确性被钉死在"gateway 必须一发完"。

修法: 累积 filled 量, 仅最终 filled (累积 >= volume) 才 pop, 中间笔保留 entry。
累积计数与 Order 同存一个 dict value ``[order, cumulative]`` (避免双注册表孤儿),
不改原 Order (避免污染已路由 event 的 remaining, 也避免越界碰 Order 的资金语义 settle)。
"""

from pathlib import Path
import sys

import pytest

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDERSTATUS_TYPES
from ginkgo.interfaces.dtos import OrderFeedbackDTO


def _make_node_pending_only() -> ExecutionNode:
    """构造仅含 pending 注册表的 ExecutionNode (跳过 Kafka/Redis init 副作用)。"""
    node = object.__new__(ExecutionNode)
    node._pending_orders = {}  # value = [Order, cumulative_filled] (单 dict, review #6778 问题③)
    node.node_id = "test-node"
    return node


def _dto(order_id: str, filled: float, price: str = "10.0",
         status: str = None) -> OrderFeedbackDTO:
    return OrderFeedbackDTO(
        order_id=order_id, portfolio_id="p1", engine_id="e", task_id="t",
        code="X", direction="1", filled_quantity=filled, fill_price=price,
        timestamp="2026-07-26T10:00:00", order_status=status,
    )


@pytest.mark.unit
class TestPartialFillNoDrop:
    """review #6778 问题③: 同 order_id 多笔 partial 必须全部处理, 不 drop。"""

    def test_multi_partial_fills_all_reconciled(self):
        """1000 手拆 500+300+200: 三笔都应返回 event, 不 drop。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]

        ev1 = node._reconcile_feedback(_dto("ord-1", 500))
        ev2 = node._reconcile_feedback(_dto("ord-1", 300))
        ev3 = node._reconcile_feedback(_dto("ord-1", 200))

        assert ev1 is not None and ev1.filled_quantity == 500
        assert ev2 is not None and ev2.filled_quantity == 300
        assert ev3 is not None and ev3.filled_quantity == 200

    def test_entry_retained_until_final_fill(self):
        """前两笔 partial 保留 entry; 第三笔 (累积达 volume) 才移除。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]

        node._reconcile_feedback(_dto("ord-1", 500))
        assert "ord-1" in node._pending_orders  # 累积 500 < 1000, 保留
        node._reconcile_feedback(_dto("ord-1", 300))
        assert "ord-1" in node._pending_orders  # 累积 800 < 1000, 保留
        node._reconcile_feedback(_dto("ord-1", 200))
        assert "ord-1" not in node._pending_orders  # 累积 1000 = volume, 移除

    def test_cumulative_filled_cleared_after_final(self):
        """终态 (累积达 volume) pop 整个 [order, cumulative] entry, 不残留。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]

        node._reconcile_feedback(_dto("ord-1", 1000))
        assert "ord-1" not in node._pending_orders

    def test_no_matching_order_returns_none(self):
        """非本节点提交 / 进程重启后丢失 → None (consumer 层响亮 drop, 不伪造骨架)。"""
        node = _make_node_pending_only()
        ev = node._reconcile_feedback(_dto("unknown", 100))
        assert ev is None

    def test_original_order_transaction_volume_not_mutated(self):
        """不改原 Order.transaction_volume: 避免污染已路由 event 的 remaining
        (event 持 order 引用, 改了会让下游读到的 remaining 失真), 也避免越界
        调 Order.settle (那是资金语义, 属下游 portfolio 职责)。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]

        ev = node._reconcile_feedback(_dto("ord-1", 500))
        assert ev is not None
        # event.remaining 此刻 = volume - 0 (历史) - 500 (本次) = 500, 反映"本笔后还剩"
        assert ev.remaining_quantity == 500
        # 原_order.transaction_volume 不被 consumer 改 (保持 0, 历史=下游职责)
        assert order.transaction_volume == 0


@pytest.mark.unit
class TestStatusFinalization:
    """review #6778 altitude: dto.order_status 优先判终态 (broker 自描述),
    缺省/解析失败回退累积量。消除"靠累积量猜终态"的 special case。"""

    def test_final_status_pops_even_if_cumulative_below_volume(self):
        """dto.order_status=FILLED → 直接判终态 pop, 不依赖累积量达 volume。
        (broker 报 FILLED 即终态权威, 即使 filled_quantity 漏报尾笔)"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]
        ev = node._reconcile_feedback(
            _dto("ord-1", 800, status=str(ORDERSTATUS_TYPES.FILLED.value)))
        assert ev is not None
        assert "ord-1" not in node._pending_orders  # status=FILLED → pop

    def test_partial_status_retained_even_if_cumulative_reaches_volume(self):
        """dto.order_status=PARTIAL_FILLED → 中间笔保留 entry, 即使累积碰巧达 volume。
        (broker 说 partial = 还有后续笔, 累积达 volume 是巧合不能 overrides broker 终态)"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]
        node._reconcile_feedback(
            _dto("ord-1", 1000, status=str(ORDERSTATUS_TYPES.PARTIAL_FILLED.value)))
        assert "ord-1" in node._pending_orders  # broker 说 partial, 保留

    def test_no_status_falls_back_to_cumulative(self):
        """dto.order_status 缺省 None → 回退累积量判终态
        (兼容旧 DTO / 模拟路径未填 status, 不破坏既有累积语义)。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = [order, 0.0]
        node._reconcile_feedback(_dto("ord-1", 500))  # 无 status
        assert "ord-1" in node._pending_orders  # 累积 500 < 1000, 保留
        node._reconcile_feedback(_dto("ord-1", 500))  # 无 status
        assert "ord-1" not in node._pending_orders  # 累积 1000, pop
