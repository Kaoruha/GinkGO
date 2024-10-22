import unittest
import time
import datetime
import random
import uuid


from ginkgo.data.models import MPortfolio
from ginkgo.data.drivers import create_table, drop_table, get_table_size
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize
from ginkgo.data.operations.portfolio_crud import *


class OperationPortfolioTest(unittest.TestCase):
    """
    UnitTest for Order CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MPortfolio
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "name": uuid.uuid4().hex,
                "backtest_start_date": datetime.datetime.now(),
                "backtest_end_date": datetime.datetime.now(),
                "is_live": random.choice([True, False]),
            }
            for i in range(cls.count)
        ]

    def test_OperationPortfolio_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationPortfolio_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_portfolios(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationPortfolio_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_portfolio(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPortfolio_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_portfolio(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationPortfolio_bulkdelete(self) -> None:
        pass

    def test_OperationPortfolio_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update name
            new_name = uuid.uuid4().hex
            update_portfolio(res.uuid, name=new_name)
            df = get_portfolio(res.uuid)
            self.assertEqual(new_name, df["name"])

            # update backtest_start_date
            new_backtest_start_date = datetime.datetime.now()
            update_portfolio(res.uuid, backtest_start_date=new_backtest_start_date)
            df = get_portfolio(res.uuid)
            self.assertEqual(new_backtest_start_date - df["backtest_start_date"] < datetime.timedelta(seconds=1), True)

            # update backtest_end_date
            new_backtest_end_date = datetime.datetime.now()
            update_portfolio(res.uuid, backtest_end_date=new_backtest_end_date)
            df = get_portfolio(res.uuid)
            self.assertEqual(new_backtest_end_date - df["backtest_end_date"] < datetime.timedelta(seconds=1), True)

            # update is_live
            new_is_live = random.choice([True, False])
            update_portfolio(res.uuid, is_live=new_is_live)
            df = get_portfolio(res.uuid)
            self.assertEqual(new_is_live, df["is_live"])

    def test_OperationPortfolio_exists(self) -> None:
        pass

    def test_OperationPortfolio_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_portfolio(res.uuid)
            self.assertEqual(res["uuid"], df["uuid"])
            self.assertEqual(res["name"], df["name"])
            self.assertEqual(
                res["backtest_start_date"] - df["backtest_start_date"] < datetime.timedelta(seconds=1), True
            )
            self.assertEqual(res["backtest_end_date"] - df["backtest_end_date"] < datetime.timedelta(seconds=1), True)
            self.assertEqual(res["is_del"], df["is_del"])

            self.assertEqual(res["is_live"], df["is_live"])

        # TODO Test fuzz name

    def test_OperationPortfolio_exceptions(self) -> None:
        pass
