from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG


class StrategyProfitLossLimit(StrategyBase):
    def __init__(self, *args, **kwargs):
        super(StrategyProfitLossLimit, self).__init__(*args, **kwargs)

    def cal(self, *args, **kwargs):
        GLOG.CRITICAL("Under Profit Loss Limit Calling...")
