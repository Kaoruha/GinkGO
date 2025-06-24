import unittest
import random
import uuid
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MTick


class ModelTickTest(unittest.TestCase):
    """
    UnitTest for ModelTick.
    """

    # Init
    # set data from dataframe

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTickTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MTick
        self.params = [
            {
                "code": uuid.uuid4().hex,
                "price": Decimal(str(round(random.uniform(0, 20), 1))),
                "volume": random.randint(0, 1000),
                "direction": random.choice([i for i in TICKDIRECTION_TYPES]),
                "timestamp": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelTick_Init(self) -> None:
        for i in self.params:
            o = self.model(**i)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.price, i["price"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTick_SetFromData(self) -> None:
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

            # Update direction
            o.update(i["code"], direction=i["direction"])
            self.assertEqual(o.direction, i["direction"])

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
                direction=i["direction"],
                timestamp=i["timestamp"],
                source=i["source"],
            )
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["price"], o.price)
            self.assertEqual(i["volume"], o.volume)
            self.assertEqual(i["direction"], o.direction)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["source"], o.source)

    def test_ModelTick_SetFromDataframe(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(i["code"], o.code)
            self.assertEqual(i["price"], o.price)
            self.assertEqual(i["volume"], o.volume)
            self.assertEqual(i["direction"], o.direction)
            self.assertEqual(i["timestamp"], o.timestamp)
            self.assertEqual(i["source"], o.source)
