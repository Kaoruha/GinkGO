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

    def test_TDX_FetchHistoryTransaction(self):
        """
        Test TDX FetchHistoryTransaction
        """
        code = "000001.SZ"
        df = self.tdx.fetch_history_transaction(code, 20210104)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
