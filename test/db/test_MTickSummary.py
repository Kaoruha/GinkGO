import unittest
import random
import uuid
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MTickSummary


class ModelTickSummaryTest(unittest.TestCase):
    """
    UnitTest for ModelTickSummary.
    """

    # Init
    # set data from dataframe

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTickSummaryTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MTickSummary
        self.params = [
            {
                "code": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "price": Decimal(str(random.uniform(0, 100))),
                "volume": random.randint(0, 1000),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelTickSummary_Init(self) -> None:
        for i in self.params:
            o = self.model(**i)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.price, i["price"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTickSummary_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update code
            o.update(i["code"])
            self.assertEqual(o.code, i["code"])

            # Update Price
            o.update(i["code"], price=i["price"])
            self.assertEqual(o.price, i["price"])

            # Update volume
            o.update(i["code"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])

            # Update timestamp
            o.update(i["code"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

            # Update source
            o.update(i["code"], source=i["source"])
            self.assertEqual(o.source, i["source"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(
                i["code"],
                price=i["price"],
                volume=i["volume"],
                timestamp=i["timestamp"],
                source=i["source"],
            )
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["price"], o.price)
            self.assertEqual(i["volume"], o.volume)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["source"], o.source)

    def test_ModelTickSummary_SetFromDataframe(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["price"], o.price)
            self.assertEqual(i["volume"], o.volume)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["source"], o.source)
