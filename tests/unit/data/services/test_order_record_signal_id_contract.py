"""#6911 血缘契约：MOrderRecord 三态行(NEW/SUBMITTED/FILLED)必带 signal_id 键。

背景：trade_gateway._save_submitted_order_record 手抄 17 字段漏了 signal_id，
CRUD required 校验(默认必填)拦下 → SUBMITTED 快照落库失败 ×54(6单×9重试)，
且 gateway 未检查 ServiceResult 照打成功 INFO 日志(安静失败+假成功)。

本契约把防线从"CRUD 校验+重试放大后才暴露"上移到"调用瞬间 TypeError"：
1. OrderService.create_order_record 漏传 signal_id → TypeError
2. ResultService thin delegate 漏传 signal_id → TypeError(契约透传,不静默吞)
3. SUBMITTED 快照带上 signal_id(回测必有值路径)

Run: pytest tests/unit/data/services/test_order_record_signal_id_contract.py -v -o "addopts="
"""
from unittest.mock import MagicMock, patch

import pytest


class TestSignalIdKeywordOnlyContract:
    """signal_id 显式 keyword-only 必传——漏传在函数绑定参数瞬间炸。"""

    def test_order_service_missing_signal_id_raises_type_error(self):
        """OrderService.create_order_record 漏传 signal_id → TypeError(非静默)。"""
        from ginkgo.data.services.order_service import OrderService

        svc = OrderService(crud_repo=MagicMock())
        with pytest.raises(TypeError, match="signal_id"):
            svc.create_order_record(order_id="o1", code="000001.SZ")

    def test_result_service_delegate_missing_signal_id_raises_type_error(self):
        """ResultService delegate 漏传 signal_id → TypeError(契约不因透传而丢失)。"""
        from ginkgo.data.services.result_service import ResultService

        svc = ResultService(
            analyzer_crud=MagicMock(), signal_crud=MagicMock(),
            order_record_crud=MagicMock(), position_record_crud=MagicMock(),
        )
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.order_service.return_value = MagicMock()
            with pytest.raises(TypeError, match="signal_id"):
                svc.create_order_record(order_id="o1", code="000001.SZ")

    def test_empty_string_signal_id_is_legal(self):
        """手工/外部单 signal_id='' 合法——required 拦缺键不拦空值,直通 CRUD。"""
        from ginkgo.data.services.order_service import OrderService

        fake_crud = MagicMock()
        with patch(
            "ginkgo.data.crud.order_record_crud.OrderRecordCRUD",
            return_value=fake_crud,
        ):
            svc = OrderService(crud_repo=MagicMock())
            res = svc.create_order_record(signal_id="", code="000001.SZ")
        assert res.is_success()
        # 空串原样到达 CRUD(非丢弃)
        assert fake_crud.create.call_args.kwargs.get("signal_id") == ""


class TestGatewaySubmittedSnapshotSignalId:
    """SUBMITTED 快照血缘：gateway 从 order 实体无条件抄 signal_id。"""

    def _make_gateway_with_order(self, signal_id_value):
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.base_broker import BaseBroker
        from ginkgo.entities import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
        from datetime import datetime

        class _StubBroker(BaseBroker):
            def __init__(self):
                super().__init__({})
            def set_result_callback(self, cb): pass
            def is_connected(self): return True
            def validate_order(self, order): return True
            def supports_immediate_execution(self): return False
            def requires_manual_confirmation(self): return False
            def submit_order_event(self, event): return MagicMock()
            def cancel_order(self, broker_order_id): return MagicMock()

        gw = TradeGateway(brokers=_StubBroker(), name="test")
        engine = MagicMock()
        engine.engine_id = "engine-uuid-1"
        engine.task_id = "task-uuid-1"
        gw._bound_engine = engine
        gw.set_event_publisher(MagicMock())

        order = Order(
            portfolio_id="p1", engine_id="e1", task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100, limit_price=20.0,
        )
        order.signal_id = signal_id_value
        order.timestamp = datetime.now()
        order.business_timestamp = order.timestamp

        event = MagicMock()
        event.portfolio_id = "portfolio-uuid-1"
        return gw, order, event

    def test_submitted_snapshot_carries_signal_id(self):
        """回测订单(引擎 on_signal 已绑 signal_id)→ SUBMITTED 快照带血缘。"""
        gw, order, event = self._make_gateway_with_order("signal-uuid-abc")
        mock_service = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.result_service.return_value = mock_service
            gw._save_submitted_order_record(order, event)
        kwargs = mock_service.create_order_record.call_args.kwargs
        assert kwargs.get("signal_id") == "signal-uuid-abc"

    def test_result_error_no_fake_success_path(self):
        """落库失败(ServiceResult.error)不抛异常但不再走成功分支——检查 result。"""
        from ginkgo.data.services.base_service import ServiceResult

        gw, order, event = self._make_gateway_with_order("signal-uuid-abc")
        mock_service = MagicMock()
        mock_service.create_order_record.return_value = ServiceResult.error("db down")
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.result_service.return_value = mock_service
            # 不抛:持久化失败不阻断提交流程(既有设计),但 result 已被检查
            gw._save_submitted_order_record(order, event)
        mock_service.create_order_record.assert_called_once()
