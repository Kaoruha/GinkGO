import unittest
import random
import uuid
import time
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
    MARKET_TYPES,
)

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MOrder

from ginkgo.backtest.order import Order


class ModelOrderTest(unittest.TestCase):
    """
    UnitTest for Order.
    """

    # Init
    # set data from bar

    def __init__(self, *args, **kwargs) -> None:
        super(ModelOrderTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MOrder
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "uuid": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "direction": random.choice([i for i in DIRECTION_TYPES]),
                "order_type": random.choice([i for i in ORDER_TYPES]),
                "status": random.choice([i for i in ORDERSTATUS_TYPES]),
                "volume": random.randint(0, 1000),
                "limit_price": Decimal(str(round(random.uniform(0, 100), 2))),
                "frozen": random.randint(0, 1000),
                "transaction_price": Decimal(str(round(random.uniform(0, 100), 2))),
                "transaction_volume": random.randint(0, 1000),
                "remain": Decimal(str(round(random.uniform(0, 100), 2))),
                "fee": Decimal(str(round(random.uniform(0, 100), 2))),
                "timestamp": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelOrder_Init(self) -> None:
        for i in self.params:
            o = self.model(**i)

            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.uuid, i["uuid"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.order_type, i["order_type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.transaction_volume, i["transaction_volume"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])

    def test_ModelOrder_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            o.set_source(i["source"])
            self.assertEqual(o.source, i["source"])
            # Update uuid
            o.update(i["portfolio_id"], i["engine_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            # Update code
            o.update(i["portfolio_id"], i["engine_id"], code=i["code"])
            self.assertEqual(o.code, i["code"])
            # Update direction
            o.update(i["portfolio_id"], i["engine_id"], direction=i["direction"])
            self.assertEqual(o.direction, i["direction"])
            # Update type
            o.update(i["portfolio_id"], i["engine_id"], order_type=i["order_type"])
            self.assertEqual(o.order_type, i["order_type"])
            # Update status
            o.update(i["portfolio_id"], i["engine_id"], status=i["status"])
            self.assertEqual(o.status, i["status"])
            # Update volume
            o.update(i["portfolio_id"], i["engine_id"], volume=i["volume"])
            self.assertEqual(o.volume, i["volume"])
            # Update limit_price
            o.update(i["portfolio_id"], i["engine_id"], limit_price=i["limit_price"])
            self.assertEqual(o.limit_price, i["limit_price"])
            # Update frozen
            o.update(i["portfolio_id"], i["engine_id"], frozen=i["frozen"])
            self.assertEqual(o.frozen, i["frozen"])
            # Update transaction_price
            o.update(i["portfolio_id"], i["engine_id"], transaction_price=i["transaction_price"])
            self.assertEqual(o.transaction_price, i["transaction_price"])

            # Update transaction_volume
            o.update(i["portfolio_id"], i["engine_id"], transaction_volume=i["transaction_volume"])
            self.assertEqual(o.transaction_volume, i["transaction_volume"])
            # Update remain
            o.update(i["portfolio_id"], i["engine_id"], remain=i["remain"])
            self.assertEqual(o.remain, i["remain"])
            # Update fee
            o.update(i["portfolio_id"], i["engine_id"], fee=i["fee"])
            self.assertEqual(o.fee, i["fee"])
            # Update timestamp
            o.update(i["portfolio_id"], i["engine_id"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(
                i["portfolio_id"],
                i["engine_id"],
                i["uuid"],
                i["code"],
                i["direction"],
                i["order_type"],
                i["status"],
                i["volume"],
                i["limit_price"],
                i["frozen"],
                i["transaction_price"],
                i["transaction_volume"],
                i["remain"],
                i["fee"],
                i["timestamp"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.order_type, i["order_type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.transaction_volume, i["transaction_volume"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])

    def test_ModelOrder_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = self.model()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.update(df)
            o.set_source(i["source"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.uuid, i["uuid"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.order_type, i["order_type"])
            self.assertEqual(o.status, i["status"])
            self.assertEqual(o.volume, i["volume"])
            self.assertEqual(o.limit_price, i["limit_price"])
            self.assertEqual(o.frozen, i["frozen"])
            self.assertEqual(o.transaction_price, i["transaction_price"])
            self.assertEqual(o.transaction_volume, i["transaction_volume"])
            self.assertEqual(o.remain, i["remain"])
            self.assertEqual(o.fee, i["fee"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.source, i["source"])
