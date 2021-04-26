from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo_server.backtest.events import SignalEvent, DealType, EventType
from ginkgo_server.backtest.broker.T_1_broker import T1Broker
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.postion import Position
from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.matcher.simulate_matcher import SimulateMatcher

r = RiskAVGSizer(base_factor=500)

engine = EventEngine()
broker = T1Broker(engine=engine)
broker.sizer_register(sizer=r)
broker.get_cash(2000)
matcher = SimulateMatcher()
print(matcher)
broker.matcher_register(matcher=matcher)

p1 = Position(code="sh.000901", price=2.11, volume=100)
p2 = Position(code="sh.000902", price=3.11, volume=200)
p3 = Position(code="sz.000725", price=3.15, volume=200)
broker.add_position(p1)
broker.add_position(p2)
broker.add_position(p3)


signal1 = SignalEvent(
    date="2020-04-22", code="sz.000725", deal=DealType.SELL, source="测试信息"
)
o1 = broker.signal_handler(signal=signal1, broker=broker)
price_info = gm.get_dayBar_by_mongo(
    code="sz.000725", start_date="2020-04-23", end_date="2020-04-23"
)
print("接到信号后")
# print(broker)
if o1 is not None:
    o_n = matcher.try_match(o1, broker, price_info)
    print("发出订单，尝试成交后")
    # print(broker)
    fill = matcher.get_result(price_info)
    for i in fill:
        if i.type_ == EventType.Order:
            print("处理订单事件")

        if i.type_ == EventType.Fill:
            print("处理成交事件")
            broker.fill_handler(i)
print("成交后")
print(broker)


# p4 = Position(code="sh.000905", price=20.1, volume=10)
# broker.add_position(p4)

# signal2 = SignalEvent(
#     date="2020-04-23", code="sh.000905", deal=DealType.BUY, source="测试信息"
# )
# o2 = r.get_signal(signal=signal2, broker=broker)

# signal3 = SignalEvent(
#     date="2020-04-25", code="sh.000905", deal=DealType.SELL, source="测试信息"
# )
# o3 = r.get_signal(signal3, broker=broker)


# signal4 = SignalEvent(
#     date="2020-04-25", code="sh.000901", deal=DealType.SELL, source="测试信息"
# )
# o4 = r.get_signal(signal4, broker=broker)
