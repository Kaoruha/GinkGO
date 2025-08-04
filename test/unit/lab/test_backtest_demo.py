import sys
import unittest
import datetime
from time import sleep
import pandas as pd
from ginkgo.data import *
from ginkgo.backtest.execution.engines import HistoricEngine
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
from ginkgo.backtest.analysis.analyzers import Profit
from ginkgo.backtest.execution.feeders import BacktestFeeder
from ginkgo.backtest.strategy.selectors import FixedSelector
from ginkgo.backtest.strategy.sizers import FixedSizer
from ginkgo.backtest.strategy.strategies import StrategyRandomChoice

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
