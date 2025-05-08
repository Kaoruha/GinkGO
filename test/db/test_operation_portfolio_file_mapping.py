import unittest
import time
import uuid
import random
import datetime

from ginkgo.enums import SOURCE_TYPES, FILE_TYPES
from ginkgo.data.drivers import get_table_size, create_table, drop_table
from ginkgo.data.operations.portfolio_file_mapping_crud import *

from ginkgo.data.models import MPortfolioFileMapping


class OperationPortfolioFileMappingTest(unittest.TestCase):
    """
    UnitTest for Analyzer CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MPortfolioFileMapping
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "file_id": uuid.uuid4().hex,
                "name": uuid.uuid4().hex,
                "type": random.choice([i for i in FILE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationPortfolioFileMapping_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio_file_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationPortfolioFileMapping_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        res = add_portfolio_file_mappings(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationPortfolioFileMapping_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio_file_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_portfolio_file_mapping(res.uuid)
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPortfolioFileMapping_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio_file_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            softdelete_portfolio_file_mapping(res.uuid)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)
            delete_portfolio_file_mapping(res.uuid)
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size1)

    def test_OperationPortfolioFileMapping_delete_by_portfolio(self) -> None:
        # TODO
        pass

    def test_OperationPortfolioFileMapping_softdelete_by_portfolio(self) -> None:
        # TODO
        pass

    def test_OperationPortfolioFileMapping_exists(self) -> None:
        pass

    def test_OperationPortfolioFileMapping_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio_file_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # update portfolio id
            new_portfolio_id = uuid.uuid4().hex
            update_portfolio_file_mapping(res.uuid, portfolio_id=new_portfolio_id)
            df = get_portfolio_file_mapping(res.uuid).iloc[0]
            self.assertEqual(df["portfolio_id"], new_portfolio_id)

            # update file id
            new_file_id = uuid.uuid4().hex
            update_portfolio_file_mapping(res.uuid, file_id=new_file_id)
            df = get_portfolio_file_mapping(res.uuid).iloc[0]
            self.assertEqual(df["file_id"], new_file_id)

            # update name
            new_name = uuid.uuid4().hex
            update_portfolio_file_mapping(res.uuid, name=new_name)
            df = get_portfolio_file_mapping(res.uuid).iloc[0]
            self.assertEqual(df["name"], new_name)

            # update type
            new_type = random.choice([i for i in FILE_TYPES])
            update_portfolio_file_mapping(res.uuid, type=new_type)
            df = get_portfolio_file_mapping(res.uuid).iloc[0]
            self.assertEqual(df["type"], new_type)

    def test_OperationPortfolioFileMapping_get(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_portfolio_file_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            df = get_portfolio_file_mapping(id=res.uuid).iloc[0]
            self.assertEqual(df["uuid"], res["uuid"])
            self.assertEqual(df["portfolio_id"], res["portfolio_id"])
            self.assertEqual(df["file_id"], res["file_id"])
            self.assertEqual(df["name"], res["name"])

    def test_OperationPortfolioFileMapping_get_by_portfolio(self) -> None:
        new_portfolio_id = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["portfolio_id"] = new_portfolio_id
            add_portfolio_file_mapping(**params_copy)
        df = get_portfolio_file_mappings_page_filtered(portfolio_id=new_portfolio_id)
        self.assertEqual(df.shape[0], self.count)

    def test_OperationPortfolio_exceptions(self) -> None:
        # TODO
        pass
