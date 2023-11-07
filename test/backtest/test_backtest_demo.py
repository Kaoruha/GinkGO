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
        interval = 20
        datestart = 20000101
        dateend = 20020101

        portfolio = PortfolioT1Backtest()

        codes = GDATA.get_stock_info_df()
        # codes = codes[45:3000]
        codes = codes.code.to_list()
        import random

        codes = random.sample(codes, 200)

        # selector = FixedSelector(["000001.SZ", "000002.SZ"])
        # selector = FixedSelector(["000042.SZ"])
        selector = FixedSelector(codes)
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
        engine.start()
        # for i in range(4000):
        #     print(i)
        #     print(i)
        #     engine.put(EventNextPhase())
        #     # time.sleep(interval)
        #     r = portfolio.cash + portfolio.fee
        #     for i in portfolio.positions.keys():
        #         pos = portfolio.positions[i]
        #         r += pos.volume * pos.cost
        #     print(f"CAL: {r}")
        #     print(f"FROZEN: {portfolio.frozen}")
        #     self.assertLessEqual(portfolio.frozen, 1e-5)
        #     pf = 0
        #     for pos in portfolio.positions.keys():
        #         pf += portfolio.get_position(pos).frozen
        #     self.assertLessEqual(pf, 1e-5)
        # engine.stop()
