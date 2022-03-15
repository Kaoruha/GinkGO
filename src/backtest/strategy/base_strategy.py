import pandas as pd
import abc
from src.backtest.event_engine import EventEngine
from src.backtest.postion import Position
from src.backtest.events import InfoType


class BaseStrategy(metaclass=abc.ABCMeta):
    """
    基础策略类
    回头改成抽象类
    """

    def __init__(self, name="策略基类"):
        self._name = name
        self._day_columns = [
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
        self._daybar = pd.DataFrame(columns=self._day_columns)
        self._minbar = None
        self._broker = None
        self._engine = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def broker(self):
        return self._broker

    @broker.setter
    def broker(self, value):
        self._broker = value

    def __repr__(self):
        s = self.name
        return s

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def broker_register(self, broker):
        # 注册经纪人
        self._broker = broker

    def try_gen_enter_signal(self):
        """进入策略"""
        raise NotImplementedError("Must implement enter_market()")

    def try_gen_exit_signal(self):
        """退出策略"""
        raise NotImplementedError("Must implement exit_market()")

    def pre_treate(self):
        """预处理函数"""
        raise NotImplementedError("Must implement pre_treate()")

    def try_gen_signals(self):
        self.pre_treate()
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
                self._daybar = self.daybar.append(day_bar.data, ignore_index=True)
                # 去重
                self._daybar = self.daybar.drop_duplicates()
                # 排序
                self._daybar = self.daybar.sort_values(by="date", ascending=True, axis=0)
            except Exception as e:
                print(e)
                print("数据接收异常，请检查代码")
        r = self.try_gen_signals()
        return r
