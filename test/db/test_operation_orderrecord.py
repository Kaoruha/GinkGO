import unittest
import datetime
import time
import random
import uuid


from ginkgo.data.models import MOrderRecord
from ginkgo.data.drivers import create_table, drop_table, get_table_size
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs import datetime_normalize
from ginkgo.data.operations.order_record_crud import *


class OperationOrderRecordTest(unittest.TestCase):
    """
    UnitTest for Order CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MOrderRecord
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "order_id": uuid.uuid4().hex,
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "code": uuid.uuid4().hex,
                "direction": random.choice([i for i in DIRECTION_TYPES]),
                "order_type": random.choice([i for i in ORDER_TYPES]),
                "status": random.choice([i for i in ORDERSTATUS_TYPES]),
                "limit_price": round(random.uniform(0, 100), 2),
                "volume": random.randint(0, 1000),
                "frozen": random.randint(0, 1000),
                "transaction_price": round(random.uniform(0, 100), 2),
                "remain": round(random.uniform(0, 100), 2),
                "fee": round(random.uniform(0, 100), 2),
                "timestamp": datetime.datetime.now(),
            }
            for i in range(cls.count)
        ]

    def test_OperationOrderRecord_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order_record(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationOrderRecord_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_order_records(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationOrderRecord_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order_record(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_order_record(res.uuid)
            time.sleep(0.02)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationOrderRecord_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order_record(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_order_record(res.uuid)
            time.sleep(0.02)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    # def test_OperationOrderRecord_delete_by_portfolio_and_date_range(self) -> None:
    #     # TODO
    #     pass

    # def test_OperationOrderRecord_softdelete_by_portfolio_and_date_range(self) -> None:
    #     # TODO
    #     pass

    # def test_OperationOrderRecord_exists(self) -> None:
    #     pass

    def test_OperationOrderRecord_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_order_record(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            df = get_order_record(res.uuid)
            self.assertEqual(df["uuid"], res["uuid"])
            self.assertEqual(df["portfolio_id"], res["portfolio_id"])
            self.assertEqual(df["engine_id"], res["engine_id"])
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

    def test_OperationOrderRecord_get_filtered(self) -> None:
        # Filter portfolio_id
        new_portfolio_id = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count, len(res))

        # Filter engine_id
        new_engine_id = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["engine_id"] = new_engine_id
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count * 2, len(res))
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id, engine_id=new_engine_id)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and code
        new_code = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["code"] = new_code
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count * 3, len(res))
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id, code=new_code)
        self.assertEqual(self.count, len(res))

        # Filter portfolio_id and direction
        new_direction = random.choice([i for i in DIRECTION_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["direction"] = new_direction
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count * 4, len(res))
        self.assertGreaterEqual(len(res), self.count)

        # Filter portfolio_id and type
        new_type = random.choice([i for i in ORDER_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["order_type"] = new_type
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count * 5, len(res))
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id, order_type=new_type)
        self.assertGreaterEqual(len(res), self.count)

        # Filter portfolio_id and status
        new_status = random.choice([i for i in ORDERSTATUS_TYPES])
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            params_copy["status"] = new_status
            add_order_record(**params_copy)
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(self.count * 6, len(res))
        res = get_order_records_page_filtered(portfolio_id=new_portfolio_id, status=new_status)
        self.assertGreaterEqual(len(res), self.count)

    # def test_OperationOrderRecord_exceptions(self) -> None:
    #     pass
