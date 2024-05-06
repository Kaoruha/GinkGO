from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer


class HoldPCT(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(HoldPCT, self).__init__(name, *args, **kwargs)

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        pass
