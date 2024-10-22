import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
)

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MOrderRecord


class ModelOrderRecordTest(unittest.TestCase):
    """
    UnitTest for Order.
    """

    # Init
    # set data from bar

    def __init__(self, *args, **kwargs) -> None:
        super(ModelOrderRecordTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MOrderRecord
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "order_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "direction": random.choice([i for i in DIRECTION_TYPES]),
                "type": random.choice([i for i in ORDER_TYPES]),
                "status": random.choice([i for i in ORDERSTATUS_TYPES]),
                "volume": random.randint(0, 1000),
                "limit_price": Decimal(str(round(random.uniform(0, 100), 3))),
                "frozen": random.randint(0, 1000),
                "transaction_price": Decimal(str(round(random.uniform(0, 100), 3))),
                "remain": Decimal(str(round(random.uniform(0, 100), 3))),
                "fee": Decimal(str(round(random.uniform(0, 100), 3))),
                "timestamp": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelOrderRecord_Init(self) -> None:
        for i in self.params:
            o = self.model(
                portfolio_id=i["portfolio_id"],
                order_id=i["order_id"],
                code=i["code"],
                direction=i["direction"],
                type=i["type"],
                status=i["status"],
                volume=i["volume"],
                limit_price=i["limit_price"],
                frozen=i["frozen"],
                transaction_price=i["transaction_price"],
                remain=i["remain"],
                fee=i["fee"],
                timestamp=i["timestamp"],
                source=i["source"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.order_id, i["order_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrderRecord_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update uuid
            o.update(i["order_id"])
            self.assertEqual(o.order_id, i["order_id"])
            # Update portfolio_id
            o.update(i["order_id"], portfolio_id=i["portfolio_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            # Update code
            o.update(i["order_id"], code=i["code"])
            self.assertEqual(o.code, i["code"])
            # Update direction
            o.update(i["order_id"], direction=i["direction"])
            self.assertEqual(o.direction, i["direction"])
            # Update type
            o.update(i["order_id"], type=i["type"])
            self.assertEqual(o.type, i["type"])
            # Update status
            o.update(i["order_id"], status=i["status"])
            self.assertEqual(o.status, i["status"])
            # Update volume
            o.update(i["order_id"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])
            # Update limit_price
            o.update(i["order_id"], limit_price=i["limit_price"])
            self.assertEqual(o.limit_price, i["limit_price"])
            # Update frozen
            o.update(i["order_id"], frozen=i["frozen"])
            self.assertEqual(o.frozen, i["frozen"])
            # Update transaction_price
            o.update(i["order_id"], transaction_price=i["transaction_price"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            # Update remain
            o.update(i["order_id"], remain=i["remain"])
            self.assertEqual(o.remain, i["remain"])
            # Update fee
            o.update(i["order_id"], fee=i["fee"])
            self.assertEqual(o.fee, i["fee"])
            # Update timestamp
            o.update(i["order_id"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])
            # Update portfolio_id
            o.update(i["order_id"], source=i["source"])
            self.assertEqual(o.source, i["source"])

        for i in self.params:
            o = self.model()
            # Update all
            o.update(
                i["order_id"],
                i["portfolio_id"],
                i["code"],
                i["direction"],
                i["type"],
                i["status"],
                i["volume"],
                i["limit_price"],
                i["frozen"],
                i["transaction_price"],
                i["remain"],
                i["fee"],
                i["timestamp"],
                i["source"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])

    def test_ModelOrderRecord_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = self.model()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.update(df)
            self.assertEqual(o.order_id, i["order_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])
