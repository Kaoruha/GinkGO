# Upstream: src/ginkgo/workers/execution_node/node.py (_consume_order_feedback)
# Role: review #6778 问题③ — partial fill 多笔回报不能 pop 注册表

"""review #6778 问题③: partial fill 多笔回报不能 pop 注册表。

真实 broker 常分多笔回报 (如 1000 手拆 500+300+200)。旧代码
``_pending_orders.pop(dto.order_id)`` 在第一笔就移除 entry → 第二笔 pop
返回 None → GLOG.ERROR 丢弃 → 持仓错账。正确性被钉死在"gateway 必须一发完"。

修法: 累积 filled 量, 仅最终 filled (累积 >= volume) 才 pop, 中间笔保留 entry。
用独立 ``_pending_filled`` 字典累积, 不改原 Order (避免污染已路由 event 的
remaining, 也避免越界碰 Order 的资金语义 settle)。
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
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.interfaces.dtos import OrderFeedbackDTO


def _make_node_pending_only() -> ExecutionNode:
    """构造仅含 pending 注册表的 ExecutionNode (跳过 Kafka/Redis init 副作用)。"""
    node = object.__new__(ExecutionNode)
    node._pending_orders = {}
    node._pending_filled = {}  # review #6778 问题③: 累积 filled 判终态
    node.node_id = "test-node"
    return node


def _dto(order_id: str, filled: float, price: str = "10.0") -> OrderFeedbackDTO:
    return OrderFeedbackDTO(
        order_id=order_id, portfolio_id="p1", engine_id="e", task_id="t",
        code="X", direction="1", filled_quantity=filled, fill_price=price,
        timestamp="2026-07-26T10:00:00",
    )


@pytest.mark.unit
class TestPartialFillNoDrop:
    """review #6778 问题③: 同 order_id 多笔 partial 必须全部处理, 不 drop。"""

    def test_multi_partial_fills_all_reconciled(self):
        """1000 手拆 500+300+200: 三笔都应返回 event, 不 drop。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = order

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
        node._pending_orders["ord-1"] = order

        node._reconcile_feedback(_dto("ord-1", 500))
        assert "ord-1" in node._pending_orders  # 累积 500 < 1000, 保留
        node._reconcile_feedback(_dto("ord-1", 300))
        assert "ord-1" in node._pending_orders  # 累积 800 < 1000, 保留
        node._reconcile_feedback(_dto("ord-1", 200))
        assert "ord-1" not in node._pending_orders  # 累积 1000 = volume, 移除

    def test_cumulative_filled_cleared_after_final(self):
        """终态 pop 后, 累积字典也清, 不留孤儿。"""
        node = _make_node_pending_only()
        order = Order(uuid="ord-1", portfolio_id="p1", code="X",
                      direction=DIRECTION_TYPES.LONG, volume=1000, limit_price=10.0)
        node._pending_orders["ord-1"] = order

        node._reconcile_feedback(_dto("ord-1", 1000))
        assert "ord-1" not in node._pending_filled

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
        node._pending_orders["ord-1"] = order

        ev = node._reconcile_feedback(_dto("ord-1", 500))
        assert ev is not None
        # event.remaining 此刻 = volume - 0 (历史) - 500 (本次) = 500, 反映"本笔后还剩"
        assert ev.remaining_quantity == 500
        # 原_order.transaction_volume 不被 consumer 改 (保持 0, 历史=下游职责)
        assert order.transaction_volume == 0
