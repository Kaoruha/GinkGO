"""
经纪人类
"""
import abc
from tkinter.messagebox import NO
import pandas as pd
from src.backtest.enums import Direction, MarketType
from src.backtest.events import (
    SignalEvent,
    MarketEvent,
    FillEvent,
    OrderEvent,
)
from src.backtest.strategy.base_strategy import BaseStrategy
from src.backtest.matcher.base_matcher import BaseMatcher
from src.backtest.analyzer.base_analyzer import BaseAnalyzer
from src.backtest.risk.base_risk import BaseRisk
from src.backtest.sizer.base_sizer import BaseSizer
from src.backtest.selector.base_selector import BaseSelector
from src.backtest.painter.base_painter import BasePainter
from src.backtest.event_engine import EventEngine
from src.libs import GINKGOLOGGER as gl
from src.backtest.postion import Position
from src.backtest.price import Bar
from src.data.ginkgo_mongo import ginkgo_mongo as gm


class BaseBroker(abc.ABC):
    """
    经纪人基类
    """

    @property
    def position_value(self):
        """
        持仓价值
        """
        r = 0
        for i in self.position.values():
            r += i.marker_value
        return r

    @property
    def total_capital(self):
        """
        总资金
        """
        return self.capital + self.frozen_capital + self.position_value

    def __init__(
        self,
        engine=None,
        name="base_broker",
        *,
        init_capital=100000,
        start_date="1999-07-26",
        end_date="2021-07-26",
    ) -> None:
        self.name = name  # 经纪人名称
        self.engine = engine  # 挂载引擎
        self.datetime = start_date  # 日期
        self.last_day = end_date  # 日期
        self.init_capital = init_capital  # 设置初始资金
        self.capital = init_capital  # 当前资金
        self.frozen_capital = 0  # 冻结资金
        self.strategies = []  # 策略池
        self.risk_management = []  # 风控策略池
        self.selector = None  # 股票筛选器
        self.sizer = None  # 仓位控制
        self.matcher = None  # 撮合器
        self.analyzer = []  # 分析
        self.painter = None  # 制图
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
        )
        # TODO 交易历史，需要单独抽象成一个类
        self.signals = []  # 信号队列
        self.market_type = MarketType.CN  # 当前市场
        self.trade_day = None  # 交易日

    def __repr__(self) -> str:
        s = f"{self.name} "
        s += f"当前日期：{self.datetime}， "
        s += f"初始资金：{self.init_capital}，"
        s += f"总资金：{self.total_capital}， "
        s += f"可用现金：{self.capital}， "
        s += f"冻结金额：{self.frozen_capital}, "
        s += f"仓位控制：{self.sizer.name if self.sizer else 'None'}, "
        s += f"成交撮合：{self.matcher.name if self.matcher else 'None'}, "
        s += f"分析评价：{self.analyzer.name if self.analyzer else 'None'}, "
        s += f"注册策略：{len(self.strategies)} "
        for i in self.strategies:
            s += "   "
            s += str(i)
        s += f"当前持仓：{len(self.position)}"
        for i in self.position:
            s += "  "
            s += str(self.position[i])
        return s

    def selector_register(self, selector: BaseSelector) -> None:
        """
        选股器注册

        :param selector: 负责股票筛选
        :type selector: BaseSelector
        """
        if not isinstance(selector, BaseSelector):
            gl.logger.warn(f"只有选股类实例可以被注册，{type(selector)} 类型不符")
            return
        self.selector = selector

    def strategy_register(self, strategy: BaseStrategy) -> None:
        """
        策略注册

        :param strategy: 根据MarketEvent做出信号判断的策略
        :type strategy: BaseStrategy
        """
        if not isinstance(strategy, BaseStrategy):
            gl.logger.warn(f"只有策略类实例可以被注册为策略，{type(strategy)} 类型不符")
            return
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            strategy.engine_register(self.engine)
            gl.logger.info(f"{strategy.name} 已注册")
        else:
            gl.logger.warning(f"{strategy.name} 已存在")

    def sizer_register(self, sizer: BaseSizer) -> None:
        """
        仓位控制策略注册

        :param sizer: 负责仓位控制的函数
        :type sizer: BaseSizer
        """
        if not isinstance(sizer, BaseSizer):
            gl.logger.warn(f"只有仓位控制类实例可以被注册为仓位管理，{type(sizer)} 类型不符")
            return
        self.sizer = sizer

    def risk_register(self, risk: BaseRisk) -> None:
        """
        风控策略注册

        :param risk: 负责资金池的风险控制
        :type risk: BaseRisk
        """
        if not isinstance(risk, BaseRisk):
            gl.logger.warn(f"只有风控类实例可以被注册为风控管理，{type(risk)} 类型不符")
            return
        if risk not in self.risk_management:
            self.risk_management.append(risk)
            risk.engine_register(self.engine)
            gl.logger.warning(f"{risk.name} 已注册")
        else:
            gl.logger.warning(f"{risk.name} 已存在")

    def matcher_register(self, matcher: BaseMatcher) -> None:
        """
        撮合匹配器绑定

        :param matcher: 负责撮合成交，回测为虚拟逻辑/实盘为真实异步多线程API调用监听
        :type matcher: BaseMatcher
        """
        # 撮合类、匹配器绑定
        if not isinstance(matcher, BaseMatcher):
            gl.logger.warn(f"只有撮合器类实例可以被注册为撮合器，{type(matcher)} 类型不符")
            return
        self.matcher = matcher
        if self.engine:
            self.matcher.engine_register(self.engine)
        else:
            gl.logger.error("撮合器引擎绑定失败，请检查代码")

    def analyzer_register(self, analyzer: BaseAnalyzer):
        """
        撮合匹配器绑定

        :param analyzer: 负责账户资金表现分析
        :type analyzer: BaseAnalyzer
        """
        # 撮合类、匹配器绑定
        if not isinstance(analyzer, BaseAnalyzer):
            gl.logger.warn(f"只有分析类实例可以被注册为分析模块，{type(analyzer)} 类型不符")
            return
        self.analyzer = analyzer

    def painter_register(self, painter: BasePainter):
        """
        绘图器绑定

        :param painter: 利用matplotlib绘图
        :type painter: BasePainter
        """
        if not isinstance(painter, BasePainter):
            gl.logger.warn(f"只有绘图类实例可以被注册为绘图模块，{type(painter)} 类型不符")
            return
        # 绘图器绑定
        self.painter = painter

    def market_handler(self, event: MarketEvent):
        """
        市场事件处理函数
        判断市场事件合法性（主要针对回测模式）
        将价格事件推送给撮合器
        将市场事件推送给所有策略
        将市场事件推送给所有风控
        将所有策略与风控产生的信号，存入信号队列

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement market_handler()")

    def signal_handler(self, event: SignalEvent):
        """
        信号事件处理函数
        将信号、当前资金、持仓传入仓位控制

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement signal_handler()")

    def order_handler(self, event: OrderEvent):
        """
        订单事件处理函数
        将订单推送给撮合器

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement order_handler()")

    def fill_handler(self, event: FillEvent):
        """
        成交事件处理函数
        如果成交成功，则增加持仓，扣除使用掉的金额，还原剩余的的金额
        如果成交失败，则还原冻结的金额

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement fill_handler()")

    def general_handler(self):
        """
        通用事件处理函数
        可以做分析模块的固定调用，以及绘图模块的固定调用

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement general_handler()")

    def get_new_price(self, event: MarketEvent) -> None:
        """
        获取到新的价格信息
        """
        # 更新日期
        self.today = event.date
        # 把价格信息传给每个策略
        for i in self.strategies:
            i.get_price(event)

    def get_cash(self, cash: float) -> float:
        """
        入金操作
        返回入金操作后的现金
        """
        # 入金金额只接受大于0的金额
        if not (isinstance(cash, float) or isinstance(cash, int)):
            gl.logger.error(f"入金应该是一个数值，{cash}类型不符，请检查代码")
            return self.capital
        if cash > 0:
            self.capital += cash
            self.init_capital += cash
            gl.logger.info(
                f"{self.name}「入金」{format(cash, ',')}，目前持有现金「{format(self.capital, ',')}」"
            )
        else:
            gl.logger.error(f"入金的金额{cash}应该大于0.")

        return self.capital

    def freeze_money(self, money) -> float:
        """
        冻结现金，准备买入
        返回剩余现金
        """
        if isinstance(money, int):
            money = float(money)
        if not isinstance(money, float):
            gl.logger.error(f"冻结金额应该是一个数值，{type(money)}类型不符，请检查代码")
            return self.capital

        if money > self.capital:
            gl.logger.error(f"冻结金额大于当前现金，{money}>{self.capital},冻结失败，请检查代码")
            return self.capital

        if money < 0:
            gl.logger.error(f"冻结金额应当大于0，{money} < 0,冻结失败，请检查代码")
            return self.capital

        self.capital -= money
        self.freeze += money
        return self.capital

    def add_position(self, position: Position):
        """
        添加持仓

        若是已经持有会直接添加至已有持仓内
        """
        # TODO 会被PositionManager的方法替代
        volume = position.volume
        price = position.cost
        code = position.code
        date = position.date
        if not isinstance(volume, int):
            gl.logger.error(f"持仓量应该是整型，{type(volume)}{volume}类型不符合")
            return self.position

        if isinstance(price, int):
            price = float(price)

        if not isinstance(price, float):
            gl.logger.error(f"持仓价格应该是浮点数，{type(price)}{price}类型不符合")
            return self.position

        # 判断是否已经持有该标的
        if code in self.position.keys():
            # 已经持有则执行Position的买入操作
            self.position[code].buy(cost=price, volume=volume, date=date)
            gl.logger.info(f"{date} 增加持仓 {code}")
            gl.logger.info(self.position[code])
        else:
            # 未持有则添加持仓至position
            p = Position(cost=price, volume=volume, date=date)
            gl.logger.info(f"{date} 新增持仓 {code}")
            gl.logger.info(p)
            self.position[code] = p
        return self.position

    def freeze_position(self, code: str, volume: int, date: str):
        """
        冻结持仓
        """
        if code not in self.position.keys():
            gl.logger.error(f"当前经纪人未持有{code}，无法冻结，请检查代码")
            return self.position

        self.position[code].pre_sell(volume=volume, date=date)
        gl.logger.info(f"{date} 冻结{code}持仓{volume}股")
        gl.logger.info(self.position[code])
        return self.position

    def restore_frozen_position(self, code: str, volume: int, date: str):
        """
        恢复冻结持仓
        """
        if code not in self.position.keys():
            gl.logger.error(f"当前经纪人未持有{code}，无法解除冻结，请检查代码")
            return self.position

        self.position[code].sell(volume=volume, done=False, date=date)
        return self.position

    def reduce_position(self, code: str, volume: int, date: str):
        """
        减少持仓
        """
        if code not in self.position.keys():
            gl.logger.error(f"当前经纪人未持有{code}，无法减少持仓，请检查代码")
            return False, self.position

        self.position[code].sell(volume=volume, done=True, date=date)
        self.clean_position()
        return True, self.position

    def clean_position(self):
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
                gl.logger.error(f"{k}持仓异常，回测有误，请检查代码")
        for i in clean_list:
            self.position.pop(i)
        return self.position

    def update_price(self, price: Bar):
        """
        更新持仓价格
        """
        code = price.code
        date = price.datetime
        p = price.data.close
        if code not in self.position.keys():
            gl.logger.warn(f"当前经纪人未持有{code}")
            return self.position
        self.position[code].update_last_price(price=p, date=date)
        gl.logger.info(f"{date} {code}价格更新为 {p}")

    def add_history(self, fill_event: FillEvent):
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

    def buy(self, code, type, price, volume):
        pass

    def sell(self, code, type, price, volume):
        pass

    def next(self):
        """
        根据交易日，进入下一个时间
        """
        if self.trade_day is None:
            self.trade_day = gm.get_trade_day()

        df = self.trade_day[
            (self.trade_day > self.today) & (self.trade_day <= self.last_day)
        ]
        if df.empty:
            gl.logger.info(f"{self.today} 是数据最后一天，回测结束")
            self.engine.stop()
            # TODO Call Analyzor.End()
        else:
            codes = self.selector.get_result(today=self.today)
            # GOTO NEXT DAY
            self.today = df.iloc[0]
            gl.logger.info(f"日期变更，{self.today} 已经到了")

            for i in self.position.keys():
                if i not in codes:
                    codes.append(i)

            for i in codes:
                self.engine.get_price(code=i, date=self.today)
