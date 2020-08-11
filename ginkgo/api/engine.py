import threading
from ginkgo.libs.thread_manager import thread_manager
from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.libs.response import NoException
from ginkgo.backtest.engine_portal import engine_portal
from ginkgo.backtest.portfolio import Portfolio
from ginkgo.backtest.judger import Judger
from ginkgo.backtest.strategies.test_strategy import TestStrategy
from ginkgo.backtest.simulate_engine import Ginkgo_Engine
from ginkgo.backtest.info import DailyPrice, MinutePrice, MarketMSG
from ginkgo.data.data_portal import data_portal
from ginkgo.libs.socket_manager import socket_boost

yp_engine = YellowPrint('rp_engine', url_prefix='/engine')


@yp_engine.route('/boost', methods=['POST'])
def engine_boost():
    portfolio = Portfolio(name='test')
    judger = Judger()
    heartbeat = 0
    strategy_ma = TestStrategy()
    portfolio.register_strategy(strategy_ma)
    backtest = Ginkgo_Engine(portfolio=portfolio, heartbeat=heartbeat)
    result = engine_portal.engine_register(engine=backtest)
    return NoException(msg=result)


@yp_engine.route('/sleep', methods=['POST'])
def engine_sleep_now():
    result = engine_portal.engine_sleep('test')
    return NoException(msg=result)


@yp_engine.route('/resume', methods=['POST'])
def engine_resume():
    result = engine_portal.engine_resume('test')
    return NoException(msg=result)


@yp_engine.route('/info_injection', methods=['POST'])
def info_injection():
    thread = threading.Thread(target=data_injection,
                              name='test_info_injection',
                              )
    thread_manager.thread_register(thread)  # 线程管理,新建引擎的线程
    return NoException(msg='Begin to inject')


@yp_engine.route('/socket_boost', methods=['POST'])
def socket_run():
    socket_boost()
    return NoException(msg='socket boost on!')


def data_injection():
    df = data_portal.query_stock(code='sh.600000',
                                 start_date='1990-01-02',
                                 end_date='2020-10-01',
                                 frequency='d',
                                 adjust_flag=1)
    for i in range(df.count().date):
        info = DailyPrice(data=df.iloc[i])
        engine_portal.info_injection('test', info=info)
