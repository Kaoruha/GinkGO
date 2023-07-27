import unittest
import pandas as pd
import datetime
from time import sleep
from ginkgo.backtest.events.price_update import EventPriceUpdate
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.tick import Tick
from ginkgo.libs import datetime_normalize
from ginkgo import GLOG
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    PRICEINFO_TYPES,
)


class EventPriceUpdateTest(unittest.TestCase):
    """
    UnitTest for OrderSubmission.
    """

    # Init

    def __init__(self, *args, **kwargs) -> None:
        super(EventPriceUpdateTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "code": "unittest_code",
                "source": SOURCE_TYPES.TEST,
                "timestamp": "2022-02-12 02:12:20",
                "frequency": FREQUENCY_TYPES.DAY,
                "open": 19,
                "high": 19,
                "low": 19,
                "close": 19,
                "volume": 1900,
                "price": 10.21,
            },
            {
                "code": "unittest_code22",
                "source": SOURCE_TYPES.TUSHARE,
                "timestamp": "2022-02-12 02:12:20",
                "frequency": FREQUENCY_TYPES.DAY,
                "open": 11,
                "high": 12,
                "low": 10.22,
                "close": 12.1,
                "volume": 19010,
                "price": 10.01,
            },
        ]

    def test_EventPU_Init(self) -> None:
        for i in self.params:
            e = EventPriceUpdate()

    def test_EventPU_Bar(self) -> None:
        for i in self.params:
            b = Bar()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            b.set(df)
            e = EventPriceUpdate()
            e.set(b)
            e.set_source(i["source"])
            self.assertEqual(i["code"], e.code)
            self.assertEqual(i["source"], e.source)
            self.assertEqual(datetime_normalize(i["timestamp"]), e.timestamp)
            self.assertEqual(i["volume"], e.volume)
            self.assertEqual(i["open"], e.open)
            self.assertEqual(i["high"], e.high)
            self.assertEqual(i["low"], e.low)
            self.assertEqual(i["close"], e.close)

    # TODO Tick
