"""
止盈止损
"""
from src.backtest.strategy.base_strategy import BaseStrategy
from src.backtest.events import SignalEvent
from src.backtest.enums import Direction


class ProfitLossLimit(BaseStrategy):
    def __init__(self, name="止盈止损策略", limit=(10, 5)):
        self.profit_limit = limit[0]
        self.loss_limit = limit[1]
        name = f"{name}P{self.profit_limit}L{self.loss_limit}"
        super(ProfitLossLimit, self).__init__(name=name)

    def try_gen_long_signal(self):
        """进入策略"""
        return

    def try_gen_short_signal(self):
        """退出策略"""
        code = self.daybar.loc[0].code
        date = self.daybar.iloc[-1].date
        if code not in self.broker.position.keys():
            return
        base_price = self.broker.position[code].price
        profit_limit_price = base_price * (1 + self.profit_limit / 100)
        loss_limit_price = base_price * (1 - self.loss_limit / 100)
        today = self.daybar.iloc[-1]
        if (
            float(today["close"]) > loss_limit_price
            and float(today["close"]) < profit_limit_price
        ):
            return
        signal = SignalEvent(
            code=code, date=date, deal=Direction.SELL, source=f"{date} {self.name}"
        )
        return signal

    def pre_treate(self):
        """预处理函数"""
        pass
