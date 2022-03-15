"""
《趋势交易》中的趋势追踪策略

只有在50天均线高于100天均线的时候才开多仓
只有在50天均线低于100天均线的时候才开空仓
如果某一天收盘价是过去50天最高的收盘价，我们就在下一个交易日买入
如果某一天收盘价是过去50天最低的收盘价，我们就在下一个交易日卖出或卖空
单个品种的仓位额度与其波动性有关，格局真是波动幅度均值（ART）来确定，风险因子可以暂时设定为20个基点
多头仓位的止损价格设定为开仓以来最高收盘价之下3个ART的位置
空头仓位的止损价格设定为开仓以来最低收盘价之上3个ART的位置
投资的品种吃应该涵盖尽可能多的板块，从每个板块中选取的品种数量不少于10个（需要在Selector中实现）
"""

from src.backtest.strategy.base_strategy import BaseStrategy
from src.backtest.events import SignalEvent
from src.backtest.enums import DealType
from src.util.ATR import CAL_ATR
import random


class TrendFollow(BaseStrategy):
    def __init__(
        self,
        name: str = "趋势跟踪策略",
        short_term: int = 50,
        long_term: int = 100,
        gap_count: int = 3,
    ):
        name = name + f"S{short_term}L{long_term}"
        super(TrendFollow, self).__init__(name=name)
        self.short_term = short_term  # 短周期长度
        self.long_term = long_term  # 长周期长度
        self.gap_count = gap_count  # 缺口大小，负责判断合适卖空

    def __get_column_title(self, term):
        s = "MA" + str(term)
        return s

    def pre_treate(self):
        code = self.daybar.loc[0].code
        date = self.daybar.iloc[-1].date

        short_title = self.__get_column_title(self.short_term)
        long_title = self.__get_column_title(self.long_term)
        # 计算MA值
        self.daybar[short_title] = (
            self.daybar["close"].rolling(self.short_term, min_periods=1).mean()
        )
        self.daybar[long_title] = (
            self.daybar["close"].rolling(self.long_term, min_periods=1).mean()
        )

    def try_gen_enter_signal(self):
        """进入策略"""
        if self.daybar.shape[0] < 3:
            return
        short_title = self.__get_column_title(self.short_term)
        long_title = self.__get_column_title(self.long_term)
        code = self.daybar.loc[0].code
        date = self.daybar.iloc[-1].date
        yesterday = self.daybar.iloc[-2]
        today = self.daybar.iloc[-1]
        if (
            yesterday[short_title] < yesterday[long_title]
            and today[short_title] > today[long_title]
        ):
            signal = SignalEvent(
                code=code, date=date, deal=DealType.BUY, source=f"{date} {self.name}"
            )
            return signal

    def try_gen_exit_signal(self):
        """退出策略"""
        if len(self.broker.position) == 0:
            return
        p = None
        code = self.daybar.loc[0].code
        for i in self.broker.position.keys():
            if i == code:
                p = self.broker.position[i]

        if p is None:
            return

        open_date = p.date
        hold_high = (
            self.daybar[self.daybar["date"] >= open_date]["close"].astype(float).max()
        )
        today = self.daybar.iloc[-1]
        date = today.date
        gap = CAL_ATR(code, open_date, period=int(self.short_term / 5))
        sell_point = hold_high - gap * self.gap_count
        if float(today.close) <= sell_point:
            signal = SignalEvent(
                date=date, code=code, deal=DealType.SELL, source=f"{date} {self.name}"
            )
            return signal
