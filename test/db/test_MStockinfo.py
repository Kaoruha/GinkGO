import unittest
import uuid
import base64
import random
import time
import pandas as pd
import datetime

from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES

from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.data.models import MStockInfo


class ModelStockInfoTest(unittest.TestCase):
    """
    UnitTest for StockInfo.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(ModelStockInfoTest, self).__init__(*args, **kwargs)
        self.count = 10
        self.model = MStockInfo
        self.params = [
            {
                "code": uuid.uuid4().hex,
                "code_name": uuid.uuid4().hex,
                "industry": uuid.uuid4().hex,
                "currency": random.choice([i for i in CURRENCY_TYPES]),
                "market": random.choice([i for i in MARKET_TYPES]),
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(self.count)
        ]

    def test_ModelStockInfo_Init(self) -> None:
        for i in self.params:
            o = self.model(
                code=i["code"],
                code_name=i["code_name"],
                industry=i["industry"],
                currency=i["currency"],
                market=i["market"],
                list_date=i["list_date"],
                delist_date=i["delist_date"],
                source=i["source"],
            )
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_SetFromData(self) -> None:
        for i in self.params:
            o = self.model()
            # Update code
            o.update(i["code"])
            self.assertEqual(o.code, i["code"])

            # Update code_name
            o.update(i["code"], code_name=i["code_name"])
            self.assertEqual(o.code_name, i["code_name"])

            # Update industry
            o.update(i["code"], industry=i["industry"])
            self.assertEqual(o.industry, i["industry"])

            # Update currency
            o.update(i["code"], currency=i["currency"])
            self.assertEqual(o.currency, i["currency"])

            # Update market
            o.update(i["code"], market=i["market"])
            self.assertEqual(o.market, i["market"])

            # Update list_date
            o.update(i["code"], list_date=i["list_date"])
            self.assertEqual(o.list_date, i["list_date"])

            # Update delist_date
            o.update(i["code"], delist_date=i["delist_date"])
            self.assertEqual(o.delist_date, i["delist_date"])

            # Update source
            o.update(i["code"], source=i["source"])
            self.assertEqual(o.source, i["source"])

    def test_ModelStockInfo_SetFromDataFrame(self) -> None:
        for i in self.params:
            o = self.model()
            df = pd.DataFrame.from_dict(i, orient="index")[0]
            o.update(df)
            self.assertEqual(o.code, i["code"])
            self.assertEqual(o.code_name, i["code_name"])
            self.assertEqual(o.industry, i["industry"])
            self.assertEqual(o.currency, i["currency"])
            self.assertEqual(o.market, i["market"])
            self.assertEqual(o.list_date, i["list_date"])
            self.assertEqual(o.delist_date, i["delist_date"])
            self.assertEqual(o.source, i["source"])
