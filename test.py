from ginkgo_server.backtest.sizer.risk_avg_sizer import RiskAVGSizer


r = RiskAVGSizer()
print(r._risk_factor)
print(r._init_capital)
print(r)