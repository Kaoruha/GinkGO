"""
策略类

好的策略应该：
1、相当搞的预期年化收益率
2、相对于起预期年化收益率比较合理的最大会策划
3、全球股票市场的低相关度（相关度最好是一个很小很小的负值）


投资组合的分散化程度：实现高度的分散化是取得较好的长期投资结果的最关键的一个因素，改变投资的品种以及调整在不同板块上配置的权重都会对投资业绩产生巨大的影响
持仓限额：我们需要找到有效的方法，根据每个品种的波动性正确的酸楚相应的持仓限额。
投资的期限：我们需要首先考虑到底要追踪多长期限的趋势，比如到底是一两周的趋势，还是5～8周的趋势。选择不同时间跨度的趋势kennel会导致投资结果出现巨大的差异
风险水平：需要子啊风险和收益之间选择一个平衡点
单一策略还是多策略：虽然这两种方式下的长期收益会非常接近，但讲同一种策略应用到不同但投资期间上或者同时使用多个想死但趋势跟踪策略，将有煮鱼平滑短期上但业绩波动
"""
import pandas as pd
import abc
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.postion import Position
from ginkgo_server.backtest.events import InfoType


class BaseStrategy(metaclass=abc.ABCMeta):
    """
    基础策略类
    回头改成抽象类
    """

    def __init__(self, name="策略基类"):
        self.name = name
        self.day_columns = [
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "amount",
            "adjust_flag",
            "turn",
            "pct_chg",
            "is_st",
        ]
        self.daybar = pd.DataFrame(columns=self.day_columns)
        self.minbar = None

    def __repr__(self):
        s = self.name
        return s

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def try_gen_enter_signal(self):
        """进入策略"""
        raise NotImplementedError("Must implement enter_market()")

    def try_gen_exit_signal(self):
        """退出策略"""
        raise NotImplementedError("Must implement exit_market()")

    def try_gen_signals(self):
        r = []
        signal_enter = self.try_gen_enter_signal()
        signal_exit = self.try_gen_exit_signal()
        if signal_enter:
            r.append(signal_enter)
        if signal_exit:
            r.append(signal_exit)
        return r

    def get_price(self, event):
        if event.info_type == InfoType.DailyPrice:
            try:
                day_bar = event.data
                self.daybar = self.daybar.append(day_bar.data, ignore_index=True)
                # 去重
                self.daybar = self.daybar.drop_duplicates()
                # 排序
                self.daybar = self.daybar.sort_values(by="date", ascending=True, axis=0)
                # 计算MA值
                # self.data[self.__get_column_title(self.short_term)] = (
                #     self.data["close"].rolling(self.short_term, min_periods=1).mean()
                # )
                # self.data[self.__get_column_title(self.long_term)] = (
                #     self.data["close"].rolling(self.long_term, min_periods=1).mean()
                # )
            except Exception as e:
                print(e)
                print("数据接收异常，请检查代码")
            # print(self.daybar)
        r = self.try_gen_signals()
        return r
