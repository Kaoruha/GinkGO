"""
移动均线策略
"""
from ginkgo.backtest.strategies.base_strategy import BaseStrategy
from ginkgo.backtest.events import SignalEvent



class MACD(BaseStrategy):
    def __init__(self, SHORT=5, LONG=10):
        self.short = SHORT
        self.long = LONG
    def check(self, data):
        # 传入数据
        self.data = data
        for code in self.data:
            close = self.data[code].iloc[-1]['close']
            ma = self.data[code].iloc[-2]['MA'+str(self.short)]
