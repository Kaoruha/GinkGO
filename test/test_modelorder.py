import unittest
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

from ginkgo.libs.ginkgo_conf import GINKGOCONF


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
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MOrder()
            o.set(
                i["code"],
                i["direction"],
                i["order_type"],
                i["status"],
                i["price"],
                i["volume"],
                i["datetime"],
            )
            o.set_source(i["source"])

    def test_ModelOrderSetFromData_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            o = MOrder()
            o.set(
                i["code"],
                i["direction"],
                i["order_type"],
                i["status"],
                i["volume"],
                i["price"],
                i["datetime"],
            )
            o.set_source(i["source"])

    def test_ModelOrderInsert_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        o = MOrder()
        GINKGODATA.add(o)
        GINKGODATA.commit()

    def test_ModelOrderBatchInsert_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        s = []

        for i in range(10):
            o = MOrder()
            s.append(o)
            # o.dire = 2

        GINKGODATA.add_all(s)
        GINKGODATA.commit()

    def test_ModelOrderQuery_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)

        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        o = MOrder()
        GINKGODATA.add(o)
        GINKGODATA.commit()
        r = GINKGODATA.get_order(o.uuid)
