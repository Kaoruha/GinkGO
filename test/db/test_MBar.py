import unittest
import uuid
import random
import time
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import (
    SOURCE_TYPES,
    FREQUENCY_TYPES,
)

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MBar

from ginkgo.backtest.bar import Bar


class ModelBarTest(unittest.TestCase):
    """
    UnitTest for Bar.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelBarTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MBar
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
            }
            for i in range(self.count)
        ]

    def test_ModelBar_Init(self) -> None:
        for i in self.params:
            o = self.model(
                code=i["code"],
                open=i["open"],
                high=i["high"],
                low=i["low"],
                close=i["close"],
                volume=i["volume"],
                amount=i["amount"],
                frequency=i["frequency"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.amount, i["amount"])
            self.assertEqual(o.frequency, i["frequency"])

    def test_ModelBar_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            o.update(i["code"])
            self.assertEqual(o.code, i["code"])
            o.update(i["code"], open=i["open"])
            self.assertEqual(o.open, i["open"])
            o.update(i["code"], high=i["high"])
            self.assertEqual(o.high, i["high"])
            o.update(i["code"], low=i["low"])
            self.assertEqual(o.low, i["low"])
            o.update(i["code"], close=i["close"])
            self.assertEqual(o.close, i["close"])
            o.update(i["code"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])
            o.update(i["code"], amount=i["amount"])
            self.assertEqual(o.amount, i["amount"])
            o.update(i["code"], frequency=i["frequency"])
            self.assertEqual(o.frequency, i["frequency"])
            o.update(i["code"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

        for i in self.params:
            o = self.model()
            o.update(
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
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.amount, i["amount"])
            self.assertEqual(o.timestamp, i["timestamp"])

    def test_ModelBar_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.open, i["open"])
            self.assertEqual(o.high, i["high"])
            self.assertEqual(o.low, i["low"])
            self.assertEqual(o.close, i["close"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.amount, i["amount"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])
