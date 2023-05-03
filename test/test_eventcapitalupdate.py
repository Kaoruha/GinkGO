import unittest
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.event.capital_update import EventCapitalUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


class EventCapitalUpdateTest(unittest.TestCase):
    """
    UnitTest for Event Capital Update.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "sim_code": "unit_test_code",
                "sim_source": SOURCE_TYPES.BAOSTOCK,
                "sim_dir": DIRECTION_TYPES.LONG,
                "sim_type": ORDER_TYPES.MARKETORDER,
                "sim_status": ORDERSTATUS_TYPES.FILLED,
            }
        ]

    def test_EventCU_Init(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                e = EventCapitalUpdate()
            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_EventCU_InitWithInput(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventCU_GetOrder(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        result = True
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate()
            e.get_order(uuid)
            self.assertEqual(e.order_id, uuid)

    def test_EventCU_Code(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.code, i["sim_code"])

    def test_EventCU_Dir(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.direction, i["sim_dir"])

    def test_EventCU_Type(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_type, i["sim_type"])

    def test_EventCU_Status(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        GINKGODATA.drop_table(MOrder)
        GINKGODATA.create_table(MOrder)
        for i in self.params:
            o = MOrder()
            o.code = i["sim_code"]
            o.direction = i["sim_dir"]
            o.type = i["sim_type"]
            o.status = i["sim_status"]
            GINKGODATA.add(o)
            GINKGODATA.commit()
            uuid = o.uuid
            e = EventCapitalUpdate(uuid)
            self.assertEqual(e.order_status, i["sim_status"])
