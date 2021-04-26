from ginkgo_server.backtest.broker.base_broker import BaseBroker
from ginkgo_server.backtest.events import EventType, DealType
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
        pass

    def signal_handler(self, event):
        order = self._sizer.get_signal(signal=event, broker=self)
        if order is not None:
            return order
            self._engine.put(order)

    def order_handler(self, event):
        # TODO Price 怎么传给Matcher??
        # self._matcher.try_match(order=event,broker=self,price=?)
        pass

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
