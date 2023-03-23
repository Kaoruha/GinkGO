import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.order import Order
from ginkgo.backtest.enums import OrderType, Direction


class OrderTest(unittest.TestCase):
    """
    UnitTest for order.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(OrderTest, self).__init__(*args, **kwargs)

    def test_OrderInit_OK(self) -> None:
        print("")
        gl.logger.warn("Order初始化 测试开始.")
        params = [
            {
                "code": "sh.0000001",
                "timestamp": "2020-01-01 02:02:32",
                "direction": Direction.LONG,
                "order_type": OrderType.LIMITORDER,
                "quantity": 100001,
                "limit_price": 10.0,
            },
            {
                "code": "sh.0000001",
                "timestamp": datetime.datetime.now(),
                "direction": Direction.SHORT,
                "order_type": OrderType.MARKETORDER,
                "quantity": 100001.1,
                "limit_price": 12.1,
            },
        ]
        for i in params:
            o = Order(
                timestamp=i["timestamp"],
                code=i["code"],
                direction=i["direction"],
                order_type=i["order_type"],
                quantity=i["quantity"],
                limit_price=i["limit_price"],
            )
            o.fill()
            print(o)
        gl.logger.warn("Order初始化 测试完成.")
