import unittest
import random
import datetime
import time
import uuid
from ginkgo.data.operations.transfer_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.data.models import MTransfer
from ginkgo.libs import datetime_normalize
from ginkgo.enums import TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES, MARKET_TYPES


class OperationTransferTest(unittest.TestCase):
    """
    UnitTest for Transfer CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MTransfer
        drop_table(cls.model, no_skip=True)
        create_table(cls.model, no_skip=True)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "direction": random.choice([i for i in TRANSFERDIRECTION_TYPES]),
                "market": random.choice([i for i in MARKET_TYPES]),
                "money": random.randint(10000, 1000000),
                "status": random.choice([i for i in TRANSFERSTATUS_TYPES]),
                "timestamp": datetime.datetime.now(),
            }
            for i in range(cls.count)
        ]

    def test_OperationTransfer_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_transfer(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationTransfer_bulkinsert(self) -> None:
        l = []
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        size0 = get_table_size(self.model)
        add_transfers(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationTransfer_update(self) -> None:
        pass

    def test_OperationTransfer_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_transfer(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_transfer(res["uuid"])
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationTransfer_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_transfer(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_transfer(res["uuid"])
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)
            delete_transfer(res["uuid"])
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size2)

    def test_OperationTransfer_delete_filtered(self) -> None:
        new_portfolio_id = uuid.uuid4().hex
        for i in self.params:
            params_copy = i.copy()
            params_copy["portfolio_id"] = new_portfolio_id
            size0 = get_table_size(self.model)
            add_transfer(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
        size2 = get_table_size(self.model)
        delete_transfers_filtered(portfolio_id=new_portfolio_id)
        size3 = get_table_size(self.model)
        self.assertEqual(-self.count, size3 - size2)

    def test_OperationTransfer_softdelete_filtered(self) -> None:
        new_portfolio_id = uuid.uuid4().hex
        for i in self.params:
            params_copy = i.copy()
            params_copy["portfolio_id"] = new_portfolio_id
            size0 = get_table_size(self.model)
            add_transfer(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
        size2 = get_table_size(self.model)
        softdelete_transfers_filtered(portfolio_id=new_portfolio_id)
        size3 = get_table_size(self.model)
        # Soft delete should not change table size (just marks records as deleted)
        self.assertEqual(0, size3 - size2)
        # Calling softdelete again on already soft-deleted records should have no effect
        softdelete_transfers_filtered(portfolio_id=new_portfolio_id)
        size4 = get_table_size(self.model)
        self.assertEqual(0, size4 - size3)

    def test_OperationTransfer_get(self) -> None:
        # in format ModelTransfer
        # in format dataframe
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_transfer(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(size1 - size0, 1)
            # Get as Transfer object (should return Transfer object with attributes)
            item = get_transfer(res["uuid"])
            # Check if we got a valid result - item should not be None
            self.assertIsNotNone(item, f"get_transfer returned None for uuid: {res['uuid']}")
            
            if hasattr(item, 'portfolio_id'):
                # Transfer object attributes
                self.assertEqual(i["portfolio_id"], item.portfolio_id)
                self.assertEqual(i["direction"], item.direction)
                self.assertEqual(i["market"], item.market)
                self.assertEqual(float(i["money"]), float(item.money))
                self.assertEqual(i["status"], item.status)
            elif hasattr(item, 'shape') and item.shape[0] > 0:
                # Non-empty DataFrame/Series
                self.assertEqual(i["portfolio_id"], item["portfolio_id"])
                self.assertEqual(i["direction"], item["direction"])
                self.assertEqual(i["market"], item["market"])
                self.assertEqual(i["money"], item["money"])
                self.assertEqual(i["status"], item["status"])
            else:
                # None, empty DataFrame, or error case
                self.fail(f"get_transfer returned invalid result for uuid: {res['uuid']}, got: {type(item)}")

            df = get_transfer(id=res["uuid"], as_dataframe=True)
            self.assertFalse(df.empty, f"get_transfer returned empty DataFrame for uuid: {res['uuid']}")
            self.assertEqual(df["portfolio_id"].iloc[0], i["portfolio_id"])
            self.assertEqual(df["direction"].iloc[0], i["direction"])
            self.assertEqual(df["market"].iloc[0], i["market"])
            self.assertEqual(df["money"].iloc[0], i["money"])
            self.assertEqual(df["status"].iloc[0], i["status"])

    def test_OperationTransfer_get_filtered(self) -> None:
        # By Portfolio
        new_portfolio_id = uuid.uuid4().hex[:10]
        for i in self.params:
            params_copy = i.copy()
            params_copy["portfolio_id"] = new_portfolio_id
            size0 = get_table_size(self.model)
            add_transfer(**params_copy)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

        res = get_transfers_page_filtered(portfolio_id=new_portfolio_id)
        self.assertIsNotNone(res, f"get_transfers_page_filtered returned None for portfolio {new_portfolio_id}")
        self.assertEqual(self.count, len(res), f"Expected {self.count} transfers for portfolio {new_portfolio_id}, got {len(res)}")
        df = get_transfers_page_filtered(portfolio_id=new_portfolio_id, as_dataframe=True)
        self.assertIsNotNone(df, f"get_transfers_page_filtered returned None DataFrame for portfolio {new_portfolio_id}")
        self.assertFalse(df.empty, f"get_transfers_page_filtered returned empty DataFrame for portfolio {new_portfolio_id}")
        self.assertEqual(self.count, df.shape[0], f"Expected {self.count} transfers in DataFrame, got {df.shape[0]}")

    def test_OperationTransfer_exists(self) -> None:
        pass

    def test_OperationTransfer_exceptions(self) -> None:
        pass
