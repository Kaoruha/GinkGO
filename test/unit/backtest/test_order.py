import unittest
from datetime import datetime
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.entities.order import Order


class TestOrder(unittest.TestCase):
    def setUp(self):
        # 在每个测试方法之前初始化 Order 实例
        self.order = Order(
            code="TEST123",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=50.0,
            frozen=10.0,
            transaction_price=45.0,
            transaction_volume=50,
            remain=50.0,
            fee=1.0,
            timestamp=datetime(2025, 5, 5),
            order_id="order123",
            portfolio_id="portfolio1",
            engine_id="engine1",
        )

    def test_order_initialization(self):
        # 验证订单初始化后各个字段是否正确赋值
        self.assertEqual(self.order.code, "TEST123")
        self.assertEqual(self.order.direction, DIRECTION_TYPES.LONG)
        self.assertEqual(self.order.order_type, ORDER_TYPES.LIMITORDER)
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.NEW)
        self.assertEqual(self.order.volume, 100)
        self.assertEqual(self.order.limit_price, 50.0)
        self.assertEqual(self.order.frozen, 10.0)
        self.assertEqual(self.order.transaction_price, 45.0)
        self.assertEqual(self.order.transaction_volume, 50)
        self.assertEqual(self.order.remain, 50.0)
        self.assertEqual(self.order.fee, 1.0)
        self.assertEqual(self.order.timestamp, datetime(2025, 5, 5))
        self.assertEqual(self.order.order_id, "order123")
        self.assertEqual(self.order.portfolio_id, "portfolio1")
        self.assertEqual(self.order.engine_id, "engine1")

    def test_submit(self):
        # 测试订单提交后状态是否更新
        self.order.submit()
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.SUBMITTED)

    def test_fill(self):
        # 测试订单填充后状态是否更新
        self.order.fill()
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.FILLED)

    def test_cancel(self):
        # 测试订单取消后状态是否更新
        self.order.cancel()
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.CANCELED)

    def test_set_properties(self):
        # 测试动态更新属性
        self.order.code = "TEST456"
        self.assertEqual(self.order.code, "TEST456")

        self.order.timestamp = datetime(2025, 6, 5)
        self.assertEqual(self.order.timestamp, datetime(2025, 6, 5))

        self.order.volume = 200
        self.assertEqual(self.order.volume, 200)

    def test_invalid_status_update(self):
        # 测试订单状态是否正确更新
        self.order.submit()
        # TODO
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.SUBMITTED)

    def test_set_from_dataframe(self):
        import pandas as pd

        # 使用DataFrame设置订单属性
        data = {
            "code": "TEST789",
            "direction": DIRECTION_TYPES.SHORT.value,
            "order_type": ORDER_TYPES.MARKETORDER.value,
            "status": ORDERSTATUS_TYPES.NEW.value,
            "volume": 500,
            "limit_price": 55.5,
            "frozen": 20.0,
            "transaction_price": 50.0,
            "transaction_volume": 100,
            "remain": 400.0,
            "fee": 2.0,
            "timestamp": datetime(2025, 5, 6),
            "uuid": "order456",
            "portfolio_id": "portfolio2",
            "engine_id": "engine2",
        }
        df = pd.Series(data)
        self.order.set(df)

        # 确保从DataFrame设置后值被正确更新
        self.assertEqual(self.order.code, "TEST789")
        self.assertEqual(self.order.direction, DIRECTION_TYPES.SHORT)
        self.assertEqual(self.order.order_type, ORDER_TYPES.MARKETORDER)
        self.assertEqual(self.order.status, ORDERSTATUS_TYPES.NEW)
        self.assertEqual(self.order.volume, 500)
        self.assertEqual(self.order.limit_price, 55.5)
        self.assertEqual(self.order.frozen, 20.0)
        self.assertEqual(self.order.transaction_price, 50.0)
        self.assertEqual(self.order.transaction_volume, 100)
        self.assertEqual(self.order.remain, 400.0)
        self.assertEqual(self.order.fee, 2.0)
        self.assertEqual(self.order.timestamp, datetime(2025, 5, 6))
        self.assertEqual(self.order.order_id, "order456")
        self.assertEqual(self.order.portfolio_id, "portfolio2")
        self.assertEqual(self.order.engine_id, "engine2")
