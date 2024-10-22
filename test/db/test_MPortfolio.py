import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.models import MPortfolio


class ModelPortfolioTest(unittest.TestCase):
    """
    Examples for UnitTests of models Backtest
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelPortfolioTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MPortfolio
        self.params = [
            {
                "name": uuid.uuid4().hex,
                "backtest_start_date": datetime.datetime.now(),
                "backtest_end_date": datetime.datetime.now(),
                "is_live": random.choice([True, False]),
            }
            for i in range(self.count)
        ]

    def test_ModelPortfolio_Init(self) -> None:
        for i in self.params:
            o = self.model(
                name=i["name"],
                backtest_start_date=i["backtest_start_date"],
                backtest_end_date=i["backtest_end_date"],
                is_live=i["is_live"],
            )
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.backtest_start_date, i["backtest_start_date"])
            self.assertEqual(o.backtest_end_date, i["backtest_end_date"])
            self.assertEqual(o.is_live, i["is_live"])

    def test_ModelPortfolio_SetFromData(self) -> None:
        for i in self.params:
            # Update name
            o = self.model()
            o.update(i["name"])
            self.assertEqual(o.name, i["name"])
            # Update start at
            o.update(i["name"], backtest_start_date=i["backtest_start_date"])
            self.assertEqual(o.backtest_start_date, i["backtest_start_date"])
            # Update end at
            o.update(i["name"], backtest_end_date=i["backtest_end_date"])
            self.assertEqual(o.backtest_end_date, i["backtest_end_date"])
            # Update is_live
            o.update(i["name"], is_live=i["is_live"])
            self.assertEqual(o.is_live, i["is_live"])
        # Update all
        for i in self.params:
            o = self.model()
            o.update(
                i["name"],
                backtest_start_date=i["backtest_start_date"],
                backtest_end_date=i["backtest_end_date"],
                is_live=i["is_live"],
            )

            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.backtest_start_date, i["backtest_start_date"])
            self.assertEqual(o.backtest_end_date, i["backtest_end_date"])
            self.assertEqual(o.is_live, i["is_live"])

    def test_ModelPortfolio_SetFromDataFrame(self) -> None:
        for i in self.params:
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o = self.model()
            o.update(df)
            self.assertEqual(o.name, i["name"])
            self.assertEqual(o.backtest_start_date, i["backtest_start_date"])
            self.assertEqual(o.backtest_end_date, i["backtest_end_date"])
            self.assertEqual(o.is_live, i["is_live"])
