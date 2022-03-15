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
from src.backtest.event_engine import EventEngine


class BaseAnalyzer(object):
    def __init__(self):
        self._init_date = ""
        self._current_date = ""
        self._target = "sh."
        self._engine = None
        self._init_capital = 0
        self._capital = 0
        self._position = {}
        self._profit = 0
        self._freeze = 0
        self._current_price = 0
        self._stock_value = 0
        self._max_profit = 0
        self._max_drawdown = 0

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例

        :param engine: [description]
        :type engine: EventEngine
        """
        self._engine = engine

    def report(self, *args, **kwargs):
        """
        报告方法

        :raises NotImplementedError: 必须在子类中重载
        """
        raise NotImplementedError("Must implement report()")

    def give_a_mark(self, *args, **kwargs):
        """
        报告方法

        :raises NotImplementedError: 必须在子类中重载
        """
        raise NotImplementedError("Must implement give_a_mark()")
