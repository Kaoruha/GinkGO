from ginkgo_server.backtest.sizer.base_sizer import BaseSizer


class RiskAVGSizer(BaseSizer):
    def __init__(self, risk_factor=20):
        super(RiskAVGSizer, self).__init__()
        self._risk_factor = risk_factor  # 风险因子

    def __repr__(self):
        return f"根据标的波动幅度调整仓位，当前风险因子为 {self._risk_factor}"
