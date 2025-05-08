import unittest
import uuid
import random
import datetime
import time
from ginkgo.data.models import MStockInfo
from ginkgo.backtest.stockinfo import StockInfo
from ginkgo.data.operations.stockinfo_crud import *
from ginkgo.data.drivers import create_table, drop_table, get_table_size
from ginkgo.enums import CURRENCY_TYPES, MARKET_TYPES

from src.ginkgo.data.drivers import add, add_all, get_click_connection, GinkgoClickhouse


class OperationStockinfoTest(unittest.TestCase):
    """
    UnitTest for Stockinfo CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MStockInfo
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "code": uuid.uuid4().hex,
                "code_name": uuid.uuid4().hex,
                "industry": uuid.uuid4().hex,
                "currency": random.choice([i for i in CURRENCY_TYPES]),
                "market": random.choice([i for i in MARKET_TYPES]),
                "list_date": datetime.datetime.now(),
                "delist_date": datetime.datetime.now(),
            }
            for i in range(cls.count)
        ]

    def test_OperationStockinfo_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_stockinfo(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationStockinfo_bulkinsert(self) -> None:
        l = []
        for i in self.params:
            item = MStockInfo(**i)
            l.append(item)
        size0 = get_table_size(self.model)
        add_stockinfos(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationStockinfo_upsert(self) -> None:
        for i in self.params:
            params_copy = i.copy()
            new_code = uuid.uuid4().hex
            params_copy["code"] = new_code

            size0 = get_table_size(self.model)
            # 1st upsert, do insert
            res = upsert_stockinfo(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            time.sleep(0.01)
            df = get_stockinfo(new_code).iloc[0]
            self.assertEqual(df["code"], params_copy["code"])
            self.assertEqual(df["code_name"], params_copy["code_name"])
            self.assertEqual(df["industry"], params_copy["industry"])
            self.assertEqual(df["currency"], params_copy["currency"])
            self.assertEqual(df["market"], params_copy["market"])

            new_code_name = uuid.uuid4().hex
            params_copy["code_name"] = new_code_name
            new_industry = uuid.uuid4().hex
            params_copy["industry"] = new_industry
            new_currency = random.choice([i for i in CURRENCY_TYPES])
            params_copy["currency"] = new_currency
            new_market = random.choice([i for i in MARKET_TYPES])
            params_copy["market"] = new_market
            new_list_date = "2020-01-01"
            params_copy["list_date"] = new_list_date
            new_delist_date = "2020-05-01"
            params_copy["delist_date"] = new_delist_date

            # 2nd upsert, do update
            res2 = upsert_stockinfo(**params_copy)
            time.sleep(0.02)
            df = get_stockinfo(new_code).iloc[0]
            print(df)
            self.assertEqual(df["code"], new_code)
            self.assertEqual(df["code_name"], new_code_name)
            self.assertEqual(df["industry"], new_industry)
            self.assertEqual(df["currency"], new_currency)
            self.assertEqual(df["market"], new_market)

    def test_OperationStockinfo_delete(self) -> None:
        for i in range(self.count):
            size0 = get_table_size(self.model)
            res = add_stockinfo(
                code=uuid.uuid4().hex,
                code_name=uuid.uuid4().hex,
                industry=uuid.uuid4().hex,
                currency=random.choice([i for i in CURRENCY_TYPES]),
                market=random.choice([i for i in MARKET_TYPES]),
                list_date=datetime.datetime.now(),
                delist_date=datetime.datetime.now(),
            )
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_stockinfo(res["code"])
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationStockinfo_softdelete(self) -> None:
        for i in range(self.count):
            size0 = get_table_size(self.model)
            res = add_stockinfo(
                code=uuid.uuid4().hex,
                code_name=uuid.uuid4().hex,
                industry=uuid.uuid4().hex,
                currency=random.choice([i for i in CURRENCY_TYPES]),
                market=random.choice([i for i in MARKET_TYPES]),
                list_date=datetime.datetime.now(),
                delist_date=datetime.datetime.now(),
            )
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            softdelete_stockinfo(res["code"])
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

            delete_stockinfo(res["code"])
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size2)

    def test_OperationStockinfo_update(self) -> None:
        # TODO
        pass

    def test_OperationStockinfo_filtered_code(self) -> None:
        l = []
        new_code = uuid.uuid4().hex
        size0 = get_table_size(self.model)
        for i in self.params:
            params_copy = i.copy()
            params_copy["code"] = new_code
            item = MStockInfo(**params_copy)
            l.append(item)
        add_stockinfos(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        res = get_stockinfos_filtered(code=new_code)
        self.assertEqual(self.count, len(res))
        df = get_stockinfos_filtered(code=new_code, as_dataframe=True)
        self.assertEqual(self.count, df.shape[0])

    def test_OperationStockinfo_filtered_industry(self) -> None:
        l = []
        new_industry = uuid.uuid4().hex
        size0 = get_table_size(self.model)
        for i in self.params:
            params_copy = i.copy()
            params_copy["industry"] = new_industry
            item = MStockInfo(**params_copy)
            l.append(item)
        add_stockinfos(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        df = get_stockinfos_filtered(industry=new_industry)
        self.assertEqual(self.count, df.shape[0])

    def test_OperationStockinfo_get_by_listdate(self) -> None:
        # TODO
        pass

    def test_OperationStockinfo_get_by_delistdate(self) -> None:
        # TODO
        pass

    def test_OperationStockinfo_filtered_fuzzy(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        key0 = uuid.uuid4().hex[:3]
        key1 = uuid.uuid4().hex[:3]
        key2 = uuid.uuid4().hex[:3]
        for i in self.params:
            params_copy = i.copy()
            params_copy["code"] = f"{key0}{uuid.uuid4().hex[:10]}"
            params_copy["code_name"] = f"{key1}{uuid.uuid4().hex[:10]}"
            params_copy["industry"] = f"{key2}{uuid.uuid4().hex[:10]}"
            item = MStockInfo(**params_copy)
            l.append(item)
        add_stockinfos(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        df = fget_stockinfos(filter=key0)
        self.assertLessEqual(self.count, df.shape[0])
        df = fget_stockinfos(filter=key1)
        self.assertLessEqual(self.count, df.shape[0])
        df = fget_stockinfos(filter=key2)
        self.assertLessEqual(self.count, df.shape[0])
