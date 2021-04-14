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


class BaseStrategy(metaclass=abc.ABCMeta):
    """
    基础策略类
    回头改成抽象类
    """

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def data_transfer(self, data: pd.DataFrame, position: Position):
        # 数据传递至策略
        raise NotImplementedError("Must implement data_transfer()")

    def try_gen_enter_signal(self):
        """进入策略"""
        raise NotImplementedError("Must implement enter_market()")

    def try_gen_exit_signal(self):
        """退出策略"""
        raise NotImplementedError("Must implement exit_market()")

    def try_gen_signals(self):
        self.try_gen_enter_signal()
        self.try_gen_exit_signal()
