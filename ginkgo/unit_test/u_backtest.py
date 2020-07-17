from ginkgo.backtest.backtest import BeuBacktest
from ginkgo.backtest.portfolio import Portfolio
from ginkgo.backtest.judger import Judger
from ginkgo.backtest.fund.cash_scale_limit import CashScaleLimit
from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.strategies.base_strategy import BaseStrategy
import threading
from ginkgo.backtest.info import InfoPrice, InfoMsg
import time


portfolio = Portfolio()
judger = Judger()
heartbeat = 1
strategy = BaseStrategy()
unit_backtest = BeuBacktest(strategy=strategy,
                            portfolio=portfolio,
                            heartbeat=heartbeat)


def u_backtest():
    unit_backtest._run()

def add_data():
    df = data_portal.query_stock(code='sh.600000',
                            start_date='1999-01-02',
                            end_date='2001-01-01',
                            frequency='d',
                            adjust_flag=2)
    for i in range(df.count().date):
        info = InfoPrice(data=df.iloc[i])
        unit_backtest._add_info(info)
        time.sleep(2)

def unit_test_backtest():
    t = threading.Thread(target=u_backtest, name='u_backtest')
    t.start()

def unit_test_feed():
    d = threading.Thread(target=add_data, name='u_backtest_feed')
    d.start()
