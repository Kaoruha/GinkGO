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
        cls.count = random.randint(20, 50)
        cls.params = [
            {
                "timestamp": datetime.datetime.now(),
                "uuid": uuid.uuid4().hex,
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
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationTradeday_delete_filtered(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

        for i in [j for j in MARKET_TYPES]:
            size2 = get_table_size(self.model)
            df = get_tradedays_page_filtered(market=i)
            delete_tradedays_filtered(market=i)
            size3 = get_table_size(self.model)
            self.assertEqual(size2 - size3, df.shape[0])

    def test_OperationTradeday_softdelete_filtered(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

        for i in [j for j in MARKET_TYPES]:
            size2 = get_table_size(self.model)
            df = get_tradedays_page_filtered(market=i)
            softdelete_tradedays_filtered(market=i)
            size3 = get_table_size(self.model)
            self.assertEqual(size2 - size3, 0)
            df = get_tradedays_page_filtered(market=i)
            self.assertEqual(0, df.shape[0])

    def test_OperatioTradeday_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tradeday(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            res = get_tradeday(res["uuid"])
            self.assertEqual(res.market, i["market"])
            self.assertEqual(res.is_open, i["is_open"])

    def test_OperationTradeday_get_filtered(self) -> None:
        # TODO
        pass

    def test_OperationTradeday_exists(self) -> None:
        pass

    def test_OperationTradeday_exceptions(self) -> None:
        pass
