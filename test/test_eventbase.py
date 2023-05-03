from time import sleep
import unittest
import datetime
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.event.base_event import EventBase
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES


class EventBaseTest(unittest.TestCase):
    """
    UnitTest for BaseEvent.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventBaseTest, self).__init__(*args, **kwargs)
        self.sim_source = SOURCE_TYPES.SIM
        self.sim_type = EVENT_TYPES.PRICEUPDATE
        self.sim_date = datetime.datetime.now()

    def sim_ins(self) -> EventBase:
        e = EventBase()
        e.source = self.sim_source
        e.update_time(self.sim_date)
        e.type = self.sim_type
        return e

    def test_EventBaseInit(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        params = [
            {"type": "priceupdate"},
            {"type": "orderfill"},
            {"type": "prICeupdate"},
        ]
        for i in range(len(params)):
            item = params[i]
            e = EventBase()
            e.type = item["type"]

    def test_EventBase_ID(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        e = self.sim_ins()
        self.assertTrue(e.id != None)

    def test_EventBase_Source(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        e = self.sim_ins()
        self.assertEqual(e.source, self.sim_source)

    def test_EventBase_Type(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        e = self.sim_ins()
        self.assertEqual(e.type, self.sim_type)

    def test_EventBase_Date(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        e = self.sim_ins()
        self.assertEqual(e.timestamp, self.sim_date)
