import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.tick import Tick
from ginkgo.data.models.model_tick import MTick
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.enums import SOURCE_TYPES
from ginkgo.data.ginkgo_data import GINKGODATA


class TickTest(unittest.TestCase):
    """
    UnitTest for tick.
    """

    # Init
    def __init__(self, *args, **kwargs) -> None:
        super(TickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "sh.0000001",
                "price": 10.2,
                "volume": 100,
                "timestamp": "2020-01-01 02:02:32",
                "source": SOURCE_TYPES.AKSHARE,
            },
            {
                "code": "sh.0000001",
                "price": 10,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
                "source": SOURCE_TYPES.YAHOO,
            },
        ]

    def test_Tick_Init(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            code = i["code"]
            price = i["price"]
            volume = i["volume"]
            timestamp = i["timestamp"]
            t = Tick(code, price, volume, timestamp)
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_Set(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            t = Tick()
            t.set(i["code"], i["price"], i["volume"], i["timestamp"])
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_SetFromDataFrame(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            data = {
                "code": i["code"],
                "price": i["price"],
                "volume": i["volume"],
                "timestamp": i["timestamp"],
            }
            t = Tick()
            t.set(pd.Series(data))
            t.set_source(i["source"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.source, i["source"])

    def test_Tick_SetFromModel(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            data = {
                "code": i["code"],
                "price": i["price"],
                "volume": i["volume"],
                "timestamp": i["timestamp"],
            }
            df = pd.Series(data)
            mt = MTick()
            mt.set(df)
            mt.set_source(i["source"])
            t = Tick()
            t.set(mt.to_dataframe())
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
            self.assertEqual(t.source, i["source"])
