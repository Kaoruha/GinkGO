from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo_server.backtest.events import SignalEvent, DealType
from ginkgo_server.backtest.broker.T_1_broker import T1Broker
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.postion import Position

r = RiskAVGSizer(base_factor=1000)

engine = EventEngine()
broker = T1Broker(engine=engine)
broker.sizer_register(sizer=r)
broker.get_cash(2000)

p1 = Position(code="sh.000901", price=2.11, volume=100)
p2 = Position(code="sh.000902", price=3.11, volume=200)
p3 = Position(code="sh.000902", price=3.15, volume=20000)
broker.add_position(p1)
broker.add_position(p2)
broker.add_position(p3)


signal1 = SignalEvent(
    date="2020-04-22", code="sh.000905", deal=DealType.BUY, source="测试信息"
)
o1 = r.get_signal(signal=signal1, broker=broker)

p4 = Position(code="sh.000905", price=20.1, volume=10)
broker.add_position(p4)

signal2 = SignalEvent(
    date="2020-04-23", code="sh.000905", deal=DealType.BUY, source="测试信息"
)
o2 = r.get_signal(signal=signal2, broker=broker)

signal3 = SignalEvent(
    date="2020-04-25", code="sh.000905", deal=DealType.SELL, source="测试信息"
)
o3 = r.get_signal(signal3, broker=broker)


signal4 = SignalEvent(
    date="2020-04-25", code="sh.000901", deal=DealType.SELL, source="测试信息"
)
o4 = r.get_signal(signal4, broker=broker)
