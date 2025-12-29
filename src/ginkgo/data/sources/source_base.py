# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: GinkgoSourceBase数据源基类定义数据源的抽象接口和规范支持数据源开发支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






class GinkgoSourceBase(object):
    def __init__(self, *args, **kwargs):
        self._client = None

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value) -> None:
        self._client = value

    def connect(self, *args, **kwargs):
        raise NotImplementedError()
