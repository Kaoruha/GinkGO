import unittest
import random
import datetime
import uuid
import time

from ginkgo.backtest import Position
from ginkgo.data.models import MPosition
from ginkgo.data.operations.position_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.libs import datetime_normalize


class OperationPositionTest(unittest.TestCase):
    """
    UnitTest for Position CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MPosition
        drop_table(cls.model)
        time.sleep(0.1)
        create_table(cls.model)
        cls.count = 10
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "volume": random.randint(1, 100),
                "frozen": random.randint(1, 100),
                "cost": random.uniform(0, 100),
            }
            for i in range(cls.count)
        ]

    def test_OperationPosition_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationPosition_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_positions(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationPosition_update_by_id(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # Update volume
            new_volume = random.randint(1, 100)
            update_position_by_id(res["uuid"], volume=new_volume)
            pos = get_position_by_id(res["uuid"])
            self.assertEqual(new_volume, pos.volume)

            # update cost
            new_cost = round(random.uniform(0, 100), 2)
            update_position_by_id(res["uuid"], cost=new_cost)
            pos = get_position_by_id(res["uuid"])
            self.assertEqual(new_cost, pos.cost)

            # update frozen
            new_frozen = random.randint(1, 100)
            update_position_by_id(res["uuid"], frozen=new_frozen)
            pos = get_position_by_id(res["uuid"])
            self.assertEqual(new_frozen, pos.frozen)

    def test_OperationPosition_update_by_portfolio_and_code(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # Update volume
            new_volume = random.randint(1, 100)
            update_position(portfolio_id=res["portfolio_id"], code=res["code"], volume=new_volume)
            df = get_position_by_id(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_volume, df["volume"])

            # update cost
            new_cost = round(random.uniform(0, 100), 2)
            update_position(portfolio_id=res["portfolio_id"], code=res["code"], cost=new_cost)
            df = get_position_by_id(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_cost, df["cost"])

            # update frozen
            new_frozen = random.randint(1, 100)
            update_position(portfolio_id=res["portfolio_id"], code=res["code"], frozen=new_frozen)
            df = get_position_by_id(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_frozen, df["frozen"])

    # def test_OperationPosition_get(self) -> None:
    #     # in format ModelPosition
    #     # in format dataframe
    #     pass

    # def test_OperationPosition_delete(self) -> None:
    #     pass

    # def test_OperationPosition_exists(self) -> None:
    #     pass

    # def test_OperationPosition_exceptions(self) -> None:
    #     pass
