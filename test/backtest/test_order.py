import unittest
import time
import datetime
import pandas as pd
from ginkgo.backtest.order import Order
from ginkgo.data.models import MOrder
from ginkgo.enums import ORDER_TYPES, DIRECTION_TYPES, SOURCE_TYPES, ORDERSTATUS_TYPES
from ginkgo import GLOG
from ginkgo.data.ginkgo_data import GDATA


class OrderTest(unittest.TestCase):
    """
    UnitTest for order.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(OrderTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "source": SOURCE_TYPES.SINA,
                "code": "unit_test_code",
                "uuid": "uuiduuiduuiduuid222",
                "direction": DIRECTION_TYPES.LONG,
                "type": ORDER_TYPES.MARKETORDER,
                "volume": 2000,
                "status": ORDERSTATUS_TYPES.FILLED,
                "limit_price": 2.2,
                "frozen": 44000,
                "transaction_price": 21222.3,
                "remain": 10,
                "timestamp": datetime.datetime.now(),
            },
            {
                "source": SOURCE_TYPES.SIM,
                "code": "unit_test_code22",
                "uuid": "uuiduuiduuiduuid22233",
                "direction": DIRECTION_TYPES.LONG,
                "type": ORDER_TYPES.MARKETORDER,
                "volume": 2000,
                "status": ORDERSTATUS_TYPES.FILLED,
                "limit_price": 2.4,
                "frozen": 54000,
                "transaction_price": 34,
                "remain": 400,
                "timestamp": datetime.datetime.now(),
            },
        ]

    def test_Order_Init(self) -> None:
        for i in self.params:
            o = Order()

    def test_Order_SetFromData(self) -> None:
        for item in self.params:
            o = Order()
            o.set(
                item["code"],
                item["direction"],
                item["type"],
                item["volume"],
                item["limit_price"],
                item["frozen"],
                item["transaction_price"],
                item["remain"],
                item["timestamp"],
                item["uuid"],
            )
            o.set_source(item["source"])
            self.assertEqual(o.code, item["code"])
            self.assertEqual(o.direction, item["direction"])
            self.assertEqual(o.type, item["type"])
            self.assertEqual(o.volume, item["volume"])
            self.assertEqual(o.limit_price, item["limit_price"])
            self.assertEqual(o.frozen, item["frozen"])
            self.assertEqual(o.transaction_price, item["transaction_price"])
            self.assertEqual(o.remain, item["remain"])
            self.assertEqual(o.source, item["source"])
            self.assertEqual(o.uuid, item["uuid"])

    def test_Order_SetFromDataFrame(self) -> None:
        for item in self.params:
            o = Order()
            df = pd.DataFrame.from_dict(item, orient="index")[0]
            o.set(df)
            o.set_source(item["source"])
            self.assertEqual(o.code, item["code"])
            self.assertEqual(o.direction, item["direction"])
            self.assertEqual(o.type, item["type"])
            self.assertEqual(o.volume, item["volume"])
            self.assertEqual(o.limit_price, item["limit_price"])
            self.assertEqual(o.frozen, item["frozen"])
            self.assertEqual(o.transaction_price, item["transaction_price"])
            self.assertEqual(o.remain, item["remain"])
            self.assertEqual(o.source, item["source"])
            self.assertEqual(o.uuid, item["uuid"])
