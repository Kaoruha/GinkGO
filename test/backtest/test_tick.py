import unittest
import time
import datetime
import pandas as pd
from ginkgo.backtest.tick import Tick
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES
from ginkgo.data.ginkgo_data import GDATA


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
                "price": 10.2,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
                "direction": TICKDIRECTION_TYPES.MINUSTICK,
                "source": SOURCE_TYPES.AKSHARE,
            },
            {
                "code": "sh.0000001",
                "price": 10,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
                "direction": TICKDIRECTION_TYPES.PLUSTICK,
                "source": SOURCE_TYPES.YAHOO,
            },
        ]

    def test_Tick_Init(self) -> None:
        for i in self.params:
            t = Tick()
            t.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_Set(self) -> None:
        for i in self.params:
            t = Tick()
            t.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")
            df = df[0]
            t = Tick()
            t.set(df)
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.direction, i["direction"])
            self.assertEqual(t.source, i["source"])
