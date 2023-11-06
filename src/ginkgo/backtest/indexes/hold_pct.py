from ginkgo.backtest.indexes.base_index import BaseIndex


class HoldPCT(BaseIndex):
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(HoldPCT, self).__init__(name, *args, **kwargs)
