import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime

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
from ginkgo.data.models import MSignal


class ModelSignalTest(unittest.TestCase):
    """
    Signals for UnitTests of models
    """

    # Init
    # set data from bar

    def __init__(self, *args, **kwargs) -> None:
        super(ModelSignalTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MSignal
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "code": uuid.uuid4().hex,
                "direction": random.choice([DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]),
                "reason": "reason",
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelSignal_Init(self) -> None:
        for i in self.params:
            o = self.model(
                portfolio_id=i["portfolio_id"],
                engine_id=i["engine_id"],
                timestamp=i["timestamp"],
                code=i["code"],
                direction=i["direction"],
                reason=i["reason"],
                source=i["source"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.reason, i["reason"])
            self.assertEqual(o.source, i["source"])

    def test_ModelSignal_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update portidy
            o.update(i["portfolio_id"], i["engine_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])

            # Update timestamp
            o.update(i["portfolio_id"], i["engine_id"], timestamp=i["timestamp"])
            self.assertEqual(o.timestamp, i["timestamp"])

            # Update code
            o.update(i["portfolio_id"], i["engine_id"], code=i["code"])
            self.assertEqual(o.code, i["code"])

            # Update direction
            o.update(i["portfolio_id"], i["engine_id"], direction=i["direction"])
            self.assertEqual(o.direction, i["direction"])

            # Update reason
            o.update(i["portfolio_id"], i["engine_id"], reason=i["reason"])
            self.assertEqual(o.reason, i["reason"])

            # Update source
            o.update(i["portfolio_id"], i["engine_id"], source=i["source"])
            self.assertEqual(o.source, i["source"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(
                i["portfolio_id"],
                i["engine_id"],
                timestamp=i["timestamp"],
                code=i["code"],
                direction=i["direction"],
                reason=i["reason"],
                source=i["source"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.reason, i["reason"])
            self.assertEqual(o.source, i["source"])

    def test_ModelSignal_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.direction, i["direction"])
            self.assertEqual(o.reason, i["reason"])
            self.assertEqual(o.source, i["source"])
