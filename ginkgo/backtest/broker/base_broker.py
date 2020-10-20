"""
经纪人类
"""
from ginkgo.backtest.enums import MarketType
from ginkgo.backtest.strategy.base_strategy import BaseStrategy
from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.matcher.base_matcher import BaseMatcher
from ginkgo.backtest.risk.base_risk import BaseRisk
from ginkgo.backtest.event_engine import EventEngine
import abc


class BaseBroker(metaclass=abc.ABCMeta):
    """
    基础经纪人类
    回头改成抽象类
    """

    def __init__(self, name: str, engine: EventEngine, *, stamp_tax: float = .0015, fee: float = .00025,
                 init_capital: int = 100000):
        self.name = name
        self._engine = engine
        self._init_capital = init_capital  # 设置初始资金
        self._capital = init_capital  # 设置初始资金，默认100K
        self._freeze = 0
        self._strategy = []
        self._sizer = None
        self._matcher = None
        self._risk = []
        self.fee = 0 # 用来统计所有税费
        self.position = {}  # 存放Position
        self.trades = []  # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    def strategy_register(self, strategy: BaseStrategy):
        # 策略注册，目前经纪人只允许按照一种策略来进行操作,未来可能支持多种策略同时决策
        if strategy not in self._strategy:
            self._strategy.append(strategy)
            strategy.engine_register(self._engine)
            print(f'{strategy.name} 已注册')  # TODO 用Log替换，同时本地存储
        else:
            print(f'{strategy.name} 已存在')

    def sizer_register(self, sizer: BaseSizer):
        # 仓位控制注册
        self.sizer = sizer
        sizer.engine_register(self._engine)
        sizer.get_init_capital(self._init_capital)

    def risk_register(self, risk: BaseRisk):
        # 风控注册
        if risk not in self._risk:
            self._risk.append(risk)
            risk.engine_register(self._engine)
            print(f'{risk.name} 已注册')  # TODO 用Log替换，同时本地存储
        else:
            print(f'{risk.name} 已存在')

    def matcher_register(self, matcher: BaseMatcher):
        # 撮合类、匹配器绑定
        self._matcher = matcher
        matcher.engine_register(self._engine)

    def market_handlers(self):
        raise NotImplementedError("Must implement market_handlers()")

    def signal_handlers(self):
        raise NotImplementedError("Must implement signal_handlers()")

    def order_handlers(self):
        raise NotImplementedError("Must implement order_handlers()")

    def fill_handlers(self):
        raise NotImplementedError("Must implement fill_handlers()")

    def general_handler(self):
        raise NotImplementedError("Must implement general_handler()")
