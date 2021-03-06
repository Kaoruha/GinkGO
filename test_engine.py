import datetime
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.broker.T_1_broker import T1Broker
from ginkgo.backtest.enums import EventType
from ginkgo.data.stock.baostock_data import bao_instance
from ginkgo.backtest.strategy.moving_average import MovingAverageStrategy
from ginkgo.backtest.strategy.target_profit import TargetProfit
from ginkgo.backtest.strategy.stop_loss import StopLoss
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo.backtest.sizer.all_in_one import AllInOne
from ginkgo.backtest.analyzer.normal_analyzer import NormalAnalyzer


if __name__ == "__main__":
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    df = gm.query_stock(
        code="sh.600006",
        start_date="2001-01-01",
        end_date=today,
        frequency="d",
        adjust_flag=3,
    )

    # 引擎初始化
    backtest_engine = EventEngine()
    backtest_engine.set_heartbeat(0.001)

    # 经纪人初始化
    my_broker = T1Broker(name="my_broker", engine=backtest_engine)

    # 策略挂载
    ma_strategy = MovingAverageStrategy(short_term=15, long_term=60)
    target_profit = TargetProfit(target=30, target_reduce=80)
    stop_loss = StopLoss(loss=5, target_reduce=80)
    my_broker.strategy_register(ma_strategy)
    my_broker.strategy_register(target_profit)
    my_broker.strategy_register(stop_loss)
    my_broker.sizer_register(sizer=AllInOne())

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
