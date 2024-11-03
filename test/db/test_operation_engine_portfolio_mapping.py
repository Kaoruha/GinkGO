import unittest
import time
import uuid
import random
import datetime

from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.data.drivers import get_table_size, create_table, drop_table
from ginkgo.data.operations.engine_portfolio_mapping_crud import *
from ginkgo.data.models import MEnginePortfolioMapping


class OperationEnginePortfolioMappingTest(unittest.TestCase):
    """
    UnitTest for Analyzer CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MEnginePortfolioMapping
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "engine_id": uuid.uuid4().hex,
                "portfolio_id": uuid.uuid4().hex,
            }
            for i in range(cls.count)
        ]

    def test_OperationEnginePortfolioMapping_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_engine_portfolio_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationEnginePortfolioMapping_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        res = add_engine_portfolio_mappings(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationEnginePortfolioMapping_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_engine_portfolio_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_engine_portfolio_mapping(res.uuid)
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationEnginePortfolioMapping_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_engine_portfolio_mapping(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            softdelete_engine_portfolio_mapping(res.uuid)
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(0, size2 - size1)
            delete_engine_portfolio_mapping(res.uuid)
            time.sleep(0.01)
            size3 = get_table_size(self.model)
            self.assertEqual(-1, size3 - size1)

    # def test_OperationEnginePortfolioMapping_exists(self) -> None:
    #     pass

    def test_OperationEnginePortfolioMapping_update(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_engine_portfolio_mapping(
                engine_id="test", portfolio_id="test", type=EVENT_TYPES.OTHER, name="name"
            )
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            # Update Engine ID
            update_engine_portfolio_mapping(res.uuid, engine_id=i["engine_id"])
            df = get_engine_portfolio_mapping(res.uuid).iloc[0]
            self.assertEqual(df["engine_id"], i["engine_id"])

            # Update Handler ID
            update_engine_portfolio_mapping(res.uuid, portfolio_id=i["portfolio_id"])
            df = get_engine_portfolio_mapping(res.uuid).iloc[0]
            self.assertEqual(df["portfolio_id"], i["portfolio_id"])

    def test_OperationEnginePortfolioMapping_get(self) -> None:
        engine_id = uuid.uuid4().hex
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_engine_portfolio_mapping(engine_id=engine_id, portfolio_id=i["portfolio_id"])
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
        df = get_engine_portfolio_mappings(engine_id=engine_id)
        self.assertEqual(self.count, df.shape[0])

    # def test_OperationEngine_exceptions(self) -> None:
    #     # TODO
    #     pass
