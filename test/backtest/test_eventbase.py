from time import sleep
import unittest
import datetime
from ginkgo.backtest.events import EventBase
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import datetime_normalize


class EventBaseTest(unittest.TestCase):
    """
    UnitTest for BaseEvent.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(EventBaseTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "source": SOURCE_TYPES.SIM,
                "type": EVENT_TYPES.PRICEUPDATE,
                "timestamp": datetime.datetime.now(),
            },
            {
                "source": SOURCE_TYPES.TEST,
                "type": "orderfill",
                "timestamp": "2020-01-01",
            },
            {
                "source": SOURCE_TYPES.TUSHARE,
                "type": "ORDERSubmission",
                "timestamp": 19000101,
            },
        ]

    def test_EventBase_Init(self) -> None:
        for i in self.params:
            e = EventBase()
            e.type = i["type"]
            e.set_source(i["source"])
            e.set_time(i["timestamp"])

            self.assertEqual(e.source, i["source"])
            self.assertEqual(e.timestamp, datetime_normalize(i["timestamp"]))
