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
from ginkgo_server.backtest.strategy.trend_follow import TrendFollow

r = RiskAVGSizer(base_factor=500)

engine = EventEngine()
broker = T1Broker(engine=engine)
tf_strategy = TrendFollow()
broker.strategy_register(tf_strategy)
broker.sizer_register(sizer=r)
broker.get_cash(2000)
matcher = SimulateMatcher()
broker.matcher_register(matcher=matcher)

# 设定初始持仓
p1 = Position(code="sh.000901", price=2.11, volume=100)
p2 = Position(code="sh.000902", price=3.11, volume=200)
p3 = Position(code="sz.000725", price=3.15, volume=200)
broker.add_position(p1)
broker.add_position(p2)
broker.add_position(p3)

price_info = gm.get_dayBar_by_mongo(
    code="sz.000725", start_date="2020-04-23", end_date="2020-04-23"
)
# price1 = gm.get_min5_by_mongo(
#     code="sz.000725", start_date="2020-04-23", end_date="2020-04-23"
# ).loc[0]

# pe = MarketEvent(
#     date=price1.date,
#     time=price1.time,
#     code="sz.000725",
#     source="测试数据",
#     info_type=InfoType.MinutePrice,
#     data=price1,
# )
pe = MarketEvent(
    date="2020-01-01",
    time="202001011212",
    code="sz.000725",
    source="测试数据",
    info_type=InfoType.DailyPrice,
    data=price_info,
)
broker.market_handler(pe)
# print(broker.current_price)
# print(broker.date)
# print(broker.time)
# print("=" * 20)
# pe2 = MarketEvent(
#     date="2020-01-00",
#     time="202001011212",
#     code="sz.000726",
#     source="测试数据",
#     info_type=InfoType.MinutePrice,
#     data="test2",
# )
# broker.market_handler(pe2)
# print(broker.current_price)
# print(broker.date)
# print(broker.time)
# price_info2 = gm.get_dayBar_by_mongo(
#     code="sz.000725", start_date="2020-04-24", end_date="2020-04-24"
# )
# dp_event2 = MarketEvent(
#     date="2020-04-22",
#     code="sz.000725",
#     source="测试数据",
#     info_type=InfoType.DailyPrice,
#     data=price_info,
# )
# broker.market_handler(dp_event2)

# price3 = gm.get_min5_by_mongo(
#     code="sz.000725", start_date="2020-04-24", end_date="2020-04-24"
# )
# print(price3)


# signal1 = SignalEvent(
#     date="2020-04-22", code="sz.000725", deal=DealType.SELL, source="测试信息"
# )
# o1 = broker.signal_handler(signal=signal1)
# if o1 is not None:
#     o_n = matcher.try_match(o1, broker, price_info)
#     print("发出订单，尝试成交后")
#     fill = matcher.get_result(price_info)
#     for i in fill:
#         if i.type_ == EventType.Order:
#             print("处理订单事件")

#         if i.type_ == EventType.Fill:
#             print("处理成交事件")
#             broker.fill_handler(i)