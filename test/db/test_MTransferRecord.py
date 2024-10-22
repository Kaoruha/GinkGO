import unittest
import uuid
import random
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MTransferRecord


class ModelTransferRecordTest(unittest.TestCase):
    """
    Unittest for Model TradeDay
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelTransferRecordTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MTransferRecord
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "direction": random.choice([i for i in TRANSFERDIRECTION_TYPES]),
                "market": random.choice([i for i in MARKET_TYPES]),
                "money": Decimal(str(round(random.uniform(0, 100), 2))),
                "status": random.choice([i for i in TRANSFERSTATUS_TYPES]),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelTransferRecord_Init(self) -> None:
        for i in self.params:
            o = self.model(
                portfolio_id=i["portfolio_id"],
                timestamp=i["timestamp"],
                direction=i["direction"],
                market=i["market"],
                money=i["money"],
                status=i["status"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.money, i["money"])
            self.assertEqual(o.status, i["status"])

    def test_ModelTransferRecord_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update portfolio_id
            o.update(i["portfolio_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])

            # Update timestamp
            o.update(i["portfolio_id"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

            # Update direction
            o.update(i["portfolio_id"], direction=i["direction"])
            self.assertEqual(o.direction, i["direction"])

            # Update market
            o.update(i["portfolio_id"], market=i["market"])
            self.assertEqual(o.market, i["market"])

            # Update money
            o.update(i["portfolio_id"], money=i["money"])
            self.assertEqual(o.money, i["money"])

            # Update status
            o.update(i["portfolio_id"], status=i["status"])
            self.assertEqual(o.status, i["status"])

            # Update source
            o.update(i["portfolio_id"], source=i["source"])
            self.assertEqual(o.source, i["source"])

        for i in self.params:
            o = self.model()
            o.update(
                i["portfolio_id"],
                timestamp=i["timestamp"],
                direction=i["direction"],
                market=i["market"],
                money=i["money"],
                status=i["status"],
                source=i["source"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.money, i["money"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.source, i["source"])

    def test_ModelTransferRecord_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = self.model()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.update(df)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.money, i["money"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.source, i["source"])
