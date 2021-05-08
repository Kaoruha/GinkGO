"""
经纪人类
"""
import abc
from ginkgo.backtest.enums import MarketType, InfoType
from ginkgo.backtest.events import (
    SignalEvent,
    MarketEvent,
    FillEvent,
    OrderEvent,
)
from ginkgo.backtest.strategy.base_strategy import BaseStrategy
from ginkgo.backtest.matcher.base_matcher import BaseMatcher
from ginkgo.backtest.analyzer.base_analyzer import BaseAnalyzer
from ginkgo.backtest.risk.base_risk import BaseRisk
from ginkgo.backtest.sizer.base_sizer import BaseSizer
from ginkgo.backtest.painter.base_painter import BasePainter
from ginkgo.backtest.event_engine import EventEngine


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
        self.date = None
        self.time = None
        self._init_capitial = 0  # 设置初始资金
        self._capitial = 0
        self._total_capitial = 0
        self._freeze = 0
        self._strategies = []  # 策略池
        self._sizer = None
        self._matcher = None
        self._analyzer = None
        self._painter = None
        self.current_price = {}  # 存储获得的最新价格信息
        self.position = {}  # 存放Position对象
        self.trade_history = []
        self.hold_events = []
        # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

        self.get_cash(init_capitial)  # 入金
        self.cal_total_capitial()

    def __repr__(self):
        s = "=" * 20 + "\n"
        # TODO
        s += f"{self._name} "
        s += "\n" + f"当前日期：{self.date}，"
        s += "\n" + f"当前时间：{self.time}，"
        s += "\n" + f"初始资金：{self._init_capitial}，"
        s += "\n" + f"总资金：{self._total_capitial}，"
        s += "\n" + f"可用现金：{self._capitial}，"
        s += "\n" + f"冻结金额：{self._freeze}"
        s += "\n" + f"仓位控制：{self._sizer._name if self._sizer else 'None'}"
        s += "\n" + f"成交撮合：{self._matcher._name if self._matcher else 'None'}"
        s += "\n" + f"分析评价：{self._analyzer._name if self._analyzer else 'None'}"
        s += "\n" + f"注册策略：{len(self._strategies)}"
        for i in self._strategies:
            s += "\n    "
            s += str(i)
        s += "\n" + f"当前持仓：{len(self.position)}"
        for i in self.position:
            s += "\n    "
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
        # self._sizer.engine_register(self._engine)

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

    def painter_register(self, painter: BasePainter):
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self._painter = painter
        # self._analyzer.engine_register(self._engine)

    def market_handler(self, event: MarketEvent):
        """
        市场事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement market_handler()")

    def signal_handler(self, event: SignalEvent):
        """
        信号事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement signal_handler()")

    def order_handler(self, event: OrderEvent):
        """
        订单事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement order_handler()")

    def fill_handler(self, event: FillEvent):
        """
        成交事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement fill_handler()")

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
            self._init_capitial += cash
            self.cal_total_capitial()
            print(
                f"{self._name}「入金」{format(cash,',')}，目前持有现金「{format(self._capitial,',')}」"
            )
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

    def check_position(self):
        """
        清理持仓

        将空的持仓清除出持仓列表
        """
        clean_list = []
        for k in self.position:
            total = self.position[k].volume + self.position[k].freeze
            if total == 0:
                clean_list.append(k)
            if total < 0:
                print("持仓异常，请检查代码")
        for i in clean_list:
            self.position.pop(i)

    def update_date(self, new_date):
        """
        日期更新

        如果日期更新成功返回True，如果新的日期位于当下日期更早的位置，更新失败，返回False
        """
        if self.date is None or self.date <= new_date:
            self.date = new_date
            return True
        else:
            return False

    def update_time(self, new_time):
        """
        时间更新

        如果日期更新成功返回True，如果新的日期位于当下日期更早的位置，更新失败，返回False
        """
        # 先校验日期
        date = f"{new_time[:4]}-{new_time[4:6]}-{new_time[6:8]}"
        if self.update_date(date):
            # 日期通过再校验时间
            if self.time is None or self.time <= new_time:
                self.time = new_time
                return True
            else:
                return False
        else:
            return False

    def update_price(self, code, data):
        """
        获取价格信息处理
        """
        self.current_price[code] = data

    def cal_total_capitial(self):
        stock = 0

        for i in self.position.keys():
            price = float(self.current_price[i].data.close)
            stock += price * (self.position[i].volume + self.position[i].freeze)
        self._total_capitial = self._capitial + self._freeze + stock
