import abc
import queue
import pandas as pd
from ginkgo.backtest.enums import Direction, MarketType
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
from ginkgo.backtest.selector.base_selector import BaseSelector
from ginkgo.backtest.painter.base_painter import BasePainter
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.backtest.postion import Position
from ginkgo.backtest.price import Bar
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


class BaseBroker(abc.ABC):
    """
    经纪人基类
    """

    @property
    def positions_value(self):
        """
        持仓总价值
        """
        r = 0
        for i in self.positions.values():
            r += i.market_value
        return r

    @property
    def total_capital(self):
        """
        总资金
        """
        return self.capital + self.frozen_capital + self.positions_value

    def __init__(
        self,
        engine=None,
        name="base_broker",
        *,
        init_capital=100000,
    ) -> None:
        self.name = name  # 经纪人名称
        self.engine = engine  # 挂载引擎
        self.init_capital = init_capital  # 设置初始资金
        self.capital = init_capital  # 当前资金
        self.frozen_capital = 0  # 冻结资金
        self.strategies = []  # 策略池
        self.risk_management = []  # 风控策略池
        self.selector = None  # 股票筛选器
        self.sizer = None  # 仓位控制
        self.matcher = None  # 撮合器
        self.analyzers = []  # 分析
        self.painter = None  # 制图
        self.positions = {}  # 存放Position对象
        self.trade_history = pd.DataFrame(
            columns=[
                "datetime",
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
        self.market_type = MarketType.CN  # 当前市场
        self.trade_day_index = 0  # 交易日索引

    def __repr__(self) -> str:
        s = f"{self.name} "
        s += f"初始资金：{self.init_capital}，"
        s += f"总资金：{self.total_capital}， "
        s += f"可用现金：{self.capital}， "
        s += f"冻结金额：{self.frozen_capital}, "
        s += f"仓位控制：{self.sizer.name if self.sizer else 'None'}, "
        s += f"成交撮合：{self.matcher.name if self.matcher else 'None'}, "
        s += f"分析评价："
        for i in self.analyzers:
            s += i.name + ","
        s += f"注册策略：{len(self.strategies)} "
        for i in self.strategies:
            s += "   "
            s += str(i)
        s += f"当前持仓：{len(self.positions)}"
        for i in self.positions:
            s += "  "
            s += str(self.positions[i])
        return s

    def selector_register(self, selector: BaseSelector) -> None:
        """
        选股器注册
        """
        if not isinstance(selector, BaseSelector):
            gl.logger.warn(f"只有选股类实例可以被注册，{type(selector)} 类型不符")
            return
        self.selector = selector

    def strategy_register(self, strategy: BaseStrategy) -> None:
        """
        策略注册
        """
        if not isinstance(strategy, BaseStrategy):
            gl.logger.warn(f"只有策略类实例可以被注册为策略，{type(strategy)} 类型不符")
            return
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            strategy.engine_register(self.engine)
            gl.logger.info(f"策略{strategy.name} 注册完成")
        else:
            gl.logger.warning(f"{strategy.name} 已存在")

    def sizer_register(self, sizer: BaseSizer) -> None:
        """
        仓位控制策略注册
        """
        if not isinstance(sizer, BaseSizer):
            gl.logger.warn(f"只有仓位控制类实例可以被注册为仓位管理，{type(sizer)} 类型不符")
            return
        self.sizer = sizer

    def risk_register(self, risk: BaseRisk) -> None:
        """
        风控策略注册
        """
        if not isinstance(risk, BaseRisk):
            gl.logger.warn(f"只有风控类实例可以被注册为风控管理，{type(risk)} 类型不符")
            return
        if risk not in self.risk_management:
            self.risk_management.append(risk)
            risk.engine_register(self.engine)
            gl.logger.info(f"{risk.name} 注册完成")
        else:
            gl.logger.warning(f"{risk.name} 已存在")

    def matcher_register(self, matcher: BaseMatcher) -> None:
        """
        撮合匹配器绑定
        """
        # 撮合类、匹配器绑定
        if not isinstance(matcher, BaseMatcher):
            gl.logger.warn(f"只有撮合器类实例可以被注册为撮合器，{type(matcher)} 类型不符")
            return
        self.matcher = matcher
        if self.engine:
            self.matcher.engine_register(self.engine)
            gl.logger.info(f"撮合器{matcher.name}注册完成")
        else:
            gl.logger.error("撮合器引擎绑定失败，请检查代码")

    def analyzer_register(self, analyzer: BaseAnalyzer) -> None:
        """
        撮合匹配器绑定
        """
        # 撮合类、匹配器绑定
        if not isinstance(analyzer, BaseAnalyzer):
            gl.logger.warn(f"只有分析类实例可以被注册为分析模块，{type(analyzer)} 类型不符")
            return
        if analyzer in self.analyzers:
            gl.logger.warn(f"{analyzer} 已经存在")
            return
        self.analyzers.append(analyzer)

    def painter_register(self, painter: BasePainter) -> None:
        """
        绘图器绑定
        """
        if not isinstance(painter, BasePainter):
            gl.logger.warn(f"只有绘图类实例可以被注册为绘图模块，{type(painter)} 类型不符")
            return
        # 绘图器绑定
        self.painter = painter
        gl.logger.info("绘图器绑定")

    def market_handler(self, event: MarketEvent) -> None:
        """
        市场事件处理函数
        判断市场事件合法性（主要针对回测模式）
        将价格事件推送给撮合器
        将市场事件推送给所有策略
        将市场事件推送给所有风控
        将所有策略与风控产生的信号，存入信号队列
        """
        raise NotImplementedError("Must implement market_handler()")

    def signal_handler(self, event: SignalEvent) -> None:
        """
        信号事件处理函数
        将信号、当前资金、持仓传入仓位控制
        """
        raise NotImplementedError("Must implement signal_handler()")

    def order_handler(self, event: OrderEvent) -> None:
        """
        订单事件处理函数
        将订单推送给撮合器
        """
        raise NotImplementedError("Must implement order_handler()")

    def fill_handler(self, event: FillEvent) -> None:
        """
        成交事件处理函数
        如果成交成功，则增加持仓，扣除使用掉的金额，还原剩余的的金额
        如果成交失败，则还原冻结的金额
        """
        raise NotImplementedError("Must implement fill_handler()")

    def general_handler(self) -> None:
        """
        通用事件处理函数
        可以做分析模块的固定调用，以及绘图模块的固定调用
        """
        raise NotImplementedError("Must implement general_handler()")

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

    def freeze_money(self, money) -> bool:
        """
        冻结现金，准备买入
        返回剩余现金
        """
        if isinstance(money, int):
            money = float(money)
        if not isinstance(money, float):
            gl.logger.error(f"冻结金额应该是一个数值，{type(money)}类型不符，请检查代码")
            return False

        if money > self.capital:
            gl.logger.error(f"冻结金额大于当前现金，{money}>{self.capital},冻结失败，请检查代码")
            return False

        if money < 0:
            gl.logger.error(f"冻结金额应当大于0，{money} < 0,冻结失败，请检查代码")
            return False

        self.capital -= money
        self.frozen_capital += money
        gl.logger.info(
            f"{self.name}冻结现金「{format(money,',')}」，目前持有现金「{format(self.capital,',')}」,目前冻结金额「{format(self.frozen_capital, ',')}」"
        )
        return True

    def restore_money(self, money: float) -> float:
        self.capital += money
        self.frozen_capital -= money
        gl.logger.info(
            f"{self.name}恢复冻结现金「{format(money,',')}」，目前持有现金「{format(self.capital,',')}」,目前冻结金额「{format(self.frozen_capital, ',')}」"
        )

    def add_position(self, code: str, datetime: str, price: float, volume: int):
        """
        添加持仓

        若是已经持有会直接添加至已有持仓内
        """
        if not isinstance(volume, int):
            gl.logger.error(f"持仓量应该是整型，{type(volume)}{volume}类型不符合")
            return self.positions

        if isinstance(price, int):
            price = float(price)

        if not isinstance(price, float):
            gl.logger.error(f"持仓价格应该是浮点数，{type(price)}{price}类型不符合")
            return self.positions

        # 判断是否已经持有该标的
        if code in self.positions.keys():
            # 已经持有则执行Position的买入操作
            self.positions[code].update(price=price, volume=volume, datetime=datetime)
            gl.logger.info(f"{datetime} 增加持仓 {code}")
            gl.logger.info(self.positions[code])
        else:
            # 未持有则添加持仓至position
            p = Position(code=code, price=price, volume=volume, datetime=datetime)
            gl.logger.info(f"{datetime} 新增持仓「{code}」P「{p.last_price}」 V「{p.volume}」")
            self.positions[code] = p
        return self.positions

    def freeze_position(self, code: str, volume: int, datetime: str):
        """
        冻结持仓
        """
        if code not in self.positions.keys():
            gl.logger.error(f"当前经纪人未持有{code}，无法冻结，请检查代码")
            return self.positions

        self.positions[code].freeze_position(volume=volume, datetime=datetime)
        gl.logger.info(f"{datetime} 冻结{code}持仓{volume}股")
        gl.logger.info(self.positions[code])
        return self.positions

    def restore_frozen_position(
        self, code: str, volume: int, datetime: str
    ) -> Position:
        """
        恢复冻结持仓
        """
        if code not in self.positions.keys():
            gl.logger.warn(f"当前经纪人未持有{code}，无法解除冻结，请检查代码")
            return
        if volume <= 0:
            gl.logger.warn(f"头寸解除冻结份额应该大于0")
            return self.positions[code]
        self.positions[code].unfreeze_sell(volume=volume)
        return self.positions[code]

    def reduce_position(self, code: str, volume: int, datetime: str) -> bool:
        """
        成功卖出后，减少持仓
        """
        if code not in self.positions.keys():
            gl.logger.warn(f"当前经纪人未持有{code}，无法减少持仓，请检查代码")
            return False

        if volume > 0:
            volume = -volume

        self.positions[code].update(volume=volume, datetime=datetime)
        self.clean_position()
        return True

    def clean_position(self):
        """
        清理持仓
        将空的持仓清除出持仓列表
        """
        clean_list = []
        for k in self.positions:
            total = self.positions[k].volume
            if total == 0:
                clean_list.append(k)
            if total < 0:
                gl.logger.error(f"{k}持仓异常，回测有误，请检查代码")
        for i in clean_list:
            self.positions.pop(i)
        return self.positions

    def update_price(self, code: str, datetime: str, price: float):
        """
        更新持仓价格
        """
        if code not in self.positions.keys():
            gl.logger.warn(f"当前经纪人未持有{code}")
            return self.positions
        self.positions[code].update_last_price(price=price, datetime=datetime)
        gl.logger.info(f"{datetime} {code}价格更新为 {price}")

    def add_history(self, fill_event: FillEvent):
        """
        添加交易记录
        """
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

    def next(self) -> bool:
        """
        根据交易日，进入下一个时间
        """

        self.trade_day_index += 1

        if self.trade_day_index >= len(self.trade_day):
            gl.logger.warn(f"{self.today} 是数据最后一天，回测结束")
            gl.logger.warn(f"{self.today} 是数据最后一天，回测结束")
            if self.engine:
                self.engine.stop()
            else:
                return False

            # TODO Call Analyzor.End()
        else:
            codes = []
            if self.selector:
                codes = self.selector.get_result(today=self.today)
            # GOTO NEXT DAY
            self.today = self.trade_day.iloc[self.trade_day_index]
            gl.logger.info(f"日期变更，{self.today} 已经到了")

            for i in self.positions.keys():
                if i not in codes:
                    codes.append(i)

            if self.engine:
                for i in codes:
                    self.engine.get_price(code=i, date=self.today)
            else:
                gl.logger.error("Engine未注册")

            return True
