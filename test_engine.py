import datetime
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.broker.single_daily_broker import SingleDailyBroker
from ginkgo_server.backtest.enums import EventType
from ginkgo_server.data.stock.baostock_data import bao_instance
from ginkgo_server.backtest.strategy.moving_average import MovingAverageStrategy
from ginkgo_server.backtest.strategy.target_profit import TargetProfit
from ginkgo_server.backtest.strategy.stop_loss import StopLoss
from ginkgo_server.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo_server.backtest.sizer.all_in_one import AllInOne
from ginkgo_server.backtest.analyzer.normal_analyzer import NormalAnalyzer


if __name__ == "__main__":
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    df = gm.query_stock(
<<<<<<< HEAD
        code="sz.000725",
        start_date="1995-11-01",
=======
        code="sz.000735",
        start_date="2013-01-01",
>>>>>>> 86d65df12303c06b44bd27b63bd84ae53c1ceb23
        end_date=today,
        frequency="d",
        adjust_flag=3,
    )

    # 引擎初始化
    backtest_engine = EventEngine()
    # backtest_engine.set_heartbeat(0.001)

    # 经纪人初始化
    my_broker = SingleDailyBroker(name="my_broker", engine=backtest_engine)

    # 策略挂载
<<<<<<< HEAD
    ma_strategy = MovingAverageStrategy(short_term=10, long_term=60)
=======
    ma_strategy = MovingAverageStrategy(short_term=8, long_term=40)
>>>>>>> 86d65df12303c06b44bd27b63bd84ae53c1ceb23
    # target_profit = TargetProfit(target=20, target_reduce=50)
    # stop_loss = StopLoss(loss=5, target_reduce=80)
    my_broker.strategy_register(ma_strategy)
    # my_broker.strategy_register(target_profit)
    # my_broker.strategy_register(stop_loss)

    # 仓位管理挂载
    sizer = AllInOne()
    my_broker.sizer_register(sizer=sizer)

    # 模拟撮合类挂载
    matcher = SimulateMatcher()
    my_broker.matcher_register(matcher)

    # 分析类挂载
    analyzer = NormalAnalyzer()
    my_broker.analyzer_register(analyzer)

    # 事件处理函数注册
    backtest_engine.register(EventType.Market, my_broker.market_handlers)
    backtest_engine.register(EventType.Signal, my_broker.signal_handlers)
    backtest_engine.register(EventType.Order, my_broker.order_handlers)
    backtest_engine.register(EventType.Fill, my_broker.fill_handlers)

    # 喂数据
    backtest_engine.feed(data=df)

    # 开启引擎
    backtest_engine.start()
