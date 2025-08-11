import unittest
import random
import time
import datetime
import pandas as pd
from decimal import Decimal
from ginkgo.backtest.entities.tick import Tick
from ginkgo.libs import GLOG
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class TickTest(unittest.TestCase):
    """
    UnitTest for tick.
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(TickTest, self).__init__(*args, **kwargs)
        self.dev = False
        self.params = [
            {
                "code": "sh.0000001",
                "price": Decimal(round(random.uniform(0, 100), 2)),
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
                "direction": TICKDIRECTION_TYPES.NEUTRAL,
                "source": SOURCE_TYPES.AKSHARE,
            },
            {
                "code": "sh.0000001",
                "price": Decimal(round(random.uniform(0, 100), 2)),
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
                "direction": TICKDIRECTION_TYPES.NEUTRAL,
                "source": SOURCE_TYPES.YAHOO,
            },
        ]

    def test_Tick_Init(self) -> None:
        for i in self.params:
            t = Tick()
            t.set(
                i["code"],
                i["price"],
                i["volume"],
                i["direction"],
                i["timestamp"],
                i["source"],
            )
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_Set(self) -> None:
        for i in self.params:
            t = Tick()
            t.set(
                i["code"],
                i["price"],
                i["volume"],
                i["direction"],
                i["timestamp"],
                i["source"],
            )
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame(i, index=[0])
            df = df.iloc[0]
            t = Tick()
            t.set(df)
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])
