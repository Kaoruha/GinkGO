import unittest
import random
import uuid
import time

from ginkgo.enums import MARKET_TYPES
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.data.models import MTradeDay
from ginkgo.data.operations.tradeday_crud import *


class OperationTradedayTest(unittest.TestCase):
    """
    UnitTest for Tradeday CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MTradeDay
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "timestamp": datetime.datetime.now(),
                "is_open": random.choice([True, False]),
                "market": random.choice([i for i in MARKET_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationTradeday_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationTradeday_bulkinsert(self) -> None:
        size0 = get_table_size(self.model)
        l = []
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_tradedays(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationTradeday_update(self) -> None:
        # no need to update
        pass

    def test_OperationTradeday_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_tradeday(res["uuid"])
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationTradeday_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_tradeday(res["uuid"])
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationTradeday_delete_by_market_and_date_range(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

        for i in [j for j in MARKET_TYPES]:
            size2 = get_table_size(self.model)
            df = get_tradedays(market=i)
            delete_tradedays(market=i)
            size3 = get_table_size(self.model)
            self.assertEqual(size2 - size3, df.shape[0])

    def test_OperationTradeday_softdelete_by_market_and_date_range(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

        for i in [j for j in MARKET_TYPES]:
            size2 = get_table_size(self.model)
            df = get_tradedays(market=i)
            softdelete_tradedays(market=i)
            size3 = get_table_size(self.model)
            self.assertEqual(size2 - size3, df.shape[0])

    def test_OperatioTradeday_get_by_id(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_tradeday(res["uuid"])
            self.assertEqual(df["market"], i["market"])
            self.assertEqual(df["is_open"], i["is_open"])

    #     def test_OperationTradeday_get_by_date_range(self) -> None:
    #         for i in self.params:
    #             size0 = get_table_size(self.model)
    #             add_tradeday(
    #                 market=i["market"],
    #                 is_open=i["is_open"],
    #                 timestamp=i["timestamp"],
    #             )
    #             size1 = get_table_size(self.model)
    #             self.assertEqual(size1 - size0, 1)

    #         data = get_tradeday_by_market_and_date_range(MARKET_TYPES.CHINA, "2020-01-01", "2020-01-02")
    #         df = get_tradeday_by_market_and_date_range(MARKET_TYPES.CHINA, "2020-01-01", "2020-01-02", as_dataframe=True)
    #         self.assertEqual(2, len(data))
    #         self.assertEqual(2, df.shape[0])
    #         data = get_tradeday_by_market_and_date_range(
    #             market=MARKET_TYPES.CHINA, start_date="2020-01-01", end_date="2020-01-03", page=0, page_size=2
    #         )
    #         df = get_tradeday_by_market_and_date_range(
    #             market=MARKET_TYPES.CHINA,
    #             start_date="2020-01-01",
    #             end_date="2020-01-03",
    #             as_dataframe=True,
    #             page=0,
    #             page_size=2,
    #         )
    #         self.assertEqual(2, len(data))
    #         self.assertEqual(2, df.shape[0])
    #         data = get_tradeday_by_market_and_date_range(
    #             market=MARKET_TYPES.CHINA, start_date="2020-01-01", end_date="2020-01-03", page=1, page_size=2
    #         )
    #         df = get_tradeday_by_market_and_date_range(
    #             market=MARKET_TYPES.CHINA,
    #             start_date="2020-01-01",
    #             end_date="2020-01-03",
    #             as_dataframe=True,
    #             page=1,
    #             page_size=2,
    #         )
    #         self.assertEqual(1, len(data))
    #         self.assertEqual(1, df.shape[0])

    def test_OperationTradeday_exists(self) -> None:
        pass

    def test_OperationTradeday_exceptions(self) -> None:
        pass
