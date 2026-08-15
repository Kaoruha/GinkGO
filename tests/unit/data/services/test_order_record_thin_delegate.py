"""ADR-029 Task 8 契约：result_service.create_order_record thin delegate + 实盘零改动。

验证：
1. result_service.create_order_record 是 thin delegate（委托 OrderService.create_order_record）
2. 签名 ``**kwargs`` 不变（trade_gateway:338 / t1backtest:522 调用方透明）
3. 实盘 trade_gateway:338 调用链未改（mock container.result_service 仍被命中）

Run: pytest tests/unit/data/services/test_order_record_thin_delegate.py -v -o "addopts="
"""
from unittest.mock import MagicMock, patch

import pytest


class TestResultServiceCreateOrderRecordThinDelegate:
    """thin delegate 到 OrderService.create_order_record（写逻辑迁出）。"""

    def test_delegates_to_order_service(self):
        """result_service.create_order_record → container.order_service().create_order_record。"""
        from ginkgo.data.services.result_service import ResultService

        svc = ResultService(analyzer_crud=MagicMock(), signal_crud=MagicMock(), order_record_crud=MagicMock(), position_record_crud=MagicMock())

        mock_order_service = MagicMock()
        mock_order_service.create_order_record.return_value = MagicMock(success=True)

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.order_service.return_value = mock_order_service

            result = svc.create_order_record(
                order_id="o1", portfolio_id="p1", code="000001.SZ",
            )

        # 委托命中 order_service.create_order_record（非本 service 内部写）
        mock_container.order_service.assert_called_once()
        mock_order_service.create_order_record.assert_called_once_with(
            order_id="o1", portfolio_id="p1", code="000001.SZ",
        )

    def test_preserves_varargs_signature(self):
        """签名 **kwargs 不变——任意 kwargs 透传 OrderService。"""
        from ginkgo.data.services.result_service import ResultService

        svc = ResultService(analyzer_crud=MagicMock(), signal_crud=MagicMock(), order_record_crud=MagicMock(), position_record_crud=MagicMock())
        mock_order_service = MagicMock()

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.order_service.return_value = mock_order_service

            # 调用方传任意 kwargs（如 trade_gateway:338 的 17 个 kwargs）
            svc.create_order_record(
                order_id="o1",
                portfolio_id="p1",
                engine_id="e1",
                task_id="t1",
                code="000001.SZ",
                direction="LONG",
                order_type="MARKET",
                status="NEW",
                volume=100,
                limit_price=10.0,
                frozen_money=15000,
                frozen_volume=500,
                transaction_price=0,
                transaction_volume=0,
                remain=100,
                fee=0,
                timestamp="2024-01-01",
                business_timestamp="2024-01-01",
            )

        # 全部透传
        kwargs = mock_order_service.create_order_record.call_args.kwargs
        assert kwargs["order_id"] == "o1"
        assert kwargs["frozen_money"] == 15000
        assert kwargs["frozen_volume"] == 500
        assert kwargs["status"] == "NEW"

    def test_returns_what_order_service_returns(self):
        """返回值直传 OrderService 的 ServiceResult（不包装）。"""
        from ginkgo.data.services.result_service import ResultService
        from ginkgo.data.services.base_service import ServiceResult

        svc = ResultService(analyzer_crud=MagicMock(), signal_crud=MagicMock(), order_record_crud=MagicMock(), position_record_crud=MagicMock())
        sentinel = ServiceResult.success({"message": "from order_service"})

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.order_service().create_order_record.return_value = sentinel
            result = svc.create_order_record(order_id="o1")

        assert result is sentinel


class TestTradeGatewayCallSiteUnchanged:
    """实盘零改动硬约束：trade_gateway:338 调 result_service.create_order_record 透明。

    验证 trade_gateway._save_submitted_order_record 仍走 container.result_service()
    → .create_order_record(**kwargs)（thin delegate 透明）。
    """

    def test_trade_gateway_calls_result_service_create_order_record(self):
        """trade_gateway 调用点未改——仍命中 result_service.create_order_record。"""
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.base_broker import BaseBroker
        from ginkgo.entities import Order
        from ginkgo.enums import (
            DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES,
        )
        from datetime import datetime

        # StubBroker 满足 isinstance(BaseBroker) + set_result_callback 调用
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

        broker = _StubBroker()
        gw = TradeGateway(brokers=broker, name="test")
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
            frozen_money=15000, frozen_volume=500,
        )
        order.timestamp = datetime.now()
        order.business_timestamp = order.timestamp

        event = MagicMock()
        event.portfolio_id = "portfolio-uuid-1"

        mock_service = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.result_service.return_value = mock_service
            gw._save_submitted_order_record(order, event)

        # 命中 result_service.create_order_record（thin delegate 入口，未改）
        mock_service.create_order_record.assert_called_once()
        kwargs = mock_service.create_order_record.call_args.kwargs
        # 关键 kwargs 透明（#6056 frozen 拆分字段）
        assert kwargs.get("frozen_money") == 15000
        assert kwargs.get("frozen_volume") == 500
        assert "frozen" not in kwargs
