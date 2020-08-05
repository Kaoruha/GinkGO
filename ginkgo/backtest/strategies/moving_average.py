"""
移动均线策略
"""
from ginkgo.backtest.strategies.base_strategy import BaseStrategy
from ginkgo.backtest.events import SignalEvent
from pandas import DataFrame



class MACD(BaseStrategy):
    def __init__(self, SHORT=5, LONG=10):
        self.short = SHORT
        self.long = LONG

    def check(self):
        self.__calculate_average(self.short)
        self.__calculate_average(self.long)
        for code in self.data['daily']:
            close = self.data['daily'][code].iloc[-1]['close']
            ma = self.data['daily'][code].iloc[-2]['MA'+str(self.short)]
            print(close)
            print(ma)
            print('============')
    
    def __calculate_average(self, span: int):
        """
        负责计算并写入日均线数据

        :param span: 均线跨度，MA5则传入5，MA10则传入10
        :type span: int
        """
        if type(span) is not int:
            print('请输入日均线的跨度只能输入数字')
            return
        else:
            new_column = 'MA' + str(span)

        for code in self.data['daily']:
            self.data['daily'][code][new_column] = ''

        for code in self.data['daily']:
            stock = self.data['daily'][code]
            for i in range(stock.shape[0]):
                if i <= span:
                    total = stock['close'].iloc[0:i].sum()
                    days = 1
                    if i >= 1:
                        days = i
                    average = total / days
                    self.data['daily'][code].loc[i, new_column] = average
                else:
                    start = stock['close'].iloc[i - span]
                    end = stock['close'].iloc[i]
                    total = stock['close'].iloc[i - span:i].sum()
                    average = total / span
                    self.data['daily'][code].loc[i, new_column] = average
