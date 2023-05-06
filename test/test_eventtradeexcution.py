import unittest
import datetime
from time import sleep
from ginkgo.libs.ginkgo_logger import GINKGOLOGGER as gl
from ginkgo.backtest.event.trade_execution import EventTradeExcution
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


class EventTradeExcutionTest(unittest.TestCase):
    """
    UnitTest for OrderSubmission.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventTradeExcutionTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "sim_code": "unittest_code",
                "sim_source": SOURCE_TYPES.BAOSTOCK,
                "sim_dir": DIRECTION_TYPES.LONG,
                "sim_type": ORDER_TYPES.MARKETORDER,
                "sim_status": ORDERSTATUS_TYPES.FILLED,
                "sim_volume": 2222100,
                "sim_limitprice": 12.58,
            }
        ]

    def test_EventTE_Init(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                e = EventTradeExcution()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_EventTE_GetOrder(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution()
            e.get_order(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventTE_InitWithInput(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventTE_Code(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.code, i["sim_code"])

    def test_EventTE_Direction(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.direction, i["sim_dir"])

    def test_EventTE_Type(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.order_type, i["sim_type"])

    def test_EventTE_Status(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.order_status, i["sim_status"])

    def test_EventTE_LimitPrice(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            o.limit_price = i["sim_limitprice"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.limit_price, i["sim_limitprice"])

    def test_EventTE_Volume(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.volume = i["sim_volume"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventTradeExcution(uuid)
            self.assertEqual(e.volume, i["sim_volume"])