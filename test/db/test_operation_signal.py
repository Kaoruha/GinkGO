import unittest
import uuid
import datetime
import random
import time
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data.models import MSignal
from ginkgo.backtest import Signal

from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.data.operations.signal_crud import *


class OperationSignalTest(unittest.TestCase):
    """
    UnitTest for Signal CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MSignal
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "engine_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "code": uuid.uuid4().hex,
                "direction": random.choice([i for i in DIRECTION_TYPES]),
                "reason": uuid.uuid4().hex,
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationSignal_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_signal(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationSignal_bulkinsert(self) -> None:
        l = []
        for i in self.params:
            item = Signal(**i)
            l.append(item)
        size0 = get_table_size(self.model)
        add_signals(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationSignal_bulkinsert_via_model(self) -> None:
        l = []
        for i in self.params:
            item = MSignal(**i)
            l.append(item)
        size0 = get_table_size(self.model)
        add_signals(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)

    def test_OperationSignal_delete_by_id(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_signal(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_signal(res["uuid"])
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

        def test_OperationSignal_update(self) -> None:
            # No update
            pass

    def test_OperationSignal_get_by_portfolio(self) -> None:
        l = []
        portfolio_id = uuid.uuid4().hex
        for i in self.params:
            params_copy = i.copy()
            params_copy["portfolio_id"] = portfolio_id
            item = Signal(**params_copy)
            l.append(item)
        size0 = get_table_size(self.model)
        add_signals(l)
        size1 = get_table_size(self.model)
        self.assertEqual(len(self.params), size1 - size0)
        res = get_signals_page_filtered(portfolio_id)
        self.assertEqual(self.count, len(res))
        df = get_signals_page_filtered(portfolio_id, as_dataframe=True)
        self.assertEqual(self.count, df.shape[0])

    def test_OperationSignal_get_filtered(self) -> None:
        l = []
        portfolio_id = uuid.uuid4().hex
        code1 = uuid.uuid4().hex
        code2 = uuid.uuid4().hex
        count1 = random.randint(1, 10)
        count2 = random.randint(1, 10)
        for i in range(count1):
            params_copy = self.params[i % len(self.params)].copy()
            params_copy["code"] = code1
            params_copy["portfolio_id"] = portfolio_id
            item = Signal(**params_copy)
            l.append(item)
        size0 = get_table_size(self.model)
        add_signals(l)
        size1 = get_table_size(self.model)
        self.assertEqual(count1, size1 - size0)

        l = []
        for i in range(count2):
            params_copy = self.params[i % len(self.params)].copy()
            params_copy["code"] = code2
            params_copy["portfolio_id"] = portfolio_id
            item = Signal(**params_copy)
            l.append(item)
        add_signals(l)
        size2 = get_table_size(self.model)
        self.assertEqual(count2, size2 - size1)

        res = get_signals_page_filtered(portfolio_id=portfolio_id, code=code1)
        self.assertEqual(count1, len(res))
        df = get_signals_page_filtered(portfolio_id=portfolio_id, code=code1, as_dataframe=True)
        self.assertEqual(count1, df.shape[0])

        res = get_signals_page_filtered(portfolio_id=portfolio_id, code=code2)
        self.assertEqual(count2, len(res))
        df = get_signals_page_filtered(portfolio_id=portfolio_id, code=code2, as_dataframe=True)
        self.assertEqual(count2, df.shape[0])

    def test_OperationSignal_get_by_portfolio_and_direction(self) -> None:
        # TODO
        pass

    def test_OperationSignal_get_by_portfolio_and_reason(self) -> None:
        # TODO
        pass

    def test_OperationSignal_get_by_portfolio_and_daet_range(self) -> None:
        # TODO
        pass

    def test_OperationSignal_get_by_portfolio_and_paginazion(self) -> None:
        # TODO
        pass

    def test_OperationSignal_exists(self) -> None:
        # TODO
        pass

    def test_OperationSignal_exceptions(self) -> None:
        # TODO
        pass
