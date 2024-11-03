import unittest
import datetime
import random
import uuid
import time

from ginkgo.data.models import MTickSummary
from ginkgo.data.operations.tick_summary_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.enums import SOURCE_TYPES


class OperationTickSummaryTest(unittest.TestCase):
    """
    UnitTest for TickSummary CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MTickSummary
        cls.count = random.randint(2, 5)
        drop_table(cls.model)
        create_table(cls.model)
        cls.params = [
            {
                "code": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "price": random.uniform(0, 100),
                "volume": random.randint(0, 1000),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_Operationtick_summary_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_tick_summary(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_Operationtick_summary_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_tick_summarys(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_Operationtick_summary_update(self) -> None:
        pass

    def test_Operationtick_summary_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tick_summary(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_tick_summary_by_id(res["uuid"])
            time.sleep(0.1)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_Operationtick_summary_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_tick_summary(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_tick_summary_by_id(res["uuid"])
            time.sleep(0.05)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

            delete_tick_summary_by_id(res["uuid"])
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_Operationtick_summary_get(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        code = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["code"] = code
            item = self.model(**params_copy)
            l.append(item)
        add_tick_summarys(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        df = get_tick_summarys(code=code)
        self.assertEqual(df.shape[0], len(self.params))

    def test_Operationtick_summary_get_with_date_range(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        code = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["code"] = code
            item = self.model(**params_copy)
            l.append(item)
        add_tick_summarys(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        df = get_tick_summarys(code=code)
        self.assertEqual(df.shape[0], len(self.params))


#     # def test_Operationtick_summary_get_with_pagination(self) -> None:
#     #     pass


#     def test_Operationtick_summary_exists(self) -> None:
#         pass

#     def test_Operationtick_summary_exceptions(self) -> None:
#         pass
