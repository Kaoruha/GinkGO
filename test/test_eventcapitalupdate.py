import unittest
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.event.capital_update import EventCapitalUpdate
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.ginkgo_data import GINKGODATA
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class EventCapitalUpdateTest(unittest.TestCase):
    """
    UnitTest for Event Capital Update.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventCapitalUpdateTest, self).__init__(*args, **kwargs)
        self.params = [{"code": "test"}]
        self.sim_code = "unittest_code"
        self.sim_dir = DIRECTION_TYPES.LONG
        self.sim_type = ORDER_TYPES.MARKETORDER
        self.sim_status = ORDERSTATUS_TYPES.FILLED

    def sim_ins(self) -> EventCapitalUpdate:
        GINKGODATA.drop_all()
        GINKGODATA.create_table(MOrder)
        e = EventCapitalUpdate()
        o = MOrder()
        o.code = self.sim_code
        o.direction = self.sim_dir
        o.type = self.sim_type
        o.status = self.sim_status
        GINKGODATA.add(o)
        GINKGODATA.commit()
        e.get_order(o.uuid)
        return e

    def test_EventCUInit_OK(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        # for i in self.params:
        #     GINKGODATA.drop_table(MOrder)
        #     GINKGODATA.create_table(MOrder)
        #     o = MOrder()
        #     o.status = 3
        #     GINKGODATA.add(o)
        #     GINKGODATA.commit()
        #     uuid = o.uuid
        #     e = EventCapitalUpdate()
        #     e.get_order(uuid)

    # def test_EventCU_Code_OK(self) -> None:
    #     time.sleep(GINKGOCONF.HEARTBEAT)
    #     e = self.sim_ins()
    #     print("==================================")
    #     print(e.code)
    #     print("==================================")
    #     self.assertEqual(e.code, self.sim_code)
