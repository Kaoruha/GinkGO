import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime
from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MPortfolioFileMapping
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES


class ModelPortfolioFileMappingTest(unittest.TestCase):
    """
    Examples for UnitTests of models Backtest
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelPortfolioFileMappingTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MPortfolioFileMapping
        self.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "file_id": uuid.uuid4().hex,
                "name": uuid.uuid4().hex,
                "type": random.choice([i for i in FILE_TYPES]),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelPortfoliofileMapping_Init(self) -> None:
        for i in self.params:
            o = self.model(portfolio_id=i["portfolio_id"], file_id=i["file_id"], name=i["name"], type=i["type"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.file_id, i["file_id"])
            self.assertEqual(o.name, i["name"])

    def test_ModelPortfoliofileMapping_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # update portfolio_id
            o.update(i["portfolio_id"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])

            # update file_id
            o.update(i["portfolio_id"], file_id=i["file_id"])
            self.assertEqual(o.file_id, i["file_id"])

            # update map name
            o.update(i["portfolio_id"], name=i["name"])
            self.assertEqual(o.name, i["name"])

            o.update(i["portfolio_id"], type=i["type"])
            self.assertEqual(o.type, i["type"])

        # Update all
        for i in self.params:
            o = self.model()
            o.update(i["portfolio_id"], file_id=i["file_id"], name=i["name"], type=i["type"])
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.file_id, i["file_id"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.type, i["type"])

    def test_ModelPortfoliofileMapping_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.portfolio_id, i["portfolio_id"])
            self.assertEqual(o.file_id, i["file_id"])
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.type, i["type"])
            self.assertEqual(o.source, i["source"])
