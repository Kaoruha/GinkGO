# Upstream: 各数据源子类(AKShare/BaoStock/TDX/Yahoo/Tushare)
# Downstream: 无外部依赖
# Role: 数据源抽象基类，定义connect()接口规范，所有外部数据源适配器均继承此类






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

