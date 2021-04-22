from ginkgo_server.backtest.sizer.base_sizer import BaseSizer
from ginkgo_server.util.ATR import CAL_ATR
from ginkgo_server.backtest.events import *


class RiskAVGSizer(BaseSizer):
    def __init__(self, risk_factor=20):
        super(RiskAVGSizer, self).__init__()
        self._risk_factor = risk_factor  # 风险因子

    def __repr__(self):
        print(super(RiskAVGSizer, self).__repr__())
        return f"根据标的波动幅度调整仓位，当前风险因子为 {self._risk_factor}，标的单日波动对资金最大影响为 {self._risk_factor/100} %"

    def buy_cal(self, total_capitial, code, date):
        # 根据日期获取目标标的近期的波动情况
        atr = CAL_ATR(code, date, period=5)
        # 根据波动幅度计算目标仓位总资金
        money = total_capitial * (self._risk_factor / 100 / 100)
        # 返回购入份额数
        return money / atr

    def sell_cal(self):
        pass

    def get_signal(self, event: SignalEvent, broker: BaseBroker):
        if event.deal == DealType.BUY:
            tar = self.buy_cal(broker._total_capitial, code=event.code, date=event.date)
            print(tar)