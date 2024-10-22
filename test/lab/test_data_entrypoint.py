import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.data.sources import GinkgoTDX
from ginkgo.data import *


class DataEntryPointTest(unittest.TestCase):
    """
    Test TDX data source
    """

    def __init__(self, *args, **kwargs) -> None:
        super(DataEntryPointTest, self).__init__(*args, **kwargs)

    # def test_fetch_and_update_stockinfo(self):
    #     fetch_and_update_stockinfo()

    # def test_get_stock_infos(self):
    #     df = get_stockinfos()
    #     print(df)

    # def test_fetch_and_update_cn_daybar(self):
    #     fetch_and_update_cn_daybar("600594.SH", fast_mode=True)

    # def test_fetch_and_update_cn_tick_on_date(self):
    #     fetch_and_update_tick_on_date(code="600594.SH", date="2020-04-01", fast_mode=True)

    # def test_fetch_and_update_cn_tick(self):
    #     fetch_and_update_tick(code="600594.SH", fast_mode=True)

    def test_engine_add(self):
        from ginkgo.data import add_engine, get_engines

        df = get_engines(name="backtest_example")
        if df.shape[0] == 0:
            add_engine(name="backtest_example", is_live=False)

    def test_engine_del(self):
        pass

    def test_engine_edit(self):
        pass

    def test_engine_get(self):
        from ginkgo.data import get_engines

        df = get_engines()
        print(df)

    def test_file_init(self):
        from ginkgo.data import init_example_data

        init_example_data()

    def test_file_add(self):
        pass

    def test_file_del(self):
        pass

    def test_file_edit(self):
        pass

    def test_file_get(self):
        from ginkgo.data import get_files

        df = get_files()
        print(df)

    def test_portfolio_add(self):
        pass

    def test_portfolio_del(self):
        pass

    def test_portfolio_edit(self):
        pass

    def test_portfolio_get(self):
        pass

    def test_engine_portfolio_mapping_add(self):
        pass

    def test_engine_portfolio_mapping_del(self):
        pass

    def test_engine_portfolio_mapping_edit(self):
        pass

    def test_engine_portfolio_mapping_get(self):
        pass

    def test_handler_add(self):
        pass

    def test_handler_del(self):
        pass

    def test_handler_edit(self):
        pass

    def test_handler_get(self):
        pass

    def test_handler_params_add(self):
        pass

    def test_handler_params_del(self):
        pass

    def test_handler_params_edit(self):
        pass

    def test_handler_params_get(self):
        pass

    def test_run_backtest(self):
        pass
