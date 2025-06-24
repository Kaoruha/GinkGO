import unittest
import random
import uuid
import time
import datetime
from decimal import Decimal

from ginkgo.data.models import MTick
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES
from ginkgo.data.operations.tick_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table, is_table_exsists


class OperationTickTest(unittest.TestCase):
    """
    UnitTest for Tick CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.test_code = uuid.uuid4().hex[:4]
        cls.model = get_tick_model(cls.test_code)
        drop_table(cls.model, no_skip=True)
        create_table(cls.model, no_skip=True)
        print(is_table_exsists(cls.model))
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "code": cls.test_code,
                "price": Decimal(str(random.uniform(0, 100))),
                "volume": random.randint(1, 100),
                "direction": random.choice([i for i in TICKDIRECTION_TYPES]),
                "timestamp": datetime.datetime.now(),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationTick_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_tick(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationTick_bulkinsert(self) -> None:
        l = []
        for i in self.params:
            item = Tick(**i)
            l.append(item)
        size0 = get_table_size(self.model)
        add_ticks(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationTick_delete(self) -> None:
        l = []
        new_code = uuid.uuid4().hex[:5]
        new_model = get_tick_model(new_code)
        try:
            drop_table(new_model, no_skip=True)
            create_table(new_model, no_skip=True)
            for i in self.params:
                params_copy = i.copy()
                params_copy["code"] = new_code
                item = Tick(**params_copy)
                l.append(item)
            size0 = get_table_size(new_model)
            add_ticks(l)
            size1 = get_table_size(new_model)
            self.assertEqual(self.count, size1 - size0)

            delete_ticks(code=new_code)
            size2 = get_table_size(new_model)
            self.assertEqual(-self.count, size2 - size1)
        except Exception as e:
            print(e)
        finally:
            drop_table(new_model, no_skip=True)

    def test_OperationTick_update(self) -> None:
        # No update
        pass

    def test_OperationTick_get(self) -> None:
        # in format Tick
        # in format dataframe
        l = []
        new_code = self.test_code
        for i in self.params:
            params_copy = i.copy()
            params_copy["code"] = new_code
            item = Tick(**params_copy)
            l.append(item)
        size0 = get_table_size(self.model)
        add_ticks(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

        res = get_ticks_page_filtered(code=new_code)
        self.assertEqual(len(res) >= self.count, True)

        df = get_ticks_page_filtered(code=new_code, as_dataframe=True)
        self.assertEqual(df.shape[0] >= self.count, True)


#     def test_OperationTick_get_by_date_range(self) -> None:
#         pass

#     def test_OperationTick_get_by_pagination(self) -> None:
#         pass

#     def test_OperationTick_softdelete(self) -> None:
#         pass

#     # def test_OperationTick_exists(self) -> None:
#     #     pass

#     # def test_OperationTick_exceptions(self) -> None:
#     #     pass
