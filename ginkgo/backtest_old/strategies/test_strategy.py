"""
测试策略策略
"""
from ginkgo.backtest_old.strategies.base_strategy import BaseStrategy
from ginkgo.backtest_old.events import SignalEvent
from pandas import DataFrame


class TestStrategy(BaseStrategy):

    def check(self):
        for code in self.data['daily']:
            latest_close = self.data['daily'][code].iloc[-1]['close']
            if latest_close > self.data['daily'][code].iloc[-2]['close']:
                signal = SignalEvent(date=self.data['daily'][code].iloc[-1]['date'],
                                     code=code, buy_or_sell='BUY'
                                     )
                return signal
            print(f'latest_close: {latest_close}')
            print('=========================')
