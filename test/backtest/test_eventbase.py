from time import sleep
import unittest
import datetime
from ginkgo.backtest.events.base_event import EventBase
from ginkgo import GCONF, GLOG
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES


class EventBaseTest(unittest.TestCase):
    """
    UnitTest for BaseEvent.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventBaseTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "source": SOURCE_TYPES.SIM,
                "type": EVENT_TYPES.PRICEUPDATE,
                "timestamp": datetime.datetime.now(),
            },
            {
                "source": SOURCE_TYPES.SIM,
                "type": "orderfill",
                "timestamp": datetime.datetime.now(),
            },
            {
                "source": SOURCE_TYPES.SIM,
                "type": "ORDERSubmission",
                "timestamp": datetime.datetime.now(),
            },
        ]

    # def test_EventBase_Init(self) -> None:
    #     sleep(GCONF.HEARTBEAT)
    #     result = True
    #     for i in self.params:
    #         try:
    #             e = EventBase()
    #             e.type = i["type"]

    #         except Exception as e:
    #             result = False
    #     self.assertEqual(result, True)


#     def test_EventBase_UUID(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             e = EventBase()
#             e.type = i["type"]
#             e.source = i["source"]
#             e.update_time(i["timestamp"])
#             self.assertNotEqual(e.uuid, None)

#     def test_EventBase_Source(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             e = EventBase()
#             e.type = i["type"]
#             e.source = i["source"]
#             e.update_time(i["timestamp"])
#             self.assertEqual(e.source, i["source"])

#     def test_EventBase_Date(self) -> None:
#         sleep(GCONF.HEARTBEAT)
#         for i in self.params:
#             e = EventBase()
#             e.type = i["type"]
#             e.source = i["source"]
#             e.update_time(i["timestamp"])
#             self.assertEqual(e.timestamp, i["timestamp"])
