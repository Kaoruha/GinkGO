from .base_strategy import BaseStrategy
import pandas as pd
from ginkgo.backtest.event import SignalEvent
from ginkgo.backtest.enums import DealType
import random


class MovingAverageStrategy(BaseStrategy):

    def __init__(self, *, short: int = 5, long: int = 20):
        self.columns = ['date', 'code', 'open', 'high', 'low', 'close', 'preclose', 'volume', 'adjustflag', 'turn',
                        'tradestatus', 'pctChg', 'isST']
        self.data: pd.DataFrame = pd.DataFrame(columns=self.columns)
        self.short = short
        self.long = long
        self.name = f'双均线策略SHORT{self.short}LONG{self.long}'

    def __get_column_title(self, span: int):
        # 获取DataFrame列名，用来写入移动平均线数值
        column_title = 'MA_' + str(span)
        return column_title

    def data_transfer(self, data: pd.DataFrame):
        # 数据处理
        self.data = self.data.append(data, ignore_index=True)
        # 去重 好像多余了
        self.data = self.data.drop_duplicates()
        # 排序 好像多余了
        self.data = self.data.sort_values(by='date', ascending=True, axis=0)
        # 计算MA值
        self.data[self.__get_column_title(self.short)] = self.data['close'].rolling(self.short, min_periods=1).mean()
        self.data[self.__get_column_title(self.long)] = self.data['close'].rolling(self.long, min_periods=1).mean()

        # 看看能不能产生信号
        self.enter_market()
        self.exit_market()

    def enter_market(self):
        date = self.data.iloc[-1]['date']
        code = self.data.iloc[0]['code']
        signal = SignalEvent(date=date,code=code,deal=DealType.BUY)
        condition = random.random()>.5
        if condition:
            self._engine.put(signal)
            print('产生买入信号')

    def exit_market(self):
        date = self.data.iloc[-1]['date']
        code = self.data.iloc[0]['code']
        signal = SignalEvent(date=date,code=code,deal=DealType.BUY)
        condition = random.random()>.5
        if condition:
            self._engine.put(signal)
            print('产生卖出信号')
