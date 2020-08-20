"""
经纪人类
"""
from ginkgo.backtest.enums import MarketType
from ginkgo.backtest.strategy.base_strategy import BaseStrategy
from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.risk.base_risk import BaseRisk
from ginkgo.backtest.event_engine import EventEngine


class BaseBroker(object):
    """
    基础经纪人类
    回头改成抽象类
    """

    def __init__(self, name: str,engine:EventEngine, *, stamp_tax: float = .0015, fee: float = .00025, init_capital: int = 100000):
        self.name = name
        self._engine = engine
        self._stamp_tax = stamp_tax  # 设置印花税，默认千1.5
        self._fee = fee  # 设置交易税,默认万2.5
        self._capital = init_capital  # 设置初始资金，默认100K
        self._freeze = 0
        self._strategy = []
        self._sizer = None
        self._risk = []
        self.position = []  # 存放Position
        self.trades = []  # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    def strategy_register(self, strategy: BaseStrategy):
        # 策略注册，目前经纪人只允许按照一种策略来进行操作,未来可能支持多种策略同时决策
        if strategy not in self._strategy:
            self._strategy.append(strategy)
            strategy.engine_register(self._engine)
            # print(strategy.__engine)
            print(f'{strategy.name} 已注册')  # TODO 用Log替换，同时本地存储
        else:
            print(f'{strategy.name} 已存在')

    def sizer_register(self, sizer: BaseSizer):
        # 策略注册，目前经纪人只允许按照一种策略来进行操作
        self.sizer = sizer

    def risk_register(self, risk: BaseRisk):
        # 风控注册
        if risk not in self.risk:
            self.risk.append(risk)
            print(f'{risk.name} 已注册')  # TODO 用Log替换，同时本地存储
        else:
            print(f'{risk.name} 已存在')

    def market_handlers(self):
        raise NotImplementedError("Must implement market_handlers()")

    def signal_handlers(self):
        raise NotImplementedError("Must implement market_handlers()")

    def order_handlers(self):
        raise NotImplementedError("Must implement market_handlers()")

    def fill_handlers(self):
        raise NotImplementedError("Must implement market_handlers()")

    def general_handler(self):
        raise NotImplementedError("Must implement general_handler()")
