import threading
import time
from ginkgo.backtest.simulate_engine import Ginkgo_Engine
from ginkgo.backtest.portfolio import Portfolio
from ginkgo.backtest.judger import Judger
from ginkgo.backtest.fund.cash_scale_limit import CashScaleLimit
from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.strategies.base_strategy import BaseStrategy
from ginkgo.backtest.info import DailyPrice, MinutePrice, MarketMSG

portfolio = Portfolio()
judger = Judger()
heartbeat = .01
strategy = BaseStrategy()
unit_backtest = Ginkgo_Engine(strategy=strategy,
                            portfolio=portfolio,
                            heartbeat=heartbeat)


def u_backtest():
    unit_backtest._run()


def add_data():
    df = data_portal.query_stock(code='sh.600000',
                                 start_date='1990-01-02',
                                 end_date='2020-10-01',
                                 frequency='d',
                                 adjust_flag=1)
    for i in range(df.count().date):
        info = DailyPrice(data=df.iloc[i])
        unit_backtest._add_info(info)
        # time.sleep(.1)


def unit_test_backtest():
    t = threading.Thread(target=u_backtest, name='u_backtest')
    t.start()


def unit_test_feed():
    feed = threading.Thread(target=add_data, name='u_backtest_feed')
    feed.start()
