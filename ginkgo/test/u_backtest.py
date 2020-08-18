import threading
import time
from ginkgo.backtest.engine import Ginkgo_Engine
from ginkgo.backtest.portfolio import Portfolio
from ginkgo.backtest.judger import Judger
from ginkgo.backtest.capital_controls.cash_scale_limit import CashScaleLimit
from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.strategies.moving_average import MACD
from ginkgo.backtest.info import DailyPrice, MinutePrice, MarketMSG
# from ginkgo.backtest.engine_portal import engine_portal
from ginkgo.backtest.strategies.test_strategy import TestStrategy

def run():
    portfolio = Portfolio(name='test')
    judger = Judger()
    heartbeat = 0
    strategy_ma = TestStrategy()
    portfolio.register_strategy(strategy_ma)
    backtest = Ginkgo_Engine(portfolio=portfolio, heartbeat=heartbeat)
    print('hh')
    # df = data_portal.query_stock(code='sh.600000',
    #                              start_date='1990-01-02',
    #                              end_date='2020-10-01',
    #                              frequency='d',
    #                              adjust_flag=1)
    # for i in range(df.count().date):
    #     info = DailyPrice(data=df.iloc[i])
    #     backtest.put_info(info=info)


if __name__ == '__main__':
    run()

