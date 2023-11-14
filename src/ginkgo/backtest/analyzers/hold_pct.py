from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer


class HoldPCT(BaseAnalyzer):
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(HoldPCT, self).__init__(name, *args, **kwargs)
