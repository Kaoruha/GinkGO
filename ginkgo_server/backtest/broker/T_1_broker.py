from ginkgo_server.backtest.broker.base_broker import BaseBroker
from ginkgo_server.backtest.events import EventType, DealType, InfoType
from ginkgo_server.backtest.postion import Position


class T1Broker(BaseBroker):
    def __init__(
        self,
        engine,
        *,
        name="T+1 经纪人",
        init_capitial=100000,
    ):
        super(T1Broker, self).__init__(
            engine=engine, name=name, init_capitial=init_capitial
        )

    def market_handler(self, event):
        # 市场事件的日期超过当前日期才会进行后续操作
        if event.info_type == InfoType.DailyPrice:
            if not self.update_date(event.date):
                print("事件日期异常，不进行任何操作，请检查代码")
                return
            self.update_price(code=event.code, data=event.data)
            print("处理DayBar")

        if event.info_type == InfoType.MinutePrice:
            if not self.update_time(event.time):
                print("事件时间异常，不进行任何操作，请检查代码")
                return
            self.update_price(code=event.code, data=event.data)
            print("处理Min5")

        for i in self._strategies:
            i.get_price(event)

    def signal_handler(self, signal):
        order = self._sizer.get_signal(signal=signal, broker=self)
        if order is not None:
            return order
            self._engine.put(order)

    def order_handler(self, event):
        # TODO Price 怎么传给Matcher??
        if event.code not in self.current_price.keys():
            print(f"没有{event.code}的当前价格信息，请检查代码")
            return
        result = self._matcher.try_match(
            order=event, broker=self, price=self.current_price[event.code]
        )
        for i in result:
            # TODO 根据事件类型分别处理？
            print(i)

    def fill_handler(self, event):
        if event.done:
            # 交易成功的处理
            if event.deal == DealType.BUY:
                # 交易成功的买单处理
                p = Position(code=event.code, price=event.price, volume=event.volume)
                self.add_position(p)
                self._freeze -= event.freeze
                self._capitial += event.remain
                self._total_capitial -= event.fee
            elif event.deal == DealType.SELL:
                # 交易成功的卖单处理
                if event.code not in self.position.keys():
                    print("未持仓却交易成功，请检查代码")
                self.position[event.code].sell(volume=event.volume, done=True)
                self._capitial += event.price * event.volume
                self._total_capitial += event.price * event.volume
                self.check_position()
        else:
            # 交易失败的处理
            if event.deal == DealType.BUY:
                self._freeze -= event.freeze
                self._capitial += event.freeze
            if event.deal == DealType.SELL:
                self.position[event.code].sell(volume=event.volume, done=False)

    def general_handler(self, event):
        pass
