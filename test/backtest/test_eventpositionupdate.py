import unittest
import datetime
from time import sleep
from ginkgo.backtest.events.position_update import EventPositionUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GCONF, GLOG
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
                "sim_code": "unittest_code",
                "sim_source": SOURCE_TYPES.BAOSTOCK,
                "sim_dir": DIRECTION_TYPES.LONG,
                "sim_type": ORDER_TYPES.MARKETORDER,
                "sim_status": ORDERSTATUS_TYPES.FILLED,
                "sim_volume": 2000,
                "sim_limitprice": 12.58,
            }
        ]

    def test_EventPU_Init(self) -> None:
        sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                e = EventPositionUpdate()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_EventPU_GetOrder(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate()
            e.get_order(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventPU_InitWithInput(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventPU_Code(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.code, i["sim_code"])

    def test_EventPU_Direction(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.direction, i["sim_dir"])

    def test_EventPU_Type(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.order_type, i["sim_type"])

    def test_EventPU_Status(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.order_status, i["sim_status"])

    def test_EventPU_LimitPrice(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.source = i["sim_source"]
            o.limit_price = i["sim_limitprice"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.limit_price, i["sim_limitprice"])

    def test_EventCU_Volume(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            o.volume = i["sim_volume"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventPositionUpdate(uuid)
            self.assertEqual(e.volume, i["sim_volume"])
