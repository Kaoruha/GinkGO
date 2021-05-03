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
from ginkgo_server.backtest.price import DayBar

r = RiskAVGSizer(base_factor=50)

# engine = EventEngine()
# broker = T1Broker(engine=engine)
# engine.register(EventType.Market, broker.market_handler)
# engine.register(EventType.Signal, broker.signal_handler)
# engine.register(EventType.Order, broker.order_handler)
# engine.register(EventType.Fill, broker.fill_handler)
# tf_strategy = TestStrategy()
# broker.strategy_register(tf_strategy)
# broker.sizer_register(sizer=r)
# broker.get_cash(2000)
# matcher = SimulateMatcher()
# broker.matcher_register(matcher=matcher)


# pdata = gm.get_dayBar_by_mongo(code="sz.000725")
# engine.feed(pdata)
# engine.start()
count = 0
for i in range(5):
    count += i
print(count)
