"""
分析评价基类
"""
from ginkgo_server.backtest.event_engine import EventEngine

class BaseAnalyzer(object):
    def __init__(self):
        self._init_date=''
        self._current_date=''
        self._target = 'sh.'
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
