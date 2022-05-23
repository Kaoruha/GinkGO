from ginkgo.backtest.broker.base_broker import BaseBroker
from ginkgo.backtest.events import EventType, Direction
from ginkgo.backtest.postion import Position
from ginkgo.backtest.enums import MarketEventType
from ginkgo.backtest.events import MarketEvent, SignalEvent, FillEvent, OrderEvent
from ginkgo.libs import GINKGOLOGGER as gl


class SimT1Broker(BaseBroker):
    @property
    def today(self):
        return self.trade_day[self.trade_day_index]

    def __init__(
        self,
        engine=None,
        data_engine=None,
        sim_matcher=None,
        start_date="1999-07-26",
        end_date="2021-07-26",
        *,
        name="T+1 经纪人",
        init_capital=100000,
    ) -> None:
        super(SimT1Broker, self).__init__(
            engine=engine, name=name, init_capital=init_capital
        )
        self.data_engine = data_engine  # 数据引擎
        self.sim_matcher = sim_matcher  # 模拟成交
        self.trade_day_index = -1  # 交易日索引
        self.trade_day = gm.get_trade_day()
        self.trade_day = self.trade_day[
            (self.trade_day >= start_date) & (self.trade_day <= end_date)
        ]

    def __repr__(self) -> str:
        s = f"{self.name} "
        s += f"当前日期：{self.datetime}， "
        s += f"初始资金：{self.init_capital}，"
        s += f"总资金：{self.total_capital}， "
        s += f"可用现金：{self.capital}， "
        s += f"冻结金额：{self.frozen_capital}, "
        s += f"仓位控制：{self.sizer.name if self.sizer else 'None'}, "
        s += f"成交撮合：{self.matcher.name if self.matcher else 'None'}, "
        s += f"分析评价：{len(self.analyzers)}"
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

    def market_handler_(self, event: MarketEvent) -> None:
        """
        市场事件的处理
        """
        # 市场事件的日期超过当前日期才会进行后续操作
        if event.market_event_type == MarketEventType.NEWS:
            pass
        elif event.market_event_type == MarketEventType.BAR:
            # 策略
            for i in self.strategies:
                signals = i.get_price(event, self)
                if signals:
                    for j in signals:
                        self.engine.put(j)
            # 更新价格
            if event.code in self.positions:
                self.positions[event.code].update_last_price(flaot(event.raw.close))
        elif event.market_event_type == MarketEventType.TICK:
            pass
        gl.logger.info(f"{event.date} {event.code} {self.total_capital}")

    def signal_handler(self, signal: SignalEvent) -> OrderEvent:
        """
        信号事件的处理
        """
        # 先检查信号事件里的标的当天是否有成交量，如果没有，把信号推回给
        volume, price = self.sizer.cal_size(
            event=event, capital=self.capital, positions=self.positions
        )
        if volume <= 0:
            return

        order = OrderEvent(
            code=signal.code,
            direction=signal.direction,
            order_type=OrderType.MARKET,
            volume=volume,
            price=price,
            reference_price=price,
            source=Source.B1Broker,
            datetime=self.today,
        )
        self.engine.put(order)

    def order_handler(self, event: OrderEvent) -> None:
        """
        订单事件的处理
        """
        # TODO 日期检查

        if order.direction == Direction.BULL:
            if not self.freeze_money(order.reference_price * order.volume):
                gl.logger.warn(f"{self.today} 现金不够，无法开仓")
                return
        elif order.direction == Direction.BEAR:
            if event.code not in self.positions:
                gl.logger.warn(f"{self.today} 未持有{event.code} 无法卖出")
                return
            p = self.positions[event.code]
            if not p.freeze_position(event.volume):
                gl.logger.warn(f"{self.today} {event.code} 无法冻结{ event.volume} 份额")
                reutrn

        self.matcher.get_order(order=event)

    def fill_handler(self, event: FillEvent) -> None:
        """
        成交事件的处理
        """
        if event.price == 0 or event.volume == 0:
            # 失败的成交
            # TODO 添加记录
            return
        if event.direction == Direction.BULL:
            # 买入成功
            if event.code in self.positions:
                self.positions[event.code].update(
                    datetime=event.datetime, volume=event.volume, price=event.price
                )
            else:
                self.positions[event.code] = Position(
                    code=event.code,
                    name=event.code,
                    price=event.price,
                    volume=event.volume,
                    datetime=event.datetime,
                )
                self.restore_money(event.money_remain)

        elif event.direction == Direction.BEAR:
            # 卖出失败
            if event.code not in self.positions:
                gl.logger.error(f"未持有 {event.code}，卖出操作失败，回测有误，请检查代码")
                return

            # 卖出成功
            self.positions[event.code].update(
                datetime=event.datetime, volume=-event.volume, price=event.price
            )
            self.restore_frozen_position(
                code=event.code, volume=event.volume, datetime=event.datetime
            )
            self.restore_money(event.money_remain)

    def general_handler(self, event):
        """
        通用事件的处理
        """
        for i in self.analyzers:
            i.record(self)

    def next(self):
        super(SimT1Broker, self).next()
