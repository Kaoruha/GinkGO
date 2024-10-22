# import sys
# import time
# import unittest
# import datetime
# from time import sleep
# import pandas as pd
# from ginkgo.libs.ginkgo_logger import GLOG

# from ginkgo.data.sources import GinkgoTushare


# class TuShareTest(unittest.TestCase):
#     """
#     Test tushare data source.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(TuShareTest, self).__init__(*args, **kwargs)
#         self.ts = GinkgoTushare()

#     def test_Tu_Connect(self) -> None:
#         gts = GinkgoTushare()
#         gts.connect()
#         self.assertNotEqual(gts.pro, None)

#     def test_Tu_FetchTradeDay(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_trade_day()
#         l = rs.shape[0]
#         self.assertGreater(l, 1000)

#     def test_Tu_FetchStockInfo(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_info()
#         l = rs.shape[0]
#         self.assertGreater(l, 2000)

#     def test_Tu_FetchDaybar(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_daybar("000001.SZ", "20200101", "20200110")
#         l = rs.shape[0]
#         self.assertGreater(l, 0)

#     def test_Tu_FetchAdjustfactor(self) -> None:
#         gts = GinkgoTushare()
#         rs = gts.fetch_cn_stock_adjustfactor("000001.SZ", "20100101", "20200110")
#         l = rs.shape[0]
#         self.assertGreater(l, 0)
