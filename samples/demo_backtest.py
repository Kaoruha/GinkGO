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
from ginkgo.backtest.strategies import StrategyVolumeActivate, StrategyLossLimit


interval = 0.5
datestart = 20050412

portfolio = PortfolioT1Backtest()
selector = FixedSelector(["000001.SZ", "000002.SZ"])
portfolio.bind_selector(selector)

risk = BaseRiskManagement()
portfolio.bind_risk(risk)

sizer = FixedSizer(name="1000Sizer", volume=1000)
portfolio.bind_sizer(sizer)

strategy = StrategyVolumeActivate()
profit_loss_limit = StrategyLossLimit()
portfolio.add_strategy(strategy)
portfolio.add_strategy(profit_loss_limit)

engine = EventEngine()
engine.set_backtest_interval("day")
engine.set_date_start(datestart)
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

engine.start()
for i in range(4000):
    engine.put(EventNextPhase())
    time.sleep(interval)
engine.stop()
