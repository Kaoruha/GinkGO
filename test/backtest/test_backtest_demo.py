import unittest
import time
import pandas as pd
import datetime
from ginkgo import GLOG
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.selectors import FixedSelector
from ginkgo.backtest.engines import EventEngine
from ginkgo.backtest.portfolios import PortfolioT1Backtest
from ginkgo.backtest.risk_managements import BaseRiskManagement
from ginkgo.backtest.matchmakings import MatchMakingSim
from ginkgo.backtest.sizers import FixedSizer
from ginkgo.backtest.events import EventNextPhase
from ginkgo.backtest.feeds import BacktestFeed


class BacktestTest(unittest.TestCase):
    """
    UnitTest for Backtest.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BacktestTest, self).__init__(*args, **kwargs)

    def test_btselector_Init(self) -> None:
        selector = FixedSelector(["301529.SZ", "603270.SH"])

    def test_btengine_Init(self) -> None:
        engine = EventEngine()

    def test_btrisk_Init(self) -> None:
        risk = BaseRiskManagement()

    def test_btsizer_Init(self) -> None:
        sizer = FixedSizer()

    def test_btportfolio_Init(self) -> None:
        interval = 1
        portfolio = PortfolioT1Backtest()
        selector = FixedSelector(["000001.SZ", "000002.SZ"])
        datestart = 20230412
        portfolio.bind_selector(selector)
        risk = BaseRiskManagement()
        portfolio.bind_risk(risk)
        sizer = FixedSizer()
        portfolio.bind_sizer(sizer)

        engine = EventEngine()
        engine.set_backtest_interval("day")
        engine.set_date_start(datestart)
        engine.bind_portfolio(portfolio)
        matchmaking = MatchMakingSim()
        engine.bind_matchmaking(matchmaking)
        feeder = BacktestFeed()
        feeder.subscribe(portfolio)
        engine.bind_datafeeder(feeder)

        engine.register(EVENT_TYPES.NEXTPHASE, engine.nextphase)
        engine.register(EVENT_TYPES.NEXTPHASE, feeder.broadcast)

        engine.start()
        engine.put(EventNextPhase())
        time.sleep(interval)
        self.assertEqual(engine.now, datetime_normalize(datestart + 1))
        self.assertEqual(portfolio.now, datetime_normalize(datestart + 1))
        self.assertEqual(matchmaking.now, datetime_normalize(datestart + 1))
        self.assertEqual(feeder.now, datetime_normalize(datestart + 1))
        # engine.put(EventNextPhase())
        # time.sleep(interval)
        # self.assertEqual(engine.now, datetime_normalize(datestart + 2))
        # self.assertEqual(portfolio.now, datetime_normalize(datestart + 2))
        # self.assertEqual(matchmaking.now, datetime_normalize(datestart + 2))
        # self.assertEqual(feeder.now, datetime_normalize(datestart + 2))
        engine.stop()
