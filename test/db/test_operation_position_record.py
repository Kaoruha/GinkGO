import unittest
import random
import uuid
import time
import datetime
from decimal import Decimal

from ginkgo.data.models import MPositionRecord
from ginkgo.backtest import Position
from ginkgo.data.operations.position_record_crud import *
from ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from ginkgo.data.models import MPositionRecord
from ginkgo.enums import SOURCE_TYPES


class OperationPositionrecordTest(unittest.TestCase):
    """
    UnitTest for Positionrecord CRUD
    """

    @classmethod
    def setUpClass(cls):
        cls.model = MPositionRecord
        drop_table(cls.model)
        create_table(cls.model)
        cls.count = random.randint(2, 5)
        cls.params = [
            {
                "portfolio_id": uuid.uuid4().hex,
                "timestamp": datetime.datetime.now(),
                "code": uuid.uuid4().hex,
                "volume": random.randint(1, 100),
                "frozen_volume": random.randint(1, 100),
                "cost": Decimal(str(round(random.uniform(0, 100), 2))),
                "frozen_money": random.randint(1, 100),
                "source": random.choice([i for i in SOURCE_TYPES]),
            }
            for i in range(cls.count)
        ]

    def test_OperationPositionrecord_insert(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            add_position_record(**i)
            time.sleep(0.01)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)

    def test_OperationPositionrecord_bulkinsert(self) -> None:
        l = []
        size0 = get_table_size(self.model)
        for i in self.params:
            item = self.model(**i)
            l.append(item)
        add_position_records(l)
        time.sleep(0.01)
        size1 = get_table_size(self.model)
        self.assertEqual(self.count, size1 - size0)

    def test_OperationPositionrecord_update(self) -> None:
        pass

    def test_OperationPositionrecord_delete(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position_record(**i)
            time.sleep(0.01)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            delete_position_record(res["uuid"])
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPositionrecord_softdelete_by_portfolio(self) -> None:
        for i in self.params:
            size0 = get_table_size(self.model)
            res = add_position_record(**i)
            time.sleep(0.01)
            size1 = get_table_size(self.model)
            self.assertEqual(1, size1 - size0)
            softdelete_position_record(res["uuid"])
            time.sleep(0.01)
            size2 = get_table_size(self.model)
            self.assertEqual(-1, size2 - size1)

    def test_OperationPositionrecord_delete_by_portfolio_and_code(self) -> None:
        portfolio_id = uuid.uuid4().hex
        code1 = uuid.uuid4().hex
        code2 = uuid.uuid4().hex
        l = []
        count1 = 3
        count2 = 4
        size0 = get_table_size(self.model)
        for i in range(count1):
            l.append(
                self.model(
                    portfolio_id=portfolio_id,
                    timestamp=datetime.datetime.now(),
                    code=code1,
                    volume=random.randint(1, 100),
                    frozen_volume=random.randint(1, 100),
                    cost=Decimal(str(round(random.uniform(0, 100), 2))),
                    frozen_money=random.randint(1, 100),
                    source=random.choice([i for i in SOURCE_TYPES]),
                )
            )
        for i in range(count2):
            l.append(
                self.model(
                    portfolio_id=portfolio_id,
                    timestamp=datetime.datetime.now(),
                    code=code2,
                    volume=random.randint(1, 100),
                    frozen_volume=random.randint(1, 100),
                    cost=Decimal(str(round(random.uniform(0, 100), 2))),
                    frozen_money=random.randint(1, 100),
                    source=random.choice([i for i in SOURCE_TYPES]),
                )
            )
        add_position_records(l)
        size1 = get_table_size(self.model)
        self.assertEqual(count1 + count2, size1 - size0)
        delete_position_records_by_portfolio_and_code(portfolio_id=portfolio_id, code=code1)
        time.sleep(0.01)
        size2 = get_table_size(self.model)
        self.assertEqual(-count1, size2 - size1)

        delete_position_records_by_portfolio_and_code(portfolio_id=portfolio_id, code=code2)
        time.sleep(0.01)
        size3 = get_table_size(self.model)
        self.assertEqual(-count2, size3 - size2)

    def test_OperationPositionrecord_softdelete_by_portfolio_and_code(self) -> None:
        portfolio_id = uuid.uuid4().hex
        code1 = uuid.uuid4().hex
        code2 = uuid.uuid4().hex
        l = []
        count1 = 3
        count2 = 4
        size0 = get_table_size(self.model)
        for i in range(count1):
            l.append(
                self.model(
                    portfolio_id=portfolio_id,
                    timestamp=datetime.datetime.now(),
                    code=code1,
                    volume=random.randint(1, 100),
                    frozen_volume=random.randint(1, 100),
                    cost=Decimal(str(round(random.uniform(0, 100), 2))),
                    frozen_money=random.randint(1, 100),
                    source=random.choice([i for i in SOURCE_TYPES]),
                )
            )
        for i in range(count2):
            l.append(
                self.model(
                    portfolio_id=portfolio_id,
                    timestamp=datetime.datetime.now(),
                    code=code2,
                    volume=random.randint(1, 100),
                    frozen_volume=random.randint(1, 100),
                    cost=Decimal(str(round(random.uniform(0, 100), 2))),
                    frozen_money=random.randint(1, 100),
                    source=random.choice([i for i in SOURCE_TYPES]),
                )
            )
        add_position_records(l)
        size1 = get_table_size(self.model)
        self.assertEqual(count1 + count2, size1 - size0)
        softdelete_position_records_by_portfolio_and_code(portfolio_id=portfolio_id, code=code1)
        time.sleep(0.01)
        size2 = get_table_size(self.model)
        self.assertEqual(-count1, size2 - size1)

        softdelete_position_records_by_portfolio_and_code(portfolio_id=portfolio_id, code=code2)
        time.sleep(0.01)
        size3 = get_table_size(self.model)
        self.assertEqual(-count2, size3 - size2)

    def test_OperationPositionrecord_exists(self) -> None:
        pass

    def test_OperationPositionrecord_exceptions(self) -> None:
        pass
