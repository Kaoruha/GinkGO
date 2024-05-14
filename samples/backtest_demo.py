from ginkgo.enums import *
from ginkgo.backtest.events import *
from ginkgo.backtest.feeds import BacktestFeed


from ginkgo.backtest.portfolios import PortfolioT1Backtest

portfolio = PortfolioT1Backtest()  # TODO Read from database.

from ginkgo.backtest.selectors import FixedSelector, CNAllSelector

selector = FixedSelector(
    "test_selector",
    [
        "000001.SZ",
        "000002.SZ",
        "000003.SZ",
        "000004.SZ",
        "000005.SZ",
        "000006.SZ",
        "000007.SZ",
        "000008.SZ",
        "000009.SZ",
        "000010.SZ",
        "000011.SZ",
    ],
)
# selector = FixedSelector(
#     "test_selector",
#     [
#         "000001.SZ",
#     ],
# )
portfolio.bind_selector(selector)

from ginkgo.backtest.sizers import FixedSizer

sizer = FixedSizer("fixed", 1000)
portfolio.bind_sizer(sizer)

from ginkgo.backtest.risk_managements import NoRiskManagement

risk = NoRiskManagement()
portfolio.bind_risk(risk)

from ginkgo.backtest.strategies import (
    StrategyLossLimit,
    StrategyProfitLimit,
    StrategyVolumeActivate,
)

losslimit = StrategyLossLimit("losslimit", 15)
portfolio.add_strategy(losslimit)
profitlimit = StrategyProfitLimit("profitlimit", 20)
portfolio.add_strategy(profitlimit)
volumeactivate = StrategyVolumeActivate("volumea", 20)
portfolio.add_strategy(volumeactivate)

from ginkgo.backtest.analyzers import NetValue, Profit

netvalue = NetValue("net")
portfolio.add_analyzer(netvalue)
profit = Profit("profit")
portfolio.add_analyzer(profit)

from ginkgo.backtest.engines import HistoricEngine

engine = HistoricEngine()
engine.set_backtest_interval("day")
engine.set_date_start("2000-01-01")
engine.set_date_end("2020-01-01")
engine.bind_portfolio(portfolio)


from ginkgo.backtest.matchmakings import MatchMakingSim

matchmaking = MatchMakingSim()
engine.bind_matchmaking(matchmaking)

from ginkgo.backtest.feeds import BacktestFeed

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
