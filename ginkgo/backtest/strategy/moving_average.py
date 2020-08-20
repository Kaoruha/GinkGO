from .base_strategy import BaseStrategy
import pandas as pd
from ginkgo.backtest.event import SignalEvent


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
        self.data = self.data.append(data, ignore_index=True)
        self.data = self.data.drop_duplicates()
        self.data = self.data.sort_values(by='date', ascending=True, axis=0)
        self.data[self.__get_column_title(self.short)] = self.data['close'].rolling(self.short, min_periods=1).mean()
        self.data[self.__get_column_title(self.long)] = self.data['close'].rolling(self.long, min_periods=1).mean()
        print(self.data)

    def enter_market(self):
        signal = SignalEvent(date=self.data[-1]['date'],code=self.data[0]['code'],buy_or_sell='BUY')
        condition = True
        if condition:
            return signal
        else:
            return None

    def exiting_market(self):
        signal = SignalEvent(date=self.data[-1]['date'], code=self.data[0]['code'], buy_or_sell='SELL')
        condition = True
        if condition:
            return signal
        else:
            return None
