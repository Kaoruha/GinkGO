from ginkgo.backtest.signal import Signal


class StrategyBase(object):
    def cal(self, *args, **kwargs) -> Signal:
        raise NotImplemented
