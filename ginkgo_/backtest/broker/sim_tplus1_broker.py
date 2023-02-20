from ginkgo.backtest.broker.base_broker import BaseBroker
from ginkgo.backtest.events import EventType, Direction
from ginkgo.backtest.postion import Position
from ginkgo.backtest.enums import MarketEventType, OrderType, Source
from ginkgo.backtest.events import (
    Event,
    MarketEvent,
    SignalEvent,
    FillEvent,
    OrderEvent,
)
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


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
        self.trade_day = gm.get_trade_day()
        self.trade_day = self.trade_day[
            (self.trade_day >= start_date) & (self.trade_day <= end_date)
        ]

    def __repr__(self) -> str:
        s = f"{self.name} "
        s += f"当前日期：{self.today}， "
        s += f"初始资金：{self.init_capital}，"
        s += f"总资金：{self.total_capital}， "
        s += f"可用现金：{self.capital}， "
        s += f"冻结金额：{self.frozen_capital}, "
        s += f"仓位控制：{self.sizer.name if self.sizer else 'None'}, "
        s += f"成交撮合：{self.matcher.name if self.matcher else 'None'}, "
        s += f"分析评价：{len(self.analyzers)}, "
        for i in self.analyzers:
            s += i.name + ","
        s += f"注册策略：{len(self.strategies)}, "
        for i in self.strategies:
            s += "   "
            s += str(i)
        s += f"当前持仓：{len(self.positions)}, "
        for i in self.positions:
            s += "  "
            s += str(self.positions[i])
        return s

    def __engine_put(self, event: Event) -> None:
        if self.engine:
            self.engine.put(event)
        else:
            gl.logger.warn(f"引擎未注册")

    def market_handler(self, event: MarketEvent) -> None:
        """
        市场事件的处理
        """
        # 市场事件的日期超过当前日期才会进行后续操作
        if event.market_event_type == MarketEventType.NEWS:
            # 新闻事件处理>>>
            pass
            # 新闻事件处理<<<
        elif event.market_event_type == MarketEventType.BAR:
            # Bar处理>>>

            # 把最新价格发送给模拟成交
            if self.matcher:
                self.matcher.get_bar(event.raw)
            else:
                gl.logger.warn(f"撮合器未注册")

            # 更新持仓价格
            if event.code in self.positions:
                self.positions[event.code].update_last_price(
                    price=float(event.raw.close_price), datetime=event.datetime
                )

            # 把价格信息发送给策略，尝试生成信号
            for i in self.strategies:
                signals = i.get_price(event, self)
                if signals:
                    for j in signals:
                        self.__engine_put(j)

            # Bar处理<<<
        elif event.market_event_type == MarketEventType.TICK:
            # Tick处理>>>
            pass
            # Tick处理<<<
        gl.logger.info(f"{event.datetime} 获取「{event.code}」Bar信息")

    def signal_handler(self, event: SignalEvent) -> OrderEvent:
        """
        信号事件的处理
        """
        # 先检查信号事件里的标的当天是否有成交量，如果没有，把信号推回给
        volume, price = self.sizer.cal_size(
            signal=event, capital=self.capital, positions=self.positions
        )
        if volume <= 0 or price <= 0:
            gl.logger.warn(f"价格「{price}」或购买量「{volume}」小于0，请检查Sizer计算函数")
            return

        if event.direction == Direction.BULL:
            if volume * price > self.capital:
                gl.logger.warn(f"{self.today} 现金不够，无法开仓")
                return
        elif event.direction == Direction.BEAR:
            if event.code not in self.positions:
                gl.logger.warn(f"{self.today} 未持有{event.code} 无法卖出")
                return
            av = self.positions[event.code].avaliable_volume
            if volume > av:
                gl.logger.warn(
                    f"{self.today} {event.code} 可用份额「{av}」< 「{event.volume}」 "
                )
                return
        else:
            pass

        order = OrderEvent(
            code=event.code,
            direction=event.direction,
            order_type=OrderType.MARKET,
            price=price,
            volume=volume,
            reference_price=price,
            source=Source.T1Broker,
            datetime=self.today,
        )
        self.__engine_put(order)
        return order

    def order_handler(self, event: OrderEvent) -> None:
        """
        订单事件的处理
        """
        # TODO 日期检查

        if event.direction == Direction.BULL:
            if not self.freeze_money(event.price * event.volume):
                gl.logger.warn(f"{self.today} 现金不够，无法开仓")
                return
        elif event.direction == Direction.BEAR:
            if event.code not in self.positions:
                gl.logger.warn(f"{self.today} 未持有{event.code} 无法卖出")
                return
            p = self.positions[event.code]
            if not p.freeze_position(event.volume):
                gl.logger.warn(f"{self.today} {event.code} 无法冻结{ event.volume} 份额")
                return

        self.matcher.get_order(order=event)

    def fill_handler(self, event: FillEvent) -> None:
        """
        成交事件的处理
        """
        if event.price == 0 or event.volume == 0:
            # 失败的成交
            # TODO 添加记录
            return
        money = event.price * event.volume + event.fee
        if event.direction == Direction.BULL:
            # Try cal frozen_capital
            if not self.reduce_frozen_capital(money=money):
                return
            # 买入成功
            if event.code in self.positions:
                self.positions[event.code].update(
                    datetime=event.datetime, volume=event.volume, price=event.price
                )
            else:
                """
                Add the position
                """
                self.positions[event.code] = Position(
                    code=event.code,
                    name=event.code,
                    price=event.price,
                    volume=event.volume,
                    datetime=event.datetime,
                )

        elif event.direction == Direction.BEAR:
            # 卖出失败
            if event.code not in self.positions:
                gl.logger.error(f"未持有 {event.code}，卖出操作失败，回测有误，请检查代码")
                return

            # 卖出成功
            if not self.restore_frozen_position(
                code=event.code, volume=event.volume, datetime=event.datetime
            ):
                return

            self.positions[event.code].update(
                datetime=event.datetime, volume=-event.volume, price=event.price
            )
            self.capital += event.money_remain

    def general_handler(self, event):
        """
        通用事件的处理
        """
        for i in self.analyzers:
            i.record(self)

    def next(self):
        super(SimT1Broker, self).next()
