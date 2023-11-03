import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


app = typer.Typer(help="Module for Backtest")


class ResourceType(str, Enum):
    backtest = "backtest"
    strategy = "strategy"
    selector = "selector"
    sizer = "sizer"
    risk_manager = "risk"
    portfolio = "portfolio"
    analyzer = "analyzer"
    plot = "plot"


@app.command()
def list(
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)],
):
    """
    Show backtest summary.
    """
    pass


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Run Backtest.
    """
    # TODO The DEMO param should be replaced with dynamic backtest id.
    # TODO backtest id -->> backtest file -->> backtest setting.
    # TODO setting could be a yaml, include sizer_id, selector_id, start and end, strategy_ids with setting(read strategy, and export dynamic parameters to set).
    # TODO Create a temp folder, copy sizer.py selector.py and so on.
    # TODO Dynamic create a .py file with dynamic import.
    # TODO Run backtest, and do index monitor, put back to the model of backtest(strategy).
    # TODO Remove the temp folder.

    import time
    import random
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

    datestart = 20000101

    portfolio = PortfolioT1Backtest()

    codes = GDATA.get_stock_info_df()
    codes = codes.code.to_list()

    codes = random.sample(codes, 200)
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


@app.command()
def edit(
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)],
    id: Annotated[str, typer.Option(case_sensitive=True)],
):
    """
    Edit Resources.
    """
    pass
