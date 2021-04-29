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
            # print("处理DayBar")

        if event.info_type == InfoType.MinutePrice:
            if not self.update_time(event.data.time):
                print("事件时间异常，不进行任何操作，请检查代码")
                return
            self.update_price(code=event.data.code, data=event.data)
            # print("处理Min5")

        for i in self._strategies:
            signals = i.get_price(event)
            if signals:
                for i in signals:
                    self._engine.put(i)

        for i in self.hold_orders:
            self._engine.put(i)
        self.hold_orders = []  # TODO 回头换成queue

    def signal_handler(self, signal):
        order = self._sizer.get_signal(signal=signal, broker=self)
        if order is not None:
            # return order  # 测试用，回头要删掉这行
            self._engine.put(order)

    def order_handler(self, event):
        if event.code not in self.current_price.keys():
            print(f"没有{event.code}的当前价格信息，请检查代码")
            return

        # 检查价格信息的日期是否在订单事件日期之后
        if str(self.current_price[event.code].data.date) <= str(event.date):
            print("需要在订单事件生成的第二天才可以进行撮合尝试")
            event.source = "当天无法成交，Broker暂时持有Order待获取新Price时重新尝试"
            self.hold_orders.append(event)
            return

        self._matcher.try_match(
            order=event, broker=self, current_price=self.current_price
        )

        result = self._matcher.get_result(self.current_price)
        for i in result:
            if i.type_ == EventType.Order:
                self.hold_orders.append(i)
            if i.type_ == EventType.Fill:
                # return i  # TODO 测试用，回头要删掉
                self._engine.put(i)

    def fill_handler(self, event):
        if event.done:
            # 交易成功的处理
            if event.deal == DealType.BUY:
                # 交易成功的买单处理
                p = Position(code=event.code, price=event.price, volume=event.volume)
                self.add_position(p)
                self._freeze -= event.freeze
                self._capitial += event.remain
                self.cal_total_capitial()
            elif event.deal == DealType.SELL:
                # 交易成功的卖单处理
                if event.code not in self.position.keys():
                    print("未持仓却交易成功，请检查代码")
                self.position[event.code].sell(volume=event.volume, done=True)
                self._capitial += event.remain
                self.cal_total_capitial()
                self.check_position()
        else:
            # 交易失败的处理
            if event.deal == DealType.BUY:
                self._freeze -= event.freeze
                self._capitial += event.freeze
            if event.deal == DealType.SELL:
                self.position[event.code].sell(volume=event.volume, done=False)
        print(self)

    def general_handler(self, event):
        pass
