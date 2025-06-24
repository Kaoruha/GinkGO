import unittest
import decimal
import random
import datetime
import uuid
import time

from ginkgo.backtest import Position
from ginkgo.data.models import MPosition
from ginkgo.data.operations.position_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.libs import datetime_normalize, to_decimal


class OperationPositionTest(unittest.TestCase):
    """
    UnitTest for Position CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MPosition
        drop_table(cls.model, no_skip=True)
        create_table(cls.model, no_skip=True)
        cls.count = random.randint(10, 20)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "cost": decimal.Decimal(str(round(random.uniform(0, 100), 2))),
                "volume": random.randint(1, 100),
                "frozen_volume": random.randint(1, 100),
                "frozen_money": random.randint(1, 100),
                "price": decimal.Decimal(str(round(random.uniform(0, 100), 2))),
                "fee": decimal.Decimal(str(round(random.uniform(0, 100), 2))),
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

    def test_OperationPosition_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_position(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPosition_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            softdelete_position(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)
            delete_position(res.uuid)
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size1)

    def test_OperationPosition_delete_by_portfolio_id(self) -> None:
        new_portfolio_id = uuid.uuid4().hex
        l = []
        size0 = get_table_size(self.model)
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            add_position(**params_copy)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

        delete_positions_filtered(portfolio_id=new_portfolio_id)
        size2 = get_table_size(self.model)
        self.assertEqual(0, size2 - size0)

    def test_OperationPosition_delete_by_portfolio_id_and_engine_id(self) -> None:
        portfolio_id = uuid.uuid4().hex
        engine_id_target = uuid.uuid4().hex

        size0 = get_table_size(self.model)
        # 添加匹配 engine_id 的记录
        target_fit_count = random.randint(1, 5)
        for _ in range(target_fit_count):
            add_position(
                portfolio_id=portfolio_id,
                engine_id=engine_id_target,
                code=uuid.uuid4().hex,
                cost=0,
                volume=0,
                frozen_volume=0,
                frozen_money=0,
                price=0,
                fee=0,
            )
        size1 = get_table_size(self.model)
        self.assertEqual(target_fit_count, size1 - size0)

        # 添加不匹配 engine_id 的记录
        target_unfit_count = random.randint(6, 10)
        for _ in range(target_unfit_count):
            add_position(
                portfolio_id=portfolio_id,
                engine_id=uuid.uuid4().hex,
                code=uuid.uuid4().hex,
                cost=0,
                volume=0,
                frozen_volume=0,
                frozen_money=0,
                price=0,
                fee=0,
            )
        size2 = get_table_size(self.model)
        self.assertEqual(target_unfit_count, size2 - size1)

        size3 = get_table_size(self.model)
        delete_positions_filtered(portfolio_id=portfolio_id, engine_id=engine_id_target)
        size4 = get_table_size(self.model)
        time.sleep(0.05)

        self.assertEqual(-target_fit_count, size4 - size3)

        delete_positions_filtered(portfolio_id=portfolio_id)
        time.sleep(0.05)
        size5 = get_table_size(self.model)
        self.assertEqual(-target_unfit_count, size5 - size4)

    def test_OperationPosition_delete_by_portfolio_engine_and_code(self) -> None:
        pass

    def test_OperationPosition_delete_by_portfolio_and_code(self) -> None:
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = uuid.uuid4().hex

            for j in range(5):
                params_copy["engine_id"] = uuid.uuid4().hex

                size0 = get_table_size(self.model)
                res = add_position(**params_copy)
                size1 = get_table_size(self.model)
                self.assertEqual(1, size1 - size0)

                delete_positions_filtered(portfolio_id=res.portfolio_id, code=res.code)
                size2 = get_table_size(self.model)
                self.assertEqual(-1, size2 - size1)

                for k in range(5):
                    params_copy["code"] = uuid.uuid4().hex
                    size0 = get_table_size(self.model)
                    res = add_position(**params_copy)
                    size1 = get_table_size(self.model)
                    self.assertEqual(1, size1 - size0)

                    delete_positions_filtered(portfolio_id=res.portfolio_id, code=res.code)
                    size2 = get_table_size(self.model)
                    self.assertEqual(-1, size2 - size1)

            params_copy["volume"] = random.randint(1, 100)
            params_copy["frozen_volume"] = random.randint(1, 100)
            params_copy["frozen_money"] = random.randint(1, 100)
            params_copy["cost"] = random.uniform(0, 100)

            size0 = get_table_size(self.model)
            res = add_position(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_positions_filtered(portfolio_id=res.portfolio_id, code=res.code)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPositionrecord_softdelete_by_portfolio_and_code(self) -> None:
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = uuid.uuid4().hex
            params_copy["code"] = uuid.uuid4().hex
            params_copy["volume"] = random.randint(1, 100)
            params_copy["frozen_volume"] = random.randint(1, 100)
            params_copy["frozen_money"] = random.randint(1, 100)
            params_copy["cost"] = random.uniform(0, 100)

            size0 = get_table_size(self.model)
            res = add_position(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_positions_filtered(portfolio_id=res.portfolio_id, code=res.code)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

            delete_positions_filtered(portfolio_id=res.portfolio_id, code=res.code)
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size1)

    def test_OperationPosition_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # Update volume
            new_volume = random.randint(1, 100)
            update_position(res["uuid"], volume=new_volume)
            pos = get_position(res["uuid"])
            self.assertEqual(new_volume, pos.volume)

            # Update frozen volume
            new_frozen_volume = random.randint(1, 100)
            update_position(res["uuid"], frozen_volume=new_frozen_volume)
            pos = get_position(res["uuid"])
            self.assertEqual(new_frozen_volume, pos.frozen_volume)

            # update cost
            new_cost = decimal.Decimal(str(round(random.uniform(0, 100), 2)))
            update_position(res["uuid"], cost=new_cost)
            pos = get_position(res["uuid"])
            self.assertEqual(new_cost, pos.cost)

            # update frozen
            new_frozen = random.randint(1, 100)
            update_position(res["uuid"], frozen_money=new_frozen)
            pos = get_position(res["uuid"])
            self.assertEqual(new_frozen, pos.frozen_money)

    def test_OperationPosition_update_filtered(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update cost
            new_cost = round(random.uniform(0, 100), 2)
            update_position_filtered(portfolio_id=res["portfolio_id"], code=res["code"], cost=new_cost)
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_cost, df["cost"])

            # Update volume
            new_volume = random.randint(1, 100)
            update_position_filtered(portfolio_id=res["portfolio_id"], code=res["code"], volume=new_volume)
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_volume, df["volume"])

            # Update frozen volume
            new_frozen_volume = random.randint(1, 100)
            update_position_filtered(
                portfolio_id=res["portfolio_id"], code=res["code"], frozen_volume=new_frozen_volume
            )
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_frozen_volume, df["frozen_volume"])

            # Update frozen money
            new_frozen_money = decimal.Decimal(str(round(random.uniform(0, 100), 2)))
            update_position_filtered(portfolio_id=res["portfolio_id"], code=res["code"], frozen_money=new_frozen_money)
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_frozen_money, to_decimal(df["frozen_money"]))

            # Update price
            new_price = decimal.Decimal(str(round(random.uniform(0, 100), 2)))
            update_position_filtered(portfolio_id=res["portfolio_id"], code=res["code"], price=new_price)
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_price, to_decimal(df["price"]))

            # Update price
            new_fee = decimal.Decimal(str(round(random.uniform(0, 100), 2)))
            update_position_filtered(portfolio_id=res["portfolio_id"], code=res["code"], fee=new_fee)
            df = get_position(res["uuid"], as_dataframe=True).iloc[0]
            self.assertEqual(new_fee, to_decimal(df["fee"]))

    def test_OperationPosition_get(self) -> None:
        # Position
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            pos = get_position(res.uuid, as_dataframe=False)
            self.assertEqual(res["uuid"], pos.uuid)
            self.assertEqual(res["portfolio_id"], pos.portfolio_id)
            self.assertEqual(res["engine_id"], pos.engine_id)
            self.assertEqual(res["code"], pos.code)
            self.assertEqual(res["cost"], pos.cost)
            self.assertEqual(res["volume"], pos.volume)
            self.assertEqual(res["frozen_volume"], pos.frozen_volume)
            self.assertEqual(res["frozen_money"], pos.frozen_money)
            self.assertEqual(res["price"], pos.price)
            self.assertEqual(res["fee"], pos.fee)

        # dataframe
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_position(res.uuid, as_dataframe=True).iloc[0]
            self.assertEqual(res["uuid"], df.uuid)
            self.assertEqual(res["portfolio_id"], df.portfolio_id)
            self.assertEqual(res["engine_id"], df.engine_id)
            self.assertEqual(res["code"], df.code)
            self.assertEqual(res["cost"], to_decimal(df.cost))
            self.assertEqual(res["volume"], df.volume)
            self.assertEqual(res["frozen_volume"], df["frozen_volume"])
            self.assertEqual(res["frozen_money"], to_decimal(df.frozen_money))
            self.assertEqual(res["price"], to_decimal(df["price"]))
            self.assertEqual(res["fee"], to_decimal(df["fee"]))

    def test_OperationPosition_get(self) -> None:
        # Filter portfolio_id
        new_portfolio_id = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            add_position(**params_copy)
        res = get_positions_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count, len(res))
        df = get_positions_page_filtered(portfolio_id=new_portfolio_id, as_dataframe=True)
        self.assertEqual(self.count, df.shape[0])
        df = get_positions_page_filtered(portfolio_id=new_portfolio_id, as_dataframe=True, page=0, page_size=2)
        self.assertEqual(2, df.shape[0])

    def test_OperationPosition_exists(self) -> None:
        # TODO
        pass

    def test_OperationPosition_exceptions(self) -> None:
        # TODO
        pass
