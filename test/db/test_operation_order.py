import unittest
import time
import datetime
import random
import uuid

from ginkgo.data.models import MOrder
from ginkgo.data.drivers import create_table, drop_table, get_table_size
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize
from ginkgo.data.operations.order_crud import *


class OperationOrderTest(unittest.TestCase):
    """
    UnitTest for Order CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MOrder
        drop_table(cls.model, no_skip=True)
        create_table(cls.model, no_skip=True)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "direction": random.choice([i for i in DIRECTION_TYPES]),
                "order_type": random.choice([i for i in ORDER_TYPES]),
                "status": random.choice([i for i in ORDERSTATUS_TYPES]),
                "volume": random.randint(0, 1000),
                "limit_price": round(random.uniform(0, 100), 2),
                "frozen": random.randint(0, 1000),
                "transaction_price": round(random.uniform(0, 100), 2),
                "remain": round(random.uniform(0, 100), 2),
                "fee": round(random.uniform(0, 100), 2),
                "timestamp": datetime.datetime.now(),
            }
            for i in range(cls.count)
        ]

    def test_OperationOrder_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationOrder_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_orders(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationOrder_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_order(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationOrder_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_order(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)

    def test_OperationOrder_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update portfolio_id
            new_portfolio_id = uuid.uuid4().hex
            update_order(res.uuid, portfolio_id=new_portfolio_id)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_portfolio_id, df["portfolio_id"])

            # update engine_id
            new_engine_id = uuid.uuid4().hex
            update_order(res.uuid, engine_id=new_engine_id)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_engine_id, df["engine_id"])

            # update code
            new_code = uuid.uuid4().hex
            update_order(res.uuid, code=new_code)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_code, df["code"])

            # update direction
            new_direction = random.choice([i for i in DIRECTION_TYPES])
            update_order(res.uuid, direction=new_direction)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_direction, df["direction"])

            # update type
            new_type = random.choice([i for i in ORDER_TYPES])
            update_order(res.uuid, order_type=new_type)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_type, df["order_type"])

            # update status
            new_status = random.choice([i for i in ORDERSTATUS_TYPES])
            update_order(res.uuid, status=new_status)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_status, df["status"])

            # update volume
            new_volume = random.randint(0, 1000)
            update_order(res.uuid, volume=new_volume)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_volume, df["volume"])

            # update limit_price
            new_limit_price = round(random.uniform(0, 100), 2)
            update_order(res.uuid, limit_price=new_limit_price)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_limit_price, df["limit_price"])

            # update frozen
            new_frozen = random.randint(0, 1000)
            update_order(res.uuid, frozen=new_frozen)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_frozen, df["frozen"])

            # update transaction_price
            new_transaction_price = round(random.uniform(0, 100), 2)
            update_order(res.uuid, transaction_price=new_transaction_price)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_transaction_price, df["transaction_price"])

            # update remain
            new_remain = round(random.uniform(0, 100), 2)
            update_order(res.uuid, remain=new_remain)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_remain, df["remain"])

            # update fee
            new_fee = round(random.uniform(0, 100), 2)
            update_order(res.uuid, fee=new_fee)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_fee, df["fee"])

            # update timestamp
            new_timestamp = datetime.datetime.now()
            update_order(res.uuid, timestamp=new_timestamp)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_timestamp - df["timestamp"] < datetime.timedelta(seconds=1), True)

    def test_OperationOrder_update_dataframe_response(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update portfolio_id
            new_portfolio_id = uuid.uuid4().hex
            update_order(res.uuid, portfolio_id=new_portfolio_id)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_portfolio_id, df["portfolio_id"])

            # update code
            new_code = uuid.uuid4().hex
            update_order(res.uuid, code=new_code)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_code, df["code"])

            # update direction
            new_direction = random.choice([i for i in DIRECTION_TYPES])
            update_order(res.uuid, direction=new_direction)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_direction, df["direction"])

            # update type
            new_type = random.choice([i for i in ORDER_TYPES])
            update_order(res.uuid, order_type=new_type)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_type, df["order_type"])

            # update status
            new_status = random.choice([i for i in ORDERSTATUS_TYPES])
            update_order(res.uuid, status=new_status)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_status, df["status"])

            # update volume
            new_volume = random.randint(0, 1000)
            update_order(res.uuid, volume=new_volume)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_volume, df["volume"])

            # update limit_price
            new_limit_price = round(random.uniform(0, 100), 2)
            update_order(res.uuid, limit_price=new_limit_price)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_limit_price, df["limit_price"])

            # update frozen
            new_frozen = random.randint(0, 1000)
            update_order(res.uuid, frozen=new_frozen)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_frozen, df["frozen"])

            # update transaction_price
            new_transaction_price = round(random.uniform(0, 100), 2)
            update_order(res.uuid, transaction_price=new_transaction_price)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_transaction_price, df["transaction_price"])

            # update remain
            new_remain = round(random.uniform(0, 100), 2)
            update_order(res.uuid, remain=new_remain)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_remain, df["remain"])

            # update fee
            new_fee = round(random.uniform(0, 100), 2)
            update_order(res.uuid, fee=new_fee)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_fee, df["fee"])

            # update timestamp
            new_timestamp = datetime.datetime.now()
            update_order(res.uuid, timestamp=new_timestamp)
            df = get_order(res.uuid).iloc[0]
            self.assertEqual(new_timestamp - df["timestamp"] < datetime.timedelta(seconds=1), True)

    def test_OperationOrder_exists(self) -> None:
        pass

    def test_OperationOrder_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_order(res.uuid).iloc[0]
            self.assertEqual(df["uuid"], res["uuid"])
            self.assertEqual(df["portfolio_id"], res["portfolio_id"])
            self.assertEqual(df["code"], res["code"])
            self.assertEqual(df["direction"], res["direction"])
            self.assertEqual(df["order_type"], res["order_type"])
            self.assertEqual(df["status"], res["status"])
            self.assertEqual(df["volume"], res["volume"])
            self.assertEqual(float(df["limit_price"]), float(res["limit_price"]))
            self.assertEqual(df["frozen"], res["frozen"])
            self.assertEqual(float(df["transaction_price"]), float(res["transaction_price"]))
            self.assertEqual(float(df["remain"]), float(res["remain"]))
            self.assertEqual(float(df["fee"]), float(res["fee"]))
            self.assertEqual(df["timestamp"] - res["timestamp"] < datetime.timedelta(seconds=1), True)

    def test_OperationOrder_get_filtered(self) -> None:
        # Filter portfolio_id
        new_portfolio_id = uuid.uuid4().hex
        new_engine_id = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            add_order(**params_copy)
        res = get_orders_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and code
        new_portfolio_id = uuid.uuid4().hex
        new_engine_id = uuid.uuid4().hex
        new_code = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            params_copy["code"] = new_code
            add_order(**params_copy)
        res = get_orders_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id, code=new_code)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and direction
        new_portfolio_id = uuid.uuid4().hex
        new_engine_id = uuid.uuid4().hex
        new_direction = random.choice([i for i in DIRECTION_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            params_copy["direction"] = new_direction
            add_order(**params_copy)
        res = get_orders_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id, direction=new_direction)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and type
        new_portfolio_id = uuid.uuid4().hex
        new_engine_id = uuid.uuid4().hex
        new_type = random.choice([i for i in ORDER_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            params_copy["type"] = new_type
            add_order(**params_copy)
        res = get_orders_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id, type=new_type)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and status
        new_portfolio_id = uuid.uuid4().hex
        new_engine_id = uuid.uuid4().hex
        new_status = random.choice([i for i in ORDERSTATUS_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            params_copy["status"] = new_status
            add_order(**params_copy)
        res = get_orders_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id, status=new_status)
        self.assertEqual(self.count, len(res))

        # TODO date filter
        # TODO Pagination

    def test_OperationOrder_exceptions(self) -> None:
        pass
