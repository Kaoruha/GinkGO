import unittest
import uuid
import pandas as pd
import datetime
import random
from time import sleep
from decimal import Decimal
from ginkgo.backtest.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG


class BarTest(unittest.TestCase):
    """
    Unit test for Bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BarTest, self).__init__(*args, **kwargs)
        self.dev = False

        self.params = [
            {
                "code": uuid.uuid4().hex,
                "open": Decimal(str(round(random.uniform(0, 100), 2))),
                "high": Decimal(str(round(random.uniform(0, 100), 3))),
                "low": Decimal(str(round(random.uniform(0, 100), 2))),
                "close": Decimal(str(round(random.uniform(0, 100), 2))),
                "volume": random.randint(0, 1000),
                "amount": Decimal(str(round(random.uniform(0, 100), 2))),
                "frequency": random.choice([i for i in FREQUENCY_TYPES]),
                "timestamp": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            },
        ]

    def test_Bar_Init(self) -> None:
        for i in self.params:
            b = Bar()
        self.assertTrue(True)

    def test_Bar_Set(self) -> None:
        for i in self.params:
            b = Bar()
            b.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["amount"],
                i["frequency"],
                i["timestamp"],
            )
            b.set_source(i["source"])
            self.assertEqual(b.code, i["code"])
            self.assertEqual(b.open, i["open"])
            self.assertEqual(b.high, i["high"])
            self.assertEqual(b.low, i["low"])
            self.assertEqual(b.close, i["close"])
            self.assertEqual(b.volume, i["volume"])
            self.assertEqual(b.amount, i["amount"])
            self.assertEqual(b.source, i["source"])
            self.assertEqual(b.timestamp, datetime_normalize(i["timestamp"]))
            self.assertEqual(b.frequency, i["frequency"])

    def test_Bar_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame(i, index=[0])
            df = df.iloc[0]
            b = Bar()
            b.set(df)
            b.set_source(i["source"])
            self.assertEqual(b.code, df["code"])
            self.assertEqual(b.open, df["open"])
            self.assertEqual(b.high, df["high"])
            self.assertEqual(b.low, df["low"])
            self.assertEqual(b.close, df["close"])
            self.assertEqual(b.amount, df["amount"])
            self.assertEqual(b.volume, df["volume"])
            self.assertEqual(b.source, df["source"])
            self.assertEqual(b.timestamp, datetime_normalize(df["timestamp"]))
            self.assertEqual(b.frequency, df["frequency"])

    def test_Bar_Change(self) -> None:
        for i in self.params:
            b = Bar()
            b.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["amount"],
                i["frequency"],
                i["timestamp"],
            )
            b.set_source(i["source"])
            r_expect = round(i["close"] - i["open"], 2)
            self.assertEqual(b.chg, r_expect)

    def test_Bar_Amplitude(self) -> None:
        for i in self.params:
            b = Bar()
            b.set(
                i["code"],
                i["open"],
                i["high"],
                i["low"],
                i["close"],
                i["volume"],
                i["amount"],
                i["frequency"],
                i["timestamp"],
            )
            b.set_source(i["source"])
            self.assertEqual(b.amplitude, i["high"] - i["low"])
