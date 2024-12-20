import unittest
import random
import uuid
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MPositionRecord


class ModelPositionRecordTest(unittest.TestCase):
    """
    UnitTest for ModelPositionRecord.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelPositionRecordTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MPositionRecord
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "code": uuid.uuid4().hex,
                "volume": random.randint(0, 1000),
                "frozen": random.randint(0, 1000),
                "cost": Decimal(str(round(random.uniform(0, 20), 1))),
            }
            for i in range(self.count)
        ]

    def test_ModelPositionRecord_Init(self) -> None:
        for i in self.params:
            o = self.model(**i)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.cost, i["cost"])

    def test_ModelPositionRecord_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update portfolio_id
            o.update(i["portfolio_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])

            # Update timestamp
            o.update(i["portfolio_id"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

            # Update code
            o.update(i["portfolio_id"], code=i["code"])
            self.assertEqual(o.code, i["code"])

            # Update volume
            o.update(i["portfolio_id"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])

            # Update cost
            o.update(i["portfolio_id"], cost=i["cost"])
            self.assertEqual(o.cost, i["cost"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(i["portfolio_id"], code=i["code"], volume=i["volume"], cost=i["cost"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.cost, i["cost"])

    def test_ModelPositionRecord_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.cost, i["cost"])
