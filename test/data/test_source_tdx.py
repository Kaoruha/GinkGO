import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.data.sources import GinkgoTDX


class TDXTest(unittest.TestCase):
    """
    Test TDX data source
    """

    def __init__(self, *args, **kwargs) -> None:
        super(TDXTest, self).__init__(*args, **kwargs)
        self.tdx = GinkgoTDX()

    def test_TDX_FetchLive(self):
        """
        Test TDX FetchLive
        """
        code = "000001.SZ"
        df = self.tdx.fetch_live([code])
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(df.shape[0], 0)

    def test_TDX_FetchLatestbar(self):
        code = "000001.SZ"
        df = self.tdx.fetch_latest_bar(code, 7, 10)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(df.shape[0], 0)

    def test_TDX_FetchStockList(self):
        df = self.tdx.fetch_stock_list()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(df.shape[0], 0)

    def test_TDX_FetchHistoryTransactionSummary(self):
        code = "000001.SZ"
        date = "2017-10-10"
        df = self.tdx.fetch_history_transaction_summary(code, date)
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(df.shape[0], 0)

    def test_TDX_FetchHistoryTransactionDetail(self):
        """
        Test TDX FetchHistoryTransaction
        """
        code = "000001.SZ"
        date = "2017-10-10"
        df = self.tdx.fetch_history_transaction_detail(code, date)
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)

    def test_TDX_FetchAdjustfactor(self):
        code = "600036.SZ"
        df = self.tdx.fetch_adjustfactor(code)
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)

    def test_TDXFetchHistoryDaybar(self):
        code = "600300.SZ"
        start_date = "2017-10-03"
        end_date = "2017-10-10"
        df = self.tdx.fetch_history_daybar(code, start_date, end_date)
        print(df)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
