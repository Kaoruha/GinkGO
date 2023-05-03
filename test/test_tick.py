import unittest
import time
import datetime
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.tick import Tick
from ginkgo.libs.ginkgo_conf import GINKGOCONF


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
            },
            {
                "code": "sh.0000001",
                "price": 10,
                "volume": 10022,
                "timestamp": datetime.datetime.now(),
            },
        ]

    def test_TickInit(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            code = i["code"]
            price = i["price"]
            volume = i["volume"]
            timestamp = i["timestamp"]
            t = Tick(code, price, volume, timestamp)
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])

    def test_TickSet(self) -> None:
        time.sleep(GINKGOCONF.HEARTBEAT)
        for i in self.params:
            t = Tick()
            t.set(i["code"], i["price"], i["volume"], i["timestamp"])
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])

    def test_TickSetFromDF(self) -> None:
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
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])

    def test_TickSetFromModel(self) -> None:
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
            self.assertEqual(t.code, i["code"])
            self.assertEqual(t.price, i["price"])
            self.assertEqual(t.volume, i["volume"])
