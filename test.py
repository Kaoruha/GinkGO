from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo_server.backtest.events import SignalEvent, DealType
from ginkgo_server.backtest.broker.T_1_broker import T1Broker

r = RiskAVGSizer(risk_factor=10000)
print(r._risk_factor)
print(r._init_capital)
print(r)


broker = T1Broker()

se = SignalEvent(date="2020-04-22", code="sh.000905", deal=DealType.BUY)
r.get_signal(event=se, broker=broker)
