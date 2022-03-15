"""
经纪人类
"""
import abc
import pandas as pd
from ginkgo.backtest.enums import DealType, MarketType, InfoType
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

    # region Property
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def engine(self):
        return self.__engine

    @engine.setter
    def engine(self, value):
        self.__engine = value

    @property
    def date(self):
        return self.__date

    @date.setter
    def date(self, value):
        self.__date = value

    @property
    def time(self):
        return self.__time

    @time.setter
    def time(self, value):
        self.__time = value

    @property
    def init_capital(self):
        return self.__init_capital

    @init_capital.setter
    def init_capital(self, value):
        self.__init_capital = value

    @property
    def capital(self):
        return self.__capital

    @capital.setter
    def capital(self, value):
        self.__capital = value

    @property
    def freeze(self):
        return self.__freeze

    @freeze.setter
    def freeze(self, value):
        self.__freeze = value

    @property
    def strategies(self):
        return self.__strategies

    @strategies.setter
    def strategies(self, value):
        self.__strategies = value

    @property
    def risk_management(self):
        return self.__risk_management

    @risk_management.setter
    def risk_management(self, value):
        self.__risk_management = value

    @property
    def sizer(self):
        return self.__sizer

    @sizer.setter
    def sizer(self, value):
        self.__sizer = value

    @property
    def matcher(self):
        return self.__matcher

    @matcher.setter
    def matcher(self, value):
        self.__matcher = value

    @property
    def analyzer(self):
        return self.__analyzer

    @analyzer.setter
    def analyzer(self, value):
        self.__analyzer = value

    @property
    def painter(self):
        return self.__painter

    @painter.setter
    def painter(self, value):
        self.__painter = value

    @property
    def current_price(self):
        return self.__current_price

    @current_price.setter
    def current_price(self, value):
        self.__current_price = value

    @property
    def trade_history(self):
        return self.__trade_history

    @trade_history.setter
    def trade_history(self, value):
        self.__trade_history = value

    @property
    def wait_events(self):
        return self.__wait_events

    @wait_events.setter
    def wait_events(self, value):
        self.__wait_events = value

    @property
    def market_type(self):
        return self.__market_type

    @market_type.setter
    def market_type(self, value):
        self.__market_type = value

    # endregion

    def __init__(
        self,
        name,
        engine,
        *,
        init_capital=100000,
    ) -> None:
        self.name = name  # 经纪人名称
        self.engine = engine  # 挂载引擎
        self.date = None  # 日期
        self.time = None  # 时间
        self.init_capital = 0  # 设置初始资金
        self.capital = 0  # 当前资金
        self.total_capital = 0  # 总资金
        self.freeze = 0  # 冻结资金
        self.strategies = []  # 策略池
        self.risk_management = []  # 风控策略池
        self.sizer = None  # 仓位控制
        self.matcher = None  # 撮合器
        self.analyzer = None  # 分析
        self.painter = None  # 制图
        self.current_price = {}  # 存储获得的最新价格信息
        self.position = {}  # 存放Position对象
        self.trade_history = pd.DataFrame(
            columns=[
                "date",
                "code",
                "deal",
                "done",
                "price",
                "volume",
                "source",
                "fee",
            ],
        )  # 交易历史
        self.wait_events = []  # 事件等待队列, 用来推回事件引擎
        # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 当前市场

        self.get_cash(init_capital)  # 入金
        self.cal_total_capital()  # 计算总资金

    def __repr__(self) -> str:
        s = "=" * 20 + "\n"
        s += f"{self._name} "
        s += "\n" + f"当前日期：{self.date}，"
        s += "\n" + f"当前时间：{self.time}，"
        s += "\n" + f"初始资金：{self.init_capital}，"
        s += "\n" + f"总资金：{self.total_capital}，"
        s += "\n" + f"可用现金：{self.capital}，"
        s += "\n" + f"冻结金额：{self.freeze}"
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

    def strategy_register(self, strategy: BaseStrategy) -> None:
        """
        策略注册

        :param strategy: 根据MarketEvent做出信号判断的策略
        :type strategy: BaseStrategy
        """
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            strategy.engine_register(self.engine)
            print(f"{strategy.name} 已注册")
        else:
            print(f"{strategy.name} 已存在")

    def sizer_register(self, sizer: BaseSizer) -> None:
        """
        仓位控制策略注册

        :param sizer: 负责仓位控制的函数
        :type sizer: BaseSizer
        """
        self.sizer = sizer

    def risk_register(self, risk: BaseRisk) -> None:
        """
        风控策略注册

        :param risk: 负责资金池的风险控制
        :type risk: BaseRisk
        """
        if risk not in self.risk:
            risk.engine_register(self._engine)
            self.risk.append(risk)
            print(f"{risk.name} 已注册")  # TODO 用Log替换，同时本地存储
        else:
            print(f"{risk.name} 已存在")

    def matcher_register(self, matcher: BaseMatcher) -> None:
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self.matcher = matcher

    def analyzer_register(self, analyzer: BaseAnalyzer):
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self.analyzer = analyzer
        # self.analyzer.engine_register(self._engine)

    def painter_register(self, painter: BasePainter):
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        self.painter = painter

    def market_handler_(self, event: MarketEvent):
        """
        市场事件处理函数

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement market_handler()")

    def market_handler(self, event: MarketEvent):
        self.market_handler_(event=event)

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

    def get_cash(self, cash: float) -> float:
        """
        入金操作
        返回入金操作后的现金
        """
        # 入金金额只接受大于0的金额
        if cash > 0:
            self.capital += cash
            self.init_capital += cash
            self.cal_total_capital()
            print(
                f"{self.name}「入金」{format(cash,',')}，目前持有现金「{format(self.capital,',')}」"
            )
        else:
            print("Cash should above 0.")

        return self.capital

    def freeze_money(self, money) -> float:
        """
        冻结现金，准备买入
        返回剩余现金
        """
        self.capital -= money
        self.freeze += money
        return self.capital

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

    def update_date(self, new_date) -> bool:
        """
        日期更新

        如果日期更新成功返回True，如果新的日期位于当下日期更早的位置，更新失败，返回False
        """
        if self.date is None or self.date <= new_date:
            self.date = new_date
            return True
        else:
            return False

    def update_time(self, new_time) -> bool:
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
        更新价格信息
        """
        self.current_price[code] = data

    def cal_total_capital(self) -> float:
        """
        计算总资金
        """
        stock = 0

        for i in self.position.keys():
            price = float(self.current_price[i].data.close)
            stock += price * (self.position[i].volume + self.position[i].freeze)
        self.total_capital = self.capital + self.freeze + stock

        return self.total_capital

    def add_trade_to_history(self, fill_event: FillEvent):
        df = pd.DataFrame(
            {
                "date": [fill_event.date],
                "code": [fill_event.code],
                "deal": [fill_event.deal.value],
                "done": [fill_event.done],
                "price": [fill_event.price],
                "volume": [fill_event.volume],
                "source": [fill_event.source],
                "fee": [fill_event.fee],
            }
        )
        self.trade_history = self.trade_history.append(df, ignore_index=True)