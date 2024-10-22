import unittest
import random
import time
import pandas as pd
import datetime

from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MTradeDay


class ModelTradeDayTest(unittest.TestCase):
    """
    Unittest for Model TradeDay
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTradeDayTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MTradeDay
        self.params = [
            {
                "market": random.choice([i for i in MARKET_TYPES]),
                "timestamp": datetime.datetime.now(),
                "is_open": random.choice([True, False]),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelTradeDay_Init(self) -> None:
        for i in self.params:
            o = self.model(market=i["market"], timestamp=i["timestamp"], is_open=i["is_open"], source=i["source"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.is_open, i["is_open"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTradeDay_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update market
            o.update(i["market"])
            self.assertEqual(o.market, i["market"])

            # Update timestamp
            o.update(i["market"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

            # Update is_open
            o.update(i["market"], is_open=i["is_open"])
            self.assertEqual(o.is_open, i["is_open"])

            # Update source
            o.update(i["market"], source=i["source"])
            self.assertEqual(o.source, i["source"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(i["market"], timestamp=i["timestamp"], is_open=i["is_open"], source=i["source"])
            self.assertEqual(i["market"], o.market)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["is_open"], o.is_open)
            self.assertEqual(i["source"], o.source)

    def test_ModelTradeDay_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = self.model()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.update(df)
            self.assertEqual(i["market"], o.market)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["is_open"], o.is_open)
            self.assertEqual(i["source"], o.source)
