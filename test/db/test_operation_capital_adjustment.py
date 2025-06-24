import unittest
import datetime
import random
import uuid
import time
from decimal import Decimal

from ginkgo.data.models import MCapitalAdjustment
from ginkgo.enums import SOURCE_TYPES, CAPITALADJUSTMENT_TYPES
from ginkgo.data.operations.capital_adjustment_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table


class OperationCapitalAdjustmentTest(unittest.TestCase):
    """
    UnitTest for Tick CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MCapitalAdjustment
        cls.count = random.randint(2, 5)
        drop_table(cls.model, no_skip=True)
        create_table(cls.model, no_skip=True)
        cls.params = [
            {
                "code": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "type": random.choice([i for i in CAPITALADJUSTMENT_TYPES]),
                "fenhong": Decimal(str(round(random.uniform(0, 20), 1))),
                "peigujia": Decimal(str(round(random.uniform(0, 20), 1))),
                "songzhuangu": Decimal(str(round(random.uniform(0, 20), 1))),
                "peigu": Decimal(str(round(random.uniform(0, 20), 1))),
                "suogu": Decimal(str(round(random.uniform(0, 20), 1))),
                "panqianliutong": Decimal(str(round(random.uniform(0, 20), 1))),
                "panhouliutong": Decimal(str(round(random.uniform(0, 20), 1))),
                "qianzongguben": Decimal(str(round(random.uniform(0, 20), 1))),
                "houzongguben": Decimal(str(round(random.uniform(0, 20), 1))),
                "fenshu": Decimal(str(round(random.uniform(0, 20), 1))),
                "xingquanjia": Decimal(str(round(random.uniform(0, 20), 1))),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationCapitalAdjustment_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_capital_adjustment(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationCapitalAdjustment_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_capital_adjustments(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationCapitalAdjustment_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_capital_adjustment(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            delete_capital_adjustment(res["uuid"])
            time.sleep(0.02)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationCapitalAdjustment_softdelete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_capital_adjustment(**i)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

            softdelete_capital_adjustment(res["uuid"])
            time.sleep(0.05)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

            delete_capital_adjustment(res["uuid"])
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    #     def test_OperationCapitalAdjustment_delete_by_code_and_date_range(self) -> None:
    #         # TODO
    #         pass

    #     def test_OperationCapitalAdjustment_softdelete_by_code_and_date_range(self) -> None:
    #         # TODO
    #         pass

    #     def test_OperationCapitalAdjustment_update(self) -> None:
    #         pass

    def test_OperationCapitalAdjustment_get(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        code = uuid.uuid4().hex
        for i in range(self.count):
            params_copy = self.params[i].copy()
            params_copy["code"] = code
            item = self.model(**params_copy)
            l.append(item)
        add_capital_adjustments(l)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)
        df = get_capital_adjustments_page_filtered(code=code)
        self.assertEqual(df.shape[0], len(self.params))

        def test_OperationCapitalAdjustment_get_with_date_range(self) -> None:
            l = []
            size0 = get_table_size(self.model)
            code = uuid.uuid4().hex
            for i in range(self.count):
                params_copy = self.params[i].copy()
                params_copy["code"] = code
                item = self.model(**params_copy)
                l.append(item)
            add_capital_adjustments(l)
            size1 = get_table_size(self.model)
            self.assertEqual(self.count, size1 - size0)
            df = get_capital_adjustments_page_filtered(code=code)
            self.assertEqual(df.shape[0], len(self.params))
            # TODO date range

    def test_OperationCapitalAdjustment_exists(self) -> None:
        pass

    def test_OperationCapitalAdjustment_exceptions(self) -> None:
        pass
