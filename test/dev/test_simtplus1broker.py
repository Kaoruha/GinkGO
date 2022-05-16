import unittest
from ginkgo.backtest.broker.sim_tplus1_broker import SimT1Broker
from ginkgo.libs import GINKGOLOGGER as gl


class SimT1BrokerTest(unittest.TestCase):
    """
    模拟T+1经纪人
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SimT1BrokerTest, self).__init__(*args, **kwargs)

    def reset(self):
        b = SimT1Broker()
        return b

    def test_MarketHandler(self):
        pass

    def test_SignalHandler(self):
        pass

    def test_OrderHandler(self):
        pass

    def test_FillHandler(self):
        pass

    def test_GeneralHandler(self):
        pass
