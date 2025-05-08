import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MPosition


class ModelPositionTest(unittest.TestCase):
    """
    UnitTest for ModelPosition.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelPositionTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MPosition
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "cost": Decimal(str(round(random.uniform(0, 20), 2))),
                "volume": random.randint(0, 1000),
                "frozen_volume": random.randint(0, 1000),
                "frozen_money": Decimal(str(round(random.uniform(0, 20), 2))),
                "price": Decimal(str(round(random.uniform(0, 20), 2))),
                "fee": Decimal(str(round(random.uniform(0, 20), 2))),
            }
            for i in range(self.count)
        ]

    def test_ModelPosition_Init(self) -> None:
        for i in self.params:
            o = self.model(**i)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.frozen_volume, i["frozen_volume"])
            self.assertEqual(o.cost, i["cost"])

    def test_ModelPosition_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update portfolio_id
            o.update(i["portfolio_id"], i["engine_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])

            # Update code
            o.update(i["portfolio_id"], i["engine_id"], code=i["code"])
            self.assertEqual(o.code, i["code"])

            # Update volume
            o.update(i["portfolio_id"], i["engine_id"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])

            # Update frozen_volume
            o.update(i["portfolio_id"], i["engine_id"], frozen_volume=i["frozen_volume"])
            self.assertEqual(o.frozen_volume, i["frozen_volume"])

            # Update frozen_money
            o.update(i["portfolio_id"], i["engine_id"], frozen_money=i["frozen_money"])
            self.assertEqual(o.frozen_money, i["frozen_money"])

            # Update cost
            o.update(i["portfolio_id"], i["engine_id"], cost=i["cost"])
            self.assertEqual(o.cost, i["cost"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(
                i["portfolio_id"],
                i["engine_id"],
                code=i["code"],
                volume=i["volume"],
                frozen_volume=i["frozen_volume"],
                frozen_money=i["frozen_money"],
                cost=i["cost"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.frozen_volume, i["frozen_volume"])
            self.assertEqual(o.frozen_money, i["frozen_money"])
            self.assertEqual(o.cost, i["cost"])

    def test_ModelPosition_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.frozen_volume, i["frozen_volume"])
            self.assertEqual(o.frozen_money, i["frozen_money"])
            self.assertEqual(o.cost, i["cost"])
