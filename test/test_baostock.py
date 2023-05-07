import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_conf import GINKGOCONF
from ginkgo.data import GinkgoBaoStock


class BaoStockTest(unittest.TestCase):
    """
    UnitTest for Daybar.
    """

    # Init
    # Change
    # Amplitude

    def __init__(self, *args, **kwargs) -> None:
        super(BaoStockTest, self).__init__(*args, **kwargs)
        self.bs = GinkgoBaoStock()

    def test_Bao_Login(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        self.bs.login()
        self.assert_(self.bs.client.error_code, 0)

    def test_Bao_Logout(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        self.bs.login()
        self.bs.logout()
        self.assert_(self.bs.client.error_code, 0)

    def test_Bao_FetchTradeDay(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.bs.fetch_trade_day()
        self.assertGreater(r.shape[0], 100)

    def test_Bao_TradeDay(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.bs.trade_day
        self.assertGreater(r.shape[0], 100)

    def test_Bao_TradeDayInCache(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        r = self.bs.trade_day
        time1 = datetime.datetime.now()
        r = self.bs.trade_day
        time2 = datetime.datetime.now()
        self.assertGreater(datetime.timedelta(seconds=0.0001), time2 - time1)

    def test_Bao_FetchAList(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        date = "2017-06-30"
        r = self.bs.fetch_ashare_list(date)
        self.assertEqual(r.shape[0], 3824)

    def test_Bao_FetchAStockDaybar(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        code = "sh.600000"
        date_start = "2017-07-01"
        date_end = "2017-07-31"
        r = self.bs.fetch_ashare_stock_daybar(code, date_start, date_end)
        self.assertEqual(r.shape[0], 21)

    def test_Bao_FetchAStockMin5(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        code = "sh.600519"
        date_start = "2017-07-01"
        date_end = "2017-07-31"
        r = self.bs.fetch_ashare_stock_min5(code, date_start, date_end)
        self.assertEqual(r.shape[0], 1008)

    def test_Bao_Adjustfactor(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        code = "sh.600519"
        date_start = "2015-01-01"
        date_end = "2017-07-31"
        r = self.bs.fetch_akshare_adjustfactor(code, date_start, date_end)
        print(r)
        self.assertEqual(r.shape[0], 3)

    def test_Bao_GetTodaysDaybar(self) -> None:
        sleep(GINKGOCONF.HEARTBEAT)
        fail_count = 0
        fail_limit = 30
        date = datetime.datetime.now() + datetime.timedelta(days=-2)
        while fail_count <= fail_limit:
            stock_list = self.bs.fetch_ashare_list(date.strftime("%Y-%m-%d"))
            if stock_list.shape[0] == 0:
                fail_count += 1
                date = date + datetime.timedelta(days=-1)
                print(date, end="\r")
            else:
                break
            sleep(0.1)
        self.assertGreater(stock_list.shape[0], 0)
        self.assertGreater(fail_limit, fail_count)
        success_count = 0
        success_limit = 10
        for i in stock_list.iterrows():
            item = i[1]
            code = item.code
            datef = date.strftime("%Y-%m-%d")
            day = self.bs.fetch_ashare_stock_daybar(code, datef, datef)
            sys.stdout.write("\033[K")
            if day.shape[0] > 0:
                success_count += 1
            print(f"{code}: {success_count}", end="\r")
            if success_count >= success_limit:
                break
