import unittest
import datetime
from time import sleep
from ginkgo.backtest.events.capital_update import EventCapitalUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GCONF, GLOG
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


class EventCapitalUpdateTest(unittest.TestCase):
    """
    UnitTest for Event Capital Update.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "sim_code": "unit_test_code",
                "sim_source": SOURCE_TYPES.BAOSTOCK,
                "sim_dir": DIRECTION_TYPES.LONG,
                "sim_type": ORDER_TYPES.MARKETORDER,
                "sim_volume": 2000,
                "sim_status": ORDERSTATUS_TYPES.FILLED,
            }
        ]

    def test_EventCU_Init(self) -> None:
        sleep(GCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                e = EventCapitalUpdate()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_EventCU_InitWithInput(self) -> None:
        sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventCU_GetOrder(self) -> None:
        sleep(GCONF.HEARTBEAT)
        result = True
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate()
            e.get_order(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventCU_Code(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.code, i["sim_code"])

    def test_EventCU_Dir(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.direction, i["sim_dir"])

    def test_EventCU_Type(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_type, i["sim_type"])

    def test_EventCU_Status(self) -> None:
        sleep(GCONF.HEARTBEAT)
        GDATA.drop_table(MOrder)
        GDATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GDATA.add(o)
            GDATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_status, i["sim_status"])

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
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.volume, i["sim_volume"])
