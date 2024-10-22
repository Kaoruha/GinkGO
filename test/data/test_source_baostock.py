# import sys
# import unittest
# import datetime
# from time import sleep
# import pandas as pd
# from ginkgo.data.sources import GinkgoBaoStock
# from rich.console import Console

# console = Console()


# class BaoStockTest(unittest.TestCase):
#     """
#     UnitTest for Daybar.
#     """

#     # Init
#     # Change
#     # Amplitude

#     def __init__(self, *args, **kwargs) -> None:
#         super(BaoStockTest, self).__init__(*args, **kwargs)
#         self.bs = GinkgoBaoStock()

#     def test_Bao_Login(self) -> None:
#         self.bs.login()
#         self.assertEqual(self.bs.client.error_code, "0")

#     def test_Bao_Logout(self) -> None:
#         self.bs.login()
#         self.bs.logout()
#         self.assertEqual(self.bs.client.error_code, "0")

#     def test_Bao_FetchTradeDay(self) -> None:
#         r = self.bs.fetch_cn_stock_trade_day()
#         self.assertGreater(r.shape[0], 100)

#     def test_Bao_FetchCNStockList(self) -> None:
#         date = "2017-06-30"
#         r = self.bs.fetch_cn_stock_list(date)
#         self.assertEqual(r.shape[0], 3824)

#     def test_Bao_FetchCNDaybar(self) -> None:
#         code = "sh.600000"
#         date_start = "2017-07-01"
#         date_end = "2017-07-31"
#         r = self.bs.fetch_cn_stock_daybar(code, date_start, date_end)
#         self.assertEqual(r.shape[0], 21)

#     def test_Bao_FetchCNMin5(self) -> None:
#         pass
#         # code = "sh.600000"
#         # date_start = "2017-07-01"
#         # date_end = "2017-07-31"
#         # self.bs.login()
#         # r = self.bs.fetch_cn_stock_min5(code, date_start, date_end)
#         # self.assertEqual(r.shape[0], 1008)

#     def test_Bao_FetchAdjustfactor(self) -> None:
#         code = "sh.600519"
#         date_start = "2015-01-01"
#         date_end = "2017-07-31"
#         r = self.bs.fetch_cn_stock_adjustfactor(code, date_start, date_end)
#         self.assertEqual(r.shape[0], 3)
