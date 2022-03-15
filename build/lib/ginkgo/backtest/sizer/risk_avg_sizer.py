from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.util.ATR import CAL_ATR
from ginkgo.backtest.events import OrderEvent, DealType


class RiskAVGSizer(BaseSizer):
    """
    平均真实风险仓位控制
    """

    def __init__(self, base_factor=20):
        name = f"平均波动开仓策略，基准风险因子{base_factor}"
        super(RiskAVGSizer, self).__init__(name=name)
        self._base_risk_factor = base_factor  # 风险因子
        self._risk_factor = {}

    def __repr__(self):
        print(super(RiskAVGSizer, self).__repr__())
        return f"根据标的波动幅度调整仓位，当前风险因子为 {self._risk_factor}，标的单日波动对资金最大影响为 {self._risk_factor/100} %"

    def add_risk_factor(self, code, risk_factor):
        self._risk_factor[code] = risk_factor
        # print(f"当前风险因子：{self._risk_factor}")

    def get_risk_factor(self, code):
        if code in self._risk_factor.keys():
            return self._risk_factor[code]
        else:
            return self._base_risk_factor

    def buy_cal(self, total, code, date):
        # 根据日期获取目标标的近期的波动情况
        atr = CAL_ATR(code, date, period=5)
        # 根据波动幅度计算目标仓位总资金
        money = total * (self.get_risk_factor(code=code) / 100 / 100)
        # 返回购入份额数
        if atr == 0:
            return 100
        else:
            volume = money / atr
            if volume < 100:
                volume = 100
            return volume

    def sell_cal(self, code, position):
        # 目前采用简单策略，卖出份额为持仓的全部
        volume = position[code].volume
        return volume

    def get_signal(self, signal, broker):
        # 需要根据经纪人持仓进行判断

        code = signal.code
        date = signal.date
        hold_position = broker.position
        total = broker.init_capital
        # TODO 现在所有标的都按照基准风险因子BaseRiskFactor设定风险因子，回头会根据持仓情况和信号情况动态调整风险因子
        self.add_risk_factor(code=code, risk_factor=self._base_risk_factor)
        # 经纪人未持有信号相关头寸
        if code not in hold_position.keys():
            # 买入信号，则返回头寸订单
            if signal.deal == DealType.BUY:
                volume = self.buy_cal(total=total, code=code, date=date)
                order = OrderEvent(
                    date=signal.date,
                    deal=DealType.BUY,
                    code=signal.code,
                    volume=volume,
                    source=self._name,
                )
                return order
            # 卖出信号，则无视
            print(f"{date} 「{broker._name}」未持有该股票，卖出信号没有意义，请检查代码")
        else:
            # 经纪人持有信号相关头寸:
            # 买入信号，则计算目前持仓距离目标仓位空间，返回剩余空间的头寸订单事件
            if signal.deal == DealType.BUY:
                target_volume = self.buy_cal(total=total, code=code, date=date)
                current_volume = broker.position[code].volume
                print(f"{date} {code} 当前持仓：{current_volume} 目标持仓：{target_volume}")
                gap = target_volume - current_volume
                if gap >= 100:
                    order = OrderEvent(
                        date=date,
                        code=code,
                        deal=DealType.BUY,
                        volume=gap,
                        source=self._name,
                    )
                    return order
                else:
                    print(f"{date} 补仓交易量小于最小成交量，不进行补仓操作")
                # TODO 反复出现买入信号可以考虑调大该标的的风险因子

            # 卖出信号，则根据目前持仓,计算卖出量，返回头寸订单事件
            elif signal.deal == DealType.SELL:
                order = OrderEvent(
                    date=date,
                    code=code,
                    deal=DealType.SELL,
                    volume=self.sell_cal(code=code, position=hold_position),
                    source=self._name,
                )
                return order
                # TODO 反复出现卖出信号可以考虑减小该标的的风险因子
