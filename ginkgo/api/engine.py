from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.libs.response import NoException
# from ginkgo.backtest.engine_portal import engine_portal
from ginkgo.backtest.portfolio import Portfolio
from ginkgo.backtest.judger import Judger
from ginkgo.backtest.strategies.moving_average import MACD
from ginkgo.backtest.simulate_engine import Ginkgo_Engine

yp_engine = YellowPrint('rp_engine', url_prefix='/engine')


@yp_engine.route('/start', methods=['POST'])
def engine_start():
    portfolio = Portfolio(name='test')
    judger = Judger()
    heartbeat = .01
    strategy_ma = MACD()
    portfolio.register_strategy(strategy_ma)
    backtest = Ginkgo_Engine(portfolio=portfolio, heartbeat=heartbeat)
    # engine_portal.engine_register(engine=backtest, portfolio=portfolio)
    return NoException(msg='2222')


@yp_engine.route('/sleep', methods=['POST'])
def engine_sleep_now():
    # engine_portal.engine_sleep('test')
    return NoException(msg='Sleepy Girl')
