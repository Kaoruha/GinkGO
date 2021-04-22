from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer
from ginkgo_server.util.ATR import CAL_ATR

r = RiskAVGSizer(risk_factor=10000)
print(r._risk_factor)
print(r._init_capital)
print(r)

m = r.cal(10000, "sh.000091", "2020-01-22")
print(m)