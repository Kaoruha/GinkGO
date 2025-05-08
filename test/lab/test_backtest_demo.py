import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.data import *
from ginkgo.backtest.engines import HistoricEngine
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.analyzers import Profit
from ginkgo.backtest.feeders import BacktestFeeder
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.sizers import FixedSizer
from ginkgo.backtest.strategies import StrategyRandomChoice

engine_id = "backtest_example_001"


class BacktestTest(unittest.TestCase):
    """
    Backtest
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BacktestTest, self).__init__(*args, **kwargs)

    def test_backtest(self):
        # TODO Clean data
        engine = HistoricEngine()
        engine.engine_id = engine_id

        print(1123)
