import unittest
import time
import pandas as pd
import datetime
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import EVENT_TYPES
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.engines import EventEngine
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.matchmakings import MatchMakingSim
from ginkgo.backtest.sizers import FixedSizer
from ginkgo.backtest.events import EventNextPhase
from ginkgo.backtest.feeds import BacktestFeed
from ginkgo.backtest.strategies import (
    StrategyVolumeActivate,
    StrategyProfitLimit,
    StrategyLossLimit,
)
from ginkgo.backtest.analyzers import NetValue


class BacktestTest(unittest.TestCase):
    """
    UnitTest for Backtest.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BacktestTest, self).__init__(*args, **kwargs)

    def test_btselector_Init(self) -> None:
        selector = FixedSelector("test", ["301529.SZ", "603270.SH"])
        self.assertEqual(selector.pick(), ["301529.SZ", "603270.SH"])

    def test_btengine_Init(self) -> None:
        engine = EventEngine()
        self.assertTrue(True)

    def test_btrisk_Init(self) -> None:
        risk = BaseRiskManagement()
        self.assertTrue(True)

    def test_btsizer_Init(self) -> None:
        sizer = FixedSizer()
        self.assertTrue(True)

    def test_backtest_demo(self) -> None:
        interval = 20
        datestart = 20140101
        dateend = 20140106

        portfolio = PortfolioT1Backtest()

        codes = GDATA.get_stock_info_df()
        # codes = codes[45:3000]
        codes = codes.code.to_list()
        import random

        codes = random.sample(codes, 20)

        # selector = FixedSelector(["000001.SZ", "000002.SZ"])
        # selector = FixedSelector(["000042.SZ"])
        selector = FixedSelector("test", codes)
        portfolio.bind_selector(selector)

        risk = BaseRiskManagement()
        portfolio.bind_risk(risk)

        sizer = FixedSizer(name="500Sizer", volume=500)
        portfolio.bind_sizer(sizer)

        strategy = StrategyVolumeActivate()
        win_stop = StrategyProfitLimit(5)
        lose_stop = StrategyLossLimit(5)
        portfolio.add_strategy(strategy)
        portfolio.add_strategy(win_stop)
        portfolio.add_strategy(lose_stop)

        index_netvalue = NetValue("net value")
        portfolio.add_analyzer(index_netvalue)

        engine = EventEngine()
        engine.set_backtest_interval("day")
        engine.set_date_start(datestart)
        engine.set_date_end(dateend)
        engine.bind_portfolio(portfolio)
        matchmaking = MatchMakingSim()
        engine.bind_matchmaking(matchmaking)
        feeder = BacktestFeed()
        feeder.subscribe(portfolio)
        engine.bind_datafeeder(feeder)

        # Event Handler Register
        engine.register(EVENT_TYPES.NEXTPHASE, engine.nextphase)
        engine.register(EVENT_TYPES.NEXTPHASE, feeder.broadcast)
        engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_update)
        engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_update)
        engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
        engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_stock_order)
        engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
        engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)

        engine.put(EventNextPhase())
        t = engine.start()
        t.join()
        self.assertTrue(True)
