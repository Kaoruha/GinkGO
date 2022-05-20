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
        print("")
        gl.logger.critical("SIMBroker市场事件处理测试开始.")
        gl.logger.critical("SIMBroker市场事件处理测试完成.")

    def test_SignalHandler(self):
        print("")
        gl.logger.critical("SIMBroker信号事件处理测试开始.")
        gl.logger.critical("SIMBroker信号事件处理测试完成.")

    def test_OrderHandler(self):
        print("")
        gl.logger.critical("SIMBroker订单事件处理测试开始.")
        gl.logger.critical("SIMBroker订单事件处理测试完成.")

    def test_FillHandler(self):
        print("")
        gl.logger.critical("SIMBroker成交事件处理测试开始.")
        gl.logger.critical("SIMBroker成交事件处理测试完成.")

    def test_GeneralHandler(self):
        print("")
        gl.logger.critical("SIMBroker通用事件处理测试开始.")
        gl.logger.critical("SIMBroker通用事件处理测试完成.")
