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
        self.params = [
            {
                "sim_source": SOURCE_TYPES.SIM,
                "sim_type": EVENT_TYPES.PRICEUPDATE,
                "sim_timestamp": datetime.datetime.now(),
            },
            {
                "sim_source": SOURCE_TYPES.SIM,
                "sim_type": "orderfill",
                "sim_timestamp": datetime.datetime.now(),
            },
            {
                "sim_source": SOURCE_TYPES.SIM,
                "sim_type": "ORDERSubmission",
                "sim_timestamp": datetime.datetime.now(),
            },
        ]

    def test_EventBase_Init(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        result = True
        for i in self.params:
            try:
                e = EventBase()
                e.type = i["sim_type"]

            except Exception as e:
                result = False
        self.assertEqual(result, True)

    def test_EventBase_UUID(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            e = EventBase()
            e.type = i["sim_type"]
            e.source = i["sim_source"]
            e.update_time(i["sim_timestamp"])
            self.assertNotEqual(e.uuid, None)

    def test_EventBase_Source(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            e = EventBase()
            e.type = i["sim_type"]
            e.source = i["sim_source"]
            e.update_time(i["sim_timestamp"])
            self.assertEqual(e.source, i["sim_source"])

    def test_EventBase_Date(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            e = EventBase()
            e.type = i["sim_type"]
            e.source = i["sim_source"]
            e.update_time(i["sim_timestamp"])
            self.assertEqual(e.timestamp, i["sim_timestamp"])
