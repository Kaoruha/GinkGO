from ginkgo_server.backtest.broker.base_broker import BaseBroker


class T1Broker(BaseBroker):
    def __init__(
        self,
        name,
        engine,
        *,
        init_capital=100000,
    ):
        super(T1Broker, self).__init__(
            name=name, engine=engine, init_capital=init_capital
        )
