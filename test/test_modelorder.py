import unittest
import datetime
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class ModelOrderTest(unittest.TestCase):
    """
    UnitTest for Order.
    """

    # Init
    # set data from bar
    # store in to ginkgodata
    # query from ginkgodata

    def __init__(self, *args, **kwargs) -> None:
        super(ModelOrderTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testordercode",
                "direction": DIRECTION_TYPES.LONG,
                "order_type": ORDER_TYPES.MARKETORDER,
                "status": ORDERSTATUS_TYPES.FILLED,
                "source": SOURCE_TYPES.BAOSTOCK,
                "price": 231,
                "volume": 23331,
                "datetime": datetime.datetime.now(),
            }
        ]

    def test_ModelOrderInit_OK(self) -> None:
        print("")
        gl.logger.warn("Order 初始化 测试开始.")
        for i in self.params:
            o = MOrder()
            o.set(
                i["code"],
                i["direction"],
                i["order_type"],
                i["status"],
                i["source"],
                i["price"],
                i["volume"],
                i["datetime"],
            )
            # print(o)
        gl.logger.warn("Order 初始化 测试完成.")

    def test_ModelOrderSetFromData_OK(self) -> None:
        print("")
        gl.logger.warn("ModelOrder SetFromData 测试开始.")
        for i in self.params:
            o = MOrder()
            o.set(
                i["code"],
                i["direction"],
                i["order_type"],
                i["status"],
                i["source"],
                i["volume"],
                i["price"],
                i["datetime"],
            )
        gl.logger.warn("ModelOrder SetFromData 测试完成.")

    def test_ModelOrderSetFromOrder_OK(self) -> None:
        print("")
        gl.logger.warn("ModelOrder SetFromOrder 测试开始.")
        for i in self.params:
            o = MOrder()
            order = Order(
                i["datetime"], i["code"], i["direction"], i["order_type"], i["volume"]
            )
            o.set(order, SOURCE_TYPES.SINA)
        gl.logger.warn("ModelOrder SetFromOrder 测试完成.")

    def test_OrderInsert_OK(self) -> None:
        print("")
        gl.logger.warn("Order Insert 测试开始.")
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        o = MOrder()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        gl.logger.warn("Order Insert 测试完成.")

    def test_OrderBatchInsert_OK(self) -> None:
        print("")
        gl.logger.warn("Order BatchInsert 测试开始.")
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        s = []

        for i in range(10):
            o = MOrder()
            s.append(o)
            # o.dire = 2

        GINKGODATA.add_all(s)
        GINKGODATA.commit()
        gl.logger.warn("Order BatchInsert 测试完成.")

    def test_OrderQuery_OK(self) -> None:
        print("")
        gl.logger.warn("Order Query 测试开始.")
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        o = MOrder()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        r = GINKGODATA.session.query(MOrder).first()
        print(r)
        gl.logger.warn("Order Query 测试完成.")
