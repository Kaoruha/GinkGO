from ginkgo.data.data_portal import data_portal
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.broker.single_daily_broker import SingleDailyBroker
from ginkgo.backtest.enums import EventType
from ginkgo.backtest.strategy.moving_average import MovingAverageStrategy
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo.backtest.sizer.all_in_one import AllInOne
import datetime

if __name__ == '__main__':
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    df = data_portal.query_stock(code='sh.600519',
                                 start_date='1990-01-01',
                                 end_date=today,
                                 frequency='d',
                                 adjust_flag=2)

    # 引擎初始化
    backtest_engine = EventEngine()
    backtest_engine.set_heartbeat(.001)

    # 经纪人初始化
    my_broker = SingleDailyBroker(name='my_broker', engine=backtest_engine)

    # 策略挂载
    strategy = MovingAverageStrategy(short=5, long=60)
    my_broker.strategy_register(strategy)

    # 仓位管理挂载
    sizer = AllInOne()
    my_broker.sizer_register(sizer=sizer)

    # 模拟撮合类挂载
    matcher = SimulateMatcher()
    my_broker.matcher_register(matcher)

    # 事件处理函数注册
    backtest_engine.register(EventType.Market, my_broker.daily_handlers)
    backtest_engine.register(EventType.Signal, my_broker.signal_handlers)
    backtest_engine.register(EventType.Order, my_broker.order_handlers)
    backtest_engine.register(EventType.Fill, my_broker.fill_handlers)

    # 喂数据
    backtest_engine.feed(data=df)

    # 开启引擎
    backtest_engine.start()
