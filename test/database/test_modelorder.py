import unittest
import time
import datetime
import pandas as pd
from ginkgo.backtest.order import Order
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

from ginkgo import GCONF, GLOG


class ModelOrderTest(unittest.TestCase):
    """
    UnitTest for Order.
    """

    # Init
    # set data from bar
    # store in to GDATA
    # query from GDATA

    def __init__(self, *args, **kwargs) -> None:
        super(ModelOrderTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testordercode",
                "direction": DIRECTION_TYPES.LONG,
                "type": ORDER_TYPES.MARKETORDER,
                "status": ORDERSTATUS_TYPES.SUBMITTED,
                "source": SOURCE_TYPES.PORTFOLIO,
                "limit_price": 10.12,
                "volume": 2000,
                "freeze": 20240,
                "transaction_price": 0,
                "remain": 0,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_ModelOrder_Init(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                o = MOrder()
                o.set_source(i["source"])
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_ModelOrder_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            o = MOrder()
            o.set_source(i["source"])
            o.set(
                i["code"],
                i["direction"],
                i["type"],
                i["status"],
                i["volume"],
                i["limit_price"],
                i["freeze"],
                i["transaction_price"],
                i["remain"],
                i["timestamp"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.freeze, i["freeze"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrder_SetFromData(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        for i in self.params:
            o = MOrder()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.set(df)
            o.set_source(i["source"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.freeze, i["freeze"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrder_Insert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        try:
            o = MOrder()
            GDATA.add(o)
            GDATA.commit()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelOrder_BatchInsert(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        try:
            s = []
            for i in range(10):
                o = MOrder()
                s.append(o)

            GDATA.add_all(s)
            GDATA.commit()
        except Exception as e:
            result = False

        self.assertEqual(result, True)

    def test_ModelOrder_Query(self) -> None:
        time.sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        try:
            o = MOrder()
            GDATA.add(o)
            GDATA.commit()
            r = GDATA.session.query(MOrder).first()
        except Exception as e:
            result = False

        self.assertNotEqual(r, None)
        self.assertEqual(result, True)
