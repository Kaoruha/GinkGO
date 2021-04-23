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


se = SignalEvent(date="2020-04-22", code="sh.000905", deal=DealType.BUY, source="测试信息")
o = r.get_signal(signal=se, broker=broker)
