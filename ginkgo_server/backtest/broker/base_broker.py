"""
经纪人类
"""
from ginkgo_server.backtest.enums import MarketType
from ginkgo_server.backtest.events import *
from ginkgo_server.backtest.strategy.base_strategy import BaseStrategy
from ginkgo_server.backtest.sizer.base_sizer import BaseSizer
from ginkgo_server.backtest.matcher.base_matcher import BaseMatcher
from ginkgo_server.backtest.analyzer.base_analyzer import BaseAnalyzer
from ginkgo_server.backtest.risk.base_risk import BaseRisk
from ginkgo_server.backtest.event_engine import EventEngine
import abc


class BaseBroker(metaclass=abc.ABCMeta):
    """
    经纪人基类
    """

    def __init__(
        self,
        name: str,
        engine: EventEngine,
        *,
        init_capital: int = 100000,
    ):
        self.name = name
        self._engine = engine
        self._init_capital = init_capital  # 设置初始资金
        self._capital = 0
        self.get_cash(init_capital)  # 入金
        self._freeze = 0
        self._strategies = []  # 策略池
        self._sizer = None
        self._matcher = None
        self._analyzer = None
        self.fee = 0  # 用来统计所有税费
        self.position = {}  # 存放Position对象
        # self.trade_history = []
        # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    def strategy_register(self, strategy: BaseStrategy):
        """
        策略注册

        :param strategy: 根据MarketEvent做出信号判断的策略
        :type strategy: BaseStrategy
        """
        if strategy not in self._strategies:
            self._strategies.append(strategy)
            strategy.engine_register(self._engine)
            print(f"{strategy.name} 已注册")  # TODO 用Log替换，同时本地存储
        else:
            print(f"{strategy.name} 已存在")

    def sizer_register(self, sizer: BaseSizer):
        """
        仓位控制策略注册

        :param sizer: 负责仓位控制的函数
        :type sizer: BaseSizer
        """
        self._sizer = sizer
        self._sizer.engine_register(self._engine)
        self._sizer.set_init_capital(self._init_capital)

    def risk_register(self, risk: BaseRisk):
        """
        风控策略注册

        :param risk: 负责资金池的风险控制
        :type risk: BaseRisk
        """
        if risk not in self._risk:
            risk.engine_register(self._engine)
            self._risk.append(risk)
            print(f"{risk.name} 已注册")  # TODO 用Log替换，同时本地存储
        else:
            print(f"{risk.name} 已存在")

    def matcher_register(self, matcher: BaseMatcher):
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self._matcher = matcher
        self._matcher.engine_register(self._engine)

    def analyzer_register(self, analyzer: BaseAnalyzer):
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self._analyzer = analyzer
        self._analyzer.engine_register(self._engine)

    def market_handlers(self, event: MarketEvent):
        """
        市场事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement market_handlers()")

    def signal_handlers(self, event: SignalEvent):
        """
        信号事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement signal_handlers()")

    def order_handlers(self, event: OrderEvent):
        """
        订单事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement order_handlers()")

    def fill_handlers(self, event: FillEvent):
        """
        成交事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement fill_handlers()")

    def general_handler(self):
        """
        通用事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement general_handler()")

    def get_cash(self, cash: float):
        """
        入金操作
        """
        # 入金金额只接受大于0的金额
        if cash > 0:
            self._capital += cash
        else:
            print("Cash should above 0.")
