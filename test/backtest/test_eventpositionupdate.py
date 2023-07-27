import unittest
import pandas as pd
import datetime
from time import sleep
from ginkgo.backtest.events.position_update import EventPositionUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


class EventPositionUpdateTest(unittest.TestCase):
    """
    UnitTest for OrderSubmission.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventPositionUpdateTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "code": "unit_test_code",
                "uuid": "uuiduuiduuiduuid222",
                "source": SOURCE_TYPES.BAOSTOCK,
                "direction": DIRECTION_TYPES.LONG,
                "type": ORDER_TYPES.MARKETORDER,
                "volume": 2000,
                "status": ORDERSTATUS_TYPES.FILLED,
                "limit_price": 2.2,
                "frozen": 44000,
                "transaction_price": 0,
                "remain": 0,
                "timestamp": datetime.datetime.now(),
            }
        ]

    def test_EventPU_Init(self) -> None:
        for i in self.params:
            e = EventPositionUpdate()

    def test_EventPU_GetOrder(self) -> None:
        # Clean the Table
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            # Insert an Order
            o = MOrder()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.set(df)
            GDATA.add(o)
            GDATA.commit()
            # Try Get
            e = EventPositionUpdate(o.uuid)
            self.assertEqual(e.order_id, o.uuid)
            self.assertEqual(e.code, i["code"])
            self.assertEqual(e.direction, i["direction"])
            self.assertEqual(e.order_type, i["type"])
            self.assertEqual(e.volume, i["volume"])
            self.assertEqual(e.frozen, i["frozen"])
            self.assertEqual(e.transaction_price, i["transaction_price"])
            self.assertEqual(e.remain, i["remain"])
