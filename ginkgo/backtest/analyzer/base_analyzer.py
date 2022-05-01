"""
Author: Kaoru
Date: 2022-03-07 16:50:41
LastEditTime: 2022-04-03 00:36:06
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/analyzer/base_analyzer.py
What goes around comes around.
"""
"""
分析评价基类

净值曲线 equity curve
业绩基准 benchmark
夏普比率 过去一段时间段平均年华收益率减去所谓的无风险收益率，再将结果除以该器件收益率的标准差
索提诺比率 与夏普比率类似，但是只计量负向的波动
最大亏损弥补时间 将历史最大回撤除以年化收益率
头寸平均持仓时间
盈利头寸平均持仓时间/亏损头寸平均持仓时间
总交易笔数
盈利交易笔数/亏损交易笔数

"""
import abc


class BaseAnalyzer(abc.ABC):
    def __init__(self, name="基础分析类"):
        self.name = name

    @abc.abstractmethod
    def record(self, *args, **kwargs):
        raise NotImplementedError("Must implement report()")

    @abc.abstractmethod
    def report(self, *args, **kwargs):
        raise NotImplementedError("Must implement report()")
