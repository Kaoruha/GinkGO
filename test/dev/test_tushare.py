import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.data import GinkgoTushare


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

    # def test_Tu_Connect(self) -> None:
    #     gts = GinkgoTushare()
    #     gts.connect()
    #     self.assertNotEqual(gts.pro, None)

    def test_TuTradeDay(self) -> None:
        gts = GinkgoTushare()
        gts.connect()
        rs = gts.fetch_cn_stock_trade_day()
