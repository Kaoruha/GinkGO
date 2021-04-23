from ginkgo_server.backtest.broker.base_broker import BaseBroker


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
