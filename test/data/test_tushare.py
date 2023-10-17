import sys
import time
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.libs.ginkgo_logger import GLOG

from ginkgo.data.sources import GinkgoTushare


class TuShareTest(unittest.TestCase):
    """
    UnitTest for Tushare.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(TuShareTest, self).__init__(*args, **kwargs)
        self.ts = GinkgoTushare()

    def test_Tu_Connect(self) -> None:
        gts = GinkgoTushare()
        gts.connect()
        self.assertNotEqual(gts.pro, None)

    def test_TuTradeDay(self) -> None:
        gts = GinkgoTushare()
        rs = gts.fetch_cn_stock_trade_day()
        l = rs.shape[0]
        self.assertGreater(l, 0)

    def test_TuFetchStockInfo(self) -> None:
        gts = GinkgoTushare()
        rs = gts.fetch_cn_stock_info()
        l = rs.shape[0]
        self.assertGreater(l, 2000)

    def test_TuFetchDaybar(self) -> None:
        pass
