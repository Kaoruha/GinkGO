from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo_server.backtest.events import (
    SignalEvent,
    DealType,
    EventType,
    MarketEvent,
    InfoType,
)
from ginkgo_server.backtest.broker.T_1_broker import T1Broker
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.postion import Position
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo_server.backtest.strategy.test_strategy import TestStrategy
from ginkgo_server.backtest.strategy.trend_follow import TrendFollow
from ginkgo_server.backtest.price import DayBar
from ginkgo_server.util.stock_filter import remove_index

r = RiskAVGSizer(base_factor=20)

engine = EventEngine()
broker = T1Broker(init_capitial=10000, engine=engine)
engine.register(EventType.Market, broker.market_handler)
engine.register(EventType.Signal, broker.signal_handler)
engine.register(EventType.Order, broker.order_handler)
engine.register(EventType.Fill, broker.fill_handler)
# tf_strategy = TestStrategy()
tf_strategy = TrendFollow(short_term=5, long_term=20, gap_count=3)
broker.strategy_register(tf_strategy)
broker.sizer_register(sizer=r)
matcher = SimulateMatcher()
broker.matcher_register(matcher=matcher)

code_list = remove_index()
code = code_list.sample(n=1).iloc[0].code

pdata1 = gm.get_dayBar_by_mongo(
    code="sz.300102", start_date="2020-01-01", end_date="2020-04-01"
)
engine.feed(pdata1)
engine.start()
