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
from src.backtest.enums import Direction
import random


class TestStrategy(BaseStrategy):
    def __init__(self, name: str = "测试用策略"):
        super(TestStrategy, self).__init__(name=name)

    def try_gen_enter_signal(self):
        """进入策略"""
        print(self.daybar)
        code = self.daybar.loc[0].code
        date = self.daybar.iloc[-1].date
        r = random.random()
        if r > 0.8:
            signal = SignalEvent(
                code=code, date=date, deal=Direction.BUY, source="测试随便产生的信号，10%概率买入"
            )
            return signal

    def try_gen_exit_signal(self):
        """退出策略"""
        code = self.daybar.loc[0].code
        date = self.daybar.iloc[-1].date
        r = random.random()
        if r > 0.9:
            signal = SignalEvent(
                date=date, code=code, deal=Direction.SELL, source="测试随便产生的信号，10%概率卖出"
            )
            return signal
