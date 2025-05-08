import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime
from decimal import Decimal

from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MAnalyzerRecord


class ModelAnalyzerRecordTest(unittest.TestCase):
    """
    Examples for UnitTests of models Analyzer
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelAnalyzerRecordTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MAnalyzerRecord
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "value": Decimal(str(round(random.uniform(0, 100), 2))),
                "analyzer_id": uuid.uuid4().hex,
                "name": uuid.uuid4().hex,
            }
            for i in range(self.count)
        ]

    def test_ModelAnalyzerRecord_Init(self) -> None:
        for i in self.params:
            o = self.model(
                portfolio_id=i["portfolio_id"],
                engine_id=i["engine_id"],
                timestamp=i["timestamp"],
                value=i["value"],
                analyzer_id=i["analyzer_id"],
                name=i["name"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.value, i["value"])
            self.assertEqual(o.analyzer_id, i["analyzer_id"])
            self.assertEqual(o.name, i["name"])

    def test_ModelAnalyzerRecord_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            o.update(i["portfolio_id"], i["engine_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            o.update(i["portfolio_id"], i["engine_id"], timestamp=i["timestamp"])
            self.assertEqual(i["timestamp"], o.timestamp)

            o.update(i["portfolio_id"], i["engine_id"], value=i["value"])
            self.assertEqual(o.value, i["value"])

            o.update(i["portfolio_id"], i["engine_id"], name=i["name"])
            self.assertEqual(o.name, i["name"])

            o.update(i["portfolio_id"], i["engine_id"], analyzer_id=i["analyzer_id"])
            self.assertEqual(o.analyzer_id, i["analyzer_id"])
        for i in self.params:
            o = self.model()
            o.update(
                i["portfolio_id"],
                engine_id=i["engine_id"],
                timestamp=i["timestamp"],
                value=i["value"],
                analyzer_id=i["analyzer_id"],
                name=i["name"],
            )
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.engine_id, i["engine_id"])
            self.assertEqual(o.timestamp, i["timestamp"])
            self.assertEqual(o.value, i["value"])
            self.assertEqual(o.analyzer_id, i["analyzer_id"])
            self.assertEqual(o.name, i["name"])

    def test_ModelAnalyzerRecord_SetFromDataFrame(self) -> None:
        # TODO
        pass
