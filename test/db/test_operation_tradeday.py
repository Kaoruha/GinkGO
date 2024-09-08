import unittest
import time
from ginkgo.enums import MARKET_TYPES
from src.ginkgo.data.drivers import get_table_size, create_table, add_all, drop_table
from src.ginkgo.data.models import MTradeDay
from src.ginkgo.data.operations.tradeday_crud import *


class OperationTradedayTest(unittest.TestCase):
    """
    UnitTest for Tradeday CRUD
    """

    def __init__(self, *args, **kwargs) -> None:
        super(OperationTradedayTest, self).__init__(*args, **kwargs)
        self.params = [
            {"timestamp": "2020-01-01", "is_open": True, "market": MARKET_TYPES.CHINA},
            {"timestamp": "2020-01-02", "is_open": True, "market": MARKET_TYPES.CHINA},
            {"timestamp": "2020-01-03", "is_open": False, "market": MARKET_TYPES.CHINA},
            {"timestamp": "2020-01-04", "is_open": True, "market": MARKET_TYPES.CHINA},
        ]

    def test_OperationTradeday_create(self) -> None:
        create_table(MTradeDay)
        size0 = get_table_size(MTradeDay)
        for i in self.params:
            add_tradeday(
                market=i["market"],
                is_open=i["is_open"],
                timestamp=i["timestamp"],
            )
            size1 = get_table_size(MTradeDay)
            self.assertEqual(1, size1 - size0)
            size0 = size1

    def test_OperationTradeday_bulkinsert(self) -> None:
        create_table(MTradeDay)
        size0 = get_table_size(MTradeDay)
        l = []
        for i in self.params:
            item = MTradeDay()
            item.set(i["market"], i["is_open"], i["timestamp"])
            l.append(item)
        add_tradedays(l)
        size1 = get_table_size(MTradeDay)
        self.assertEqual(len(l), size1 - size0)

    def test_OperationTradeday_update(self) -> None:
        # no need to update
        pass

    def test_OperationTradeday_read_by_date_range(self) -> None:
        drop_table(MTradeDay)
        create_table(MTradeDay)
        for i in self.params:
            size0 = get_table_size(MTradeDay)
            add_tradeday(
                market=i["market"],
                is_open=i["is_open"],
                timestamp=i["timestamp"],
            )
            size1 = get_table_size(MTradeDay)
            self.assertEqual(size1 - size0, 1)

        data = get_tradeday_by_market_and_date_range(MARKET_TYPES.CHINA, "2020-01-01", "2020-01-02")
        df = get_tradeday_by_market_and_date_range(MARKET_TYPES.CHINA, "2020-01-01", "2020-01-02", as_dataframe=True)
        self.assertEqual(2, len(data))
        self.assertEqual(2, df.shape[0])
        data = get_tradeday_by_market_and_date_range(
            market=MARKET_TYPES.CHINA, start_date="2020-01-01", end_date="2020-01-03", page=0, page_size=2
        )
        df = get_tradeday_by_market_and_date_range(
            market=MARKET_TYPES.CHINA,
            start_date="2020-01-01",
            end_date="2020-01-03",
            as_dataframe=True,
            page=0,
            page_size=2,
        )
        self.assertEqual(2, len(data))
        self.assertEqual(2, df.shape[0])
        data = get_tradeday_by_market_and_date_range(
            market=MARKET_TYPES.CHINA, start_date="2020-01-01", end_date="2020-01-03", page=1, page_size=2
        )
        df = get_tradeday_by_market_and_date_range(
            market=MARKET_TYPES.CHINA,
            start_date="2020-01-01",
            end_date="2020-01-03",
            as_dataframe=True,
            page=1,
            page_size=2,
        )
        self.assertEqual(1, len(data))
        self.assertEqual(1, df.shape[0])

    def test_OperationTradeday_delete(self) -> None:
        drop_table(MTradeDay)
        create_table(MTradeDay)
        create_table(MTradeDay)
        size0 = get_table_size(MTradeDay)
        l = []
        for i in self.params:
            item = MTradeDay()
            item.set(i["market"], i["is_open"], i["timestamp"])
            l.append(item)
        add_all(l)
        time.sleep(0.1)
        size1 = get_table_size(MTradeDay)
        self.assertEqual(len(l), size1 - size0)
        delete_tradeday_by_date_range(start_date="2020-01-01", end_date="2020-01-03")
        time.sleep(0.1)
        size2 = get_table_size(MTradeDay)
        self.assertEqual(-3, size2 - size1)

    def test_OperationTradeday_exists(self) -> None:
        pass

    def test_OperationTradeday_exceptions(self) -> None:
        create_table(MTradeDay)
        pass
