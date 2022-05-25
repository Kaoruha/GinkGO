import unittest
from ginkgo.backtest.broker.sim_tplus1_broker import SimT1Broker
from ginkgo.backtest.events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from ginkgo.backtest.price import Bar
from ginkgo.backtest.enums import *
from ginkgo.backtest.strategy.base_strategy import BaseStrategy
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

    def test_GetBar_OK(self):
        print("")
        gl.logger.critical("SIMBroker获取Bar信息测试开始.")
        broker = self.reset()
        params = [
            # 0code, 1open, 2close, 3high, 4low, 5volume, 6turnover,
            # 7yesterday_pct, 8datetime
            ("testcode", 10, 10.5, 10.6, 9.6, 10000, 0.2, 0.08, "2020-01-01"),
        ]
        for i in params:
            bar = Bar(
                code=i[0],
                open_price=i[1],
                close_price=i[2],
                high_price=i[3],
                low_price=i[4],
                volume=i[5],
                turnover=i[6],
                pct=i[7],
                datetime=i[8],
            )
            e = MarketEvent(
                code=i[0],
                raw=bar,
                markert_event_type=MarketEventType.BAR,
                datetime=i[8],
            )
            broker.market_handler(e)
            # 策略获取到价格信息
            # 持仓信息更新
            # 推送给模拟成交
        gl.logger.critical("SIMBroker获取Bar信息测试完成.")

    # def test_GetSignal_OK(self):
    #     print("")
    #     gl.logger.critical("SIMBroker获取信号信息测试开始.")
    #     # 仓位控制根据当前现金持仓，计算仓位
    #     # 生成订单信息，推送给事件引擎
    #     gl.logger.critical("SIMBroker获取信号信息测试完成.")

    # def test_GetOrder_OK(self):
    #     print("")
    #     gl.logger.critical("SIMBroker获取订单事件测试开始.")
    #     # 如果是多头订单，则冻结现金
    #     # 如果是空头订单，则冻结持仓
    #     # 讲订单发送给模拟成交
    #     gl.logger.critical("SIMBroker获取订单事件测试完成.")

    # def test_FillHandler(self):
    #     print("")
    #     gl.logger.critical("SIMBroker成交事件处理测试开始.")
    #     gl.logger.critical("SIMBroker成交事件处理测试完成.")

    # def test_GeneralHandler(self):
    #     print("")
    #     gl.logger.critical("SIMBroker通用事件处理测试开始.")
    #     gl.logger.critical("SIMBroker通用事件处理测试完成.")
