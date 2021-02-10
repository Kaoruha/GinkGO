from .base_strategy import BaseStrategy
import pandas as pd
from ginkgo_server.backtest.events import SignalEvent
from ginkgo_server.backtest.enums import DealType


class MovingAverageStrategy(BaseStrategy):
    def __init__(self, short_term: int = 5, long_term: int = 20):
        self.columns = [
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "adjust_flag",
            "turn",
            "trade_status",
            "pct_change",
            "is_st",
        ]
        self.data = pd.DataFrame(columns=self.columns)
        self.short_term = short_term
        self.long_term = long_term
        self.name = f"双均线S{self.short_term}L{self.long_term}"
        self._signal_count = 0

    def __get_column_title(self, span: int):
        """
        获取DataFrame列名，用来写入移动平均线数值

        :param span: 周期
        :type span: int
        :return: 返回对应周期的列名
        :rtype: str
        """
        column_title = "MA_" + str(span)
        return column_title

    def data_transfer(self, data: pd.DataFrame, position):
        """
        数据传输

        :param data: 这里传过来的数据应该是日交易数据
        :type data: pd.DataFrame
        :param position: 经纪人的持仓情况
        :type position: [type]
        """
        # 数据处理
        self.data = self.data.append(data, ignore_index=True)
        # 去重
        self.data = self.data.drop_duplicates()
        # 排序
        self.data = self.data.sort_values(by="date", ascending=True, axis=0)
        # 计算MA值
        self.data[self.__get_column_title(self.short_term)] = (
            self.data["close"].rolling(self.short_term, min_periods=1).mean()
        )
        self.data[self.__get_column_title(self.long_term)] = (
            self.data["close"].rolling(self.long_term, min_periods=1).mean()
        )
        # 尝试产生信号
        self.try_gen_signals()

    def try_gen_enter_signal(self):
        """
        尝试产生买入信号
        """
        date = self.data.iloc[-1]["date"]  # 获取今日日期
        code = self.data.iloc[0]["code"]  # 获取股票代码

        try:
            yesterday_short = self.data.iloc[-2][
                self.__get_column_title(self.short_term)
            ]  # 昨日短期均值
            yesterday_long = self.data.iloc[-2][
                self.__get_column_title(self.long_term)
            ]  # 昨日长期将均值
            today_short = self.data.iloc[-1][
                self.__get_column_title(self.short_term)
            ]  # 今日短期均值
            today_long = self.data.iloc[-1][
                self.__get_column_title(self.long_term)
            ]  # 今日长期均值

            condition1 = yesterday_short < yesterday_long
            condition2 = today_short > today_long
        except Exception as e:
            # 虽然想不出哪里会报错，先这么处理
            condition1 = False
            condition2 = False

        # 当条件1与条件2同时成立时，意味着短期均线上穿上期均线，发出买入信号
        if condition1 and condition2:
            signal = SignalEvent(
                date=date,
                code=code,
                source=self.name,
                current_price=self.data.iloc[-1]["close"],
                deal=DealType.BUY,
            )
            # print('产生买入信号')

            self._engine.put(signal)
            self._signal_count += 1

    def try_gen_exit_signal(self):
        """
        尝试产生卖出信号
        """
        date = self.data.iloc[-1]["date"]
        code = self.data.iloc[0]["code"]

        try:
            yesterday_short = self.data.iloc[-2][
                self.__get_column_title(self.short_term)
            ]  # 昨日短期均值
            yesterday_long = self.data.iloc[-2][
                self.__get_column_title(self.long_term)
            ]  # 昨日长期均值
            today_short = self.data.iloc[-1][
                self.__get_column_title(self.short_term)
            ]  # 今日短期均值
            today_long = self.data.iloc[-1][
                self.__get_column_title(self.long_term)
            ]  # 今日长期均值

            condition1 = yesterday_short > yesterday_long
            condition2 = today_short < today_long
        except Exception as e:
            condition1 = False
            condition2 = False

        # 当条件1与条件2同时成立时，意味着短期均线下穿长期均线，发出卖出信号
        if condition1 and condition2:
            signal = SignalEvent(
                date=date,
                code=code,
                source=self.name,
                current_price=self.data.iloc[-1]["close"],
                deal=DealType.SELL,
            )
            # print('产生卖出信号')
            self._engine.put(signal)
            self._signal_count += 1
