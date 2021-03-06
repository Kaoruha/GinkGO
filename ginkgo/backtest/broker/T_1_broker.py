from ginkgo.backtest.broker.base_broker import BaseBroker
from ginkgo.backtest.events import EventType, DealType, InfoType
from ginkgo.backtest.postion import Position


class T1Broker(BaseBroker):
    def __init__(
        self,
        engine,
        *,
        name="T+1 经纪人",
        init_capital=100000,
    ):
        super(T1Broker, self).__init__(
            engine=engine, name=name, init_capital=init_capital
        )

    def market_handler(self, event):
        # 市场事件的日期超过当前日期才会进行后续操作
        if event.info_type == InfoType.DailyPrice:
            if not self.update_date(event.date):
                print("事件日期异常，不进行任何操作，请检查代码")
                return
            self.update_price(code=event.code, data=event.data)
            if self._painter is not None:
                self._painter.get_price(broker=self, price=event.data)
            # print("处理DayBar")

        if event.info_type == InfoType.MinutePrice:
            if not self.update_time(event.data.time):
                print("事件时间异常，不进行任何操作，请检查代码")
                return
            self.update_price(code=event.data.code, data=event.data)
            # print("处理Min5")

        for i in self._strategies:
            signals = i.get_price(event, self)
            if signals:
                for i in signals:
                    self._engine.put(i)

        for i in self.hold_events:
            self._engine.put(i)
        self.hold_events = []  # TODO 回头换成queue
        self.cal_total_capital()
        print(f"{event.date} {event.code} {self._total_capital}")

    def signal_handler(self, signal):
        # 先检查信号事件里的标的当天是否有成交量，如果没有，把信号推回给
        if signal.code not in self.current_price.keys():
            print(f"目前已经价格信息内没有 {signal.code}的信息")
            return
        if self.current_price[signal.code].data.volume == 0:
            date = self.current_price[signal.code].data.date
            code = self.current_price[signal.code].data.code
            print(f"{date} {code} 没有成交量，会把信号事件重新推送至Hold")
            signal.date = date
            signal.source = "{date} {code} 无成交量，第二天再尝试处理信号事件"
            self.hold_events.append(signal)
            return
        order = self._sizer.get_signal(signal=signal, broker=self)
        if order is not None:
            # return order  # 测试用，回头要删掉这行
            self._engine.put(order)

    def order_handler(self, event):
        # 检查是否有对应Code的价格信息
        if event.code not in self.current_price.keys():
            print(f"没有{event.code}的当前价格信息，请检查代码")
            return

        # 检查价格信息的日期是否在订单事件日期之后
        current_date = str(self.current_price[event.code].data.date)
        if current_date <= str(event.date):
            print(f"{current_date} 需要在订单事件生成的第二天才可以进行撮合尝试")
            event.source = "当天无法成交，Broker暂时持有Order待获取新Price时重新尝试"
            self.hold_events.append(event)
            return

        self._matcher.try_match(
            order=event, broker=self, current_price=self.current_price
        )

        result = self._matcher.get_result(self.current_price)
        for i in result:
            if i.type_ == EventType.Order:
                self.hold_events.append(i)
            if i.type_ == EventType.Fill:
                # return i  # TODO 测试用，回头要删掉
                self._engine.put(i)

    def fill_handler(self, event):
        if event.done:
            # 交易成功的处理
            if event.deal == DealType.BUY:
                # 交易成功的买单处理
                p = Position(
                    code=event.code,
                    price=event.price,
                    volume=event.volume,
                    date=event.date,
                )
                self.add_position(p)
                self._freeze -= event.freeze
                self._capital += event.remain
                self.cal_total_capital()
            elif event.deal == DealType.SELL:
                # 交易成功的卖单处理
                if event.code not in self.position.keys():
                    print(f"{event.date} 未持仓却交易成功，请检查代码")
                    return
                self.position[event.code].sell(volume=event.volume, done=True)
                self._capital += event.remain
                self.cal_total_capital()
                self.check_position()
        else:
            # 交易失败的处理
            if event.deal == DealType.BUY:
                self._freeze -= event.freeze
                self._capital += event.freeze
            if event.deal == DealType.SELL:
                self.position[event.code].sell(volume=event.volume, done=False)
        # print(self._total_capital)

    def general_handler(self, event):
        pass
