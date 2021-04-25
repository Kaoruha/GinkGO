"""
经纪人类
"""
import abc
from ginkgo_server.backtest.enums import MarketType
from ginkgo_server.backtest.events import (
    SignalEvent,
    MarketEvent,
    FillEvent,
    OrderEvent,
)
from ginkgo_server.backtest.strategy.base_strategy import BaseStrategy
from ginkgo_server.backtest.matcher.base_matcher import BaseMatcher
from ginkgo_server.backtest.analyzer.base_analyzer import BaseAnalyzer
from ginkgo_server.backtest.risk.base_risk import BaseRisk
from ginkgo_server.backtest.sizer.base_sizer import BaseSizer
from ginkgo_server.backtest.event_engine import EventEngine


class BaseBroker(metaclass=abc.ABCMeta):
    """
    经纪人基类
    """

    def __init__(
        self,
        name,
        engine,
        *,
        init_capitial=100000,
    ):
        self._name = name
        self._engine = engine
        self._init_capitial = init_capitial  # 设置初始资金
        self._total_capitial = 0
        self._capitial = 0
        self.get_cash(init_capitial)  # 入金
        self._freeze = 0
        self._strategies = []  # 策略池
        self._sizer = None
        self._matcher = None
        self._analyzer = None
        self.position = {}  # 存放Position对象
        self.trade_history = []
        # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    def __repr__(self):
        s = "=" * 20 + "\n"
        # TODO
        s += f"{self._name} "
        s += "\n" + f"初始资金：{self._init_capitial}，"
        s += "\n" + f"总资金：{self._total_capitial}，"
        s += "\n" + f"可用现金：{self._capitial}，"
        s += "\n" + f"仓位控制：{self._sizer._name if self._sizer else 'None'}"
        s += "\n" + f"成交撮合：{self._matcher._name if self._matcher else 'None'}"
        s += "\n" + f"分析评价：{self._analyzer._name if self._analyzer else 'None'}"
        s += "\n" + "注册策略："
        for i in self._strategies:
            s += "\n"
            s += str(i)
        s += "\n" + "当前持仓："
        for i in self.position:
            s += "\n"
            s += str(self.position[i])
        return s

    def strategy_register(self, strategy: BaseStrategy):
        """
        策略注册

        :param strategy: 根据MarketEvent做出信号判断的策略
        :type strategy: BaseStrategy
        """
        if strategy not in self._strategies:
            self._strategies.append(strategy)
            strategy.engine_register(self._engine)
            print(f"{strategy.name} 已注册")
            # TODO 用Log替换，同时本地存储
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
        # self._matcher.engine_register(self._engine)

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
            self._capitial += cash
            self._total_capitial += cash
            print(f"{self._name}「入金」{cash}，目前持有现金「{self._capitial}」")
        else:
            print("Cash should above 0.")

    def freeze_money(self, money):
        """
        冻结现金，准备买入
        """
        self._capitial -= money
        self._freeze += money

    def add_position(self, position):
        """
        添加持仓

        若是已经持有会直接添加至已有持仓内
        """
        code = position.code
        # 判断是否已经持有改标的
        if code in self.position.keys():
            # 已经持有则执行Position的买入操作
            self.position[code].buy(price=position.price, volume=position.volume)
        else:
            # 未持有则添加持仓至position
            self.position[code] = position
