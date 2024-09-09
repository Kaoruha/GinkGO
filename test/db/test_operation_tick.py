import unittest
import time

from ginkgo.data.models import MTick
from ginkgo.backtest import Tick
from ginkgo.enums import TICKDIRECTION_TYPES
from src.ginkgo.data.operations.tick_crud import *
from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table


class OperationTickTest(unittest.TestCase):
    """
    UnitTest for Tick CRUD
    """

    def __init__(self, *args, **kwargs) -> None:
        super(OperationTickTest, self).__init__(*args, **kwargs)
        self.params = [
            {
                "code": "testcode001",
                "price": 10.1,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:01",
            },
            {
                "code": "testcode001",
                "price": 10.2,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:02",
            },
            {
                "code": "testcode001",
                "price": 10.3,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:03",
            },
            {
                "code": "testcode001",
                "price": 10.4,
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.OTHER,
                "timestamp": "2020-01-01 10:00:04",
            },
        ]

    def rebuild_table(self) -> None:
        codes = []
        for i in self.params:
            code = i["code"]
            if code not in codes:
                codes.append(code)

        for i in codes:
            drop_table(get_tick_model(code))
        time.sleep(0.5)

        for i in codes:
            create_table(get_tick_model(code))
        time.sleep(0.5)

    def test_OperationTick_create(self) -> None:
        self.rebuild_table()
        for i in self.params:
            model = get_tick_model(i["code"])
            size0 = get_table_size(model)
            add_tick(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            time.sleep(0.5)
            size1 = get_table_size(model)
            self.assertEqual(1, size1 - size0)

    def test_OperationTick_bulkinsert(self) -> None:
        self.rebuild_table()
        to_insert = {}
        for i in self.params:
            item = Tick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            if i["code"] not in to_insert:
                to_insert[i["code"]] = []
            to_insert[i["code"]].append(item)
        for k, v in to_insert.items():
            model = get_tick_model(k)
            size0 = get_table_size(model)
            add_ticks(v)
            time.sleep(0.5)
            size1 = get_table_size(model)
            self.assertEqual(len(v), size1 - size0)

    def test_OperationTick_update(self) -> None:
        pass

    def test_OperationTick_read(self) -> None:
        # in format Tick
        # in format dataframe
        self.rebuild_table()
        codes = []
        for i in self.params:
            code = i["code"]
            if code not in codes:
                codes.append(code)

        l = []
        for i in self.params:
            code = i["code"]
            time.sleep(0.5)
            item = Tick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            l.append(item)
        add_ticks(l)
        time.sleep(0.5)
        res = get_tick(code="testcode001")
        self.assertEqual(len(self.params), len(res))
        df = get_tick(code="testcode001", as_dataframe=True)
        self.assertEqual(df.shape[0], len(self.params))

    def test_OperationTick_read_with_date_range(self) -> None:
        # in format Tick
        # in format dataframe
        self.rebuild_table()
        l = []
        for i in self.params:
            code = i["code"]
            time.sleep(0.5)
            item = Tick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            l.append(item)
        add_ticks(l)
        time.sleep(0.5)
        res = get_tick(code="testcode001", start_date="2020-01-01 10:00:01", end_date="2020-01-01 10:00:02")
        self.assertEqual(2, len(res))
        df = get_tick(
            code="testcode001", start_date="2020-01-01 10:00:01", end_date="2020-01-01 10:00:02", as_dataframe=True
        )
        self.assertEqual(2, df.shape[0])

    def test_OperationTick_read_with_pagination(self) -> None:
        # in format Tick
        # in format dataframe
        self.rebuild_table()
        l = []
        for i in self.params:
            code = i["code"]
            time.sleep(0.5)
            item = Tick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            l.append(item)
        add_ticks(l)
        time.sleep(0.5)
        res = get_tick(
            code="testcode001", start_date="2020-01-01 10:00:01", end_date="2020-01-01 10:00:03", page=1, page_size=2
        )
        self.assertEqual(1, len(res))
        df = get_tick(
            code="testcode001",
            start_date="2020-01-01 10:00:01",
            end_date="2020-01-01 10:00:03",
            page=1,
            page_size=2,
            as_dataframe=True,
        )
        self.assertEqual(1, df.shape[0])

    def test_OperationTick_softdelete(self) -> None:
        self.rebuild_table()

    def test_OperationTick_delete(self) -> None:
        self.rebuild_table()
        l = []
        for i in self.params:
            code = i["code"]
            time.sleep(0.5)
            item = Tick()
            item.set(i["code"], i["price"], i["volume"], i["direction"], i["timestamp"])
            l.append(item)
        add_ticks(l)

    def test_OperationTick_exists(self) -> None:
        pass

    def test_OperationTick_exceptions(self) -> None:
        pass
