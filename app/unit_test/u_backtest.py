from app.backtest.backtest import BeuBacktest
from app.backtest.portfolio import Portfolio
from app.backtest.judger import Judger
from app.backtest.fund.cash_scale_limit import CashScaleLimit
from app.data.beu_data import beu_data
from app.backtest.strategies.base_strategy import BaseStrategy

df = beu_data.query_stock(code='sh.600000',
                         start_date='1999-01-02',
                         end_date='1999-01-01',
                         frequency='d',
                          adjust_flag=2)
portfolio = Portfolio()
judger = Judger()
heartbeat = 1
strategy = BaseStrategy()
unit_backtest = BeuBacktest(data=df,strategy=strategy, portfolio=portfolio, heartbeat=heartbeat)

def unit_test_backtest():
    unit_backtest._run()