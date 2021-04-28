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
from ginkgo_server.backtest.price import DayBar

r = RiskAVGSizer(base_factor=50)

engine = EventEngine()
broker = T1Broker(engine=engine)
engine.register(EventType.Market, broker.market_handler)
engine.register(EventType.Signal, broker.signal_handler)
engine.register(EventType.Order, broker.order_handler)
engine.register(EventType.Fill, broker.fill_handler)
tf_strategy = TrendFollow()
broker.strategy_register(tf_strategy)
broker.sizer_register(sizer=r)
broker.get_cash(2000)
matcher = SimulateMatcher()
broker.matcher_register(matcher=matcher)

# 设定初始持仓
# p1 = Position(code="sh.000901", price=2.11, volume=100)
# p2 = Position(code="sh.000902", price=3.11, volume=200)
# p3 = Position(code="sz.000725", price=3.15, volume=200)
# broker.add_position(p1)
# broker.add_position(p2)
# broker.add_position(p3)

pdata = gm.get_dayBar_by_mongo(
    code="sz.000725", start_date="2020-04-23", end_date="2020-04-30"
)

print(pdata)

p1 = DayBar(
    date=pdata.loc[0].date,
    code=pdata.loc[0].code,
    open_=pdata.loc[0].open,
    high=pdata.loc[0].high,
    low=pdata.loc[0].low,
    close=pdata.loc[0].close,
    pre_close=pdata.loc[0].pre_close,
    volume=pdata.loc[0].volume,
    amount=pdata.loc[0].amount,
    adjust_flag=pdata.loc[0].adjust_flag,
    turn=pdata.loc[0].turn,
    pct_change=pdata.loc[0]["pct_change"],
    is_st=pdata.loc[0].is_st,
)


pe1 = MarketEvent(
    date=p1.data.date,
    code=p1.data.code,
    source="测试数据",
    info_type=InfoType.DailyPrice,
    data=p1,
)
broker.market_handler(pe1)

p2 = DayBar(
    date=pdata.loc[1].date,
    code=pdata.loc[1].code,
    open_=pdata.loc[1].open,
    high=pdata.loc[1].high,
    low=pdata.loc[1].low,
    close=pdata.loc[1].close,
    pre_close=pdata.loc[1].pre_close,
    volume=pdata.loc[1].volume,
    amount=pdata.loc[1].amount,
    adjust_flag=pdata.loc[1].adjust_flag,
    turn=pdata.loc[1].turn,
    pct_change=10.2,
    is_st=pdata.loc[1].is_st,
)
pe2 = MarketEvent(
    date=p2.data.date,
    code=p2.data.code,
    source="测试数据",
    info_type=InfoType.DailyPrice,
    data=p2,
)
broker.market_handler(pe2)

s1 = SignalEvent(date="2020-04-23", code="sz.000725", deal=DealType.BUY, source="测试用信号")
o1 = broker.signal_handler(s1)
f1 = broker.order_handler(o1)
print(broker)
broker.fill_handler(f1)
print(broker)