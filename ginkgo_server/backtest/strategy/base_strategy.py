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
        r = self.try_gen_signals()
        return r
