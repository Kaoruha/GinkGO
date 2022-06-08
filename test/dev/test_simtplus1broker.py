import unittest
from ginkgo.backtest.broker.sim_tplus1_broker import SimT1Broker
from ginkgo.backtest.events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from ginkgo.backtest.sizer.full_sizer import FullSizer
from ginkgo.backtest.price import Bar
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
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

    # def test_GetBar_OK(self):
    #     print("")
    #     gl.logger.critical("SIMBroker获取Bar信息测试开始.")
    #     broker = self.reset()
    #     matcher = SimulateMatcher(name="测试模拟成交")
    #     broker.matcher_register(matcher=matcher)
    #     broker.add_position(
    #         code="testcode0", datetime="2020-01-01", price=5, volume=10000
    #     )
    #     params = [
    #         # 0code, 1open, 2close, 3high, 4low, 5volume, 6turnover,
    #         # 7yesterday_pct, 8datetime
    #         ("testcode0", 10, 10.5, 10.6, 9.6, 10000, 0.2, 0.08, "2020-01-01"),
    #         ("testcode0", 10.7, 11.1, 11.1, 10.5, 10000, 0.2, 0.08, "2020-01-02"),
    #     ]
    #     count = 0
    #     for i in params:
    #         bar = Bar(
    #             code=i[0],
    #             open_price=i[1],
    #             close_price=i[2],
    #             high_price=i[3],
    #             low_price=i[4],
    #             volume=i[5],
    #             turnover=i[6],
    #             pct=i[7],
    #             datetime=i[8],
    #         )
    #         e = MarketEvent(
    #             code=i[0],
    #             raw=bar,
    #             markert_event_type=MarketEventType.BAR,
    #             datetime=i[8],
    #         )
    #         broker.market_handler(e)
    #         count += 1
    #         # 持仓信息更新
    #         # 策略获取到价格信息
    #         # 推送给模拟成交
    #         if i[0] in broker.positions:
    #             p = broker.positions[i[0]].last_price
    #             self.assertEqual(first=p, second=i[2])
    #         self.assertEqual(first=count, second=matcher.bar_count)
    #     gl.logger.critical("SIMBroker获取Bar信息测试完成.")

    # def test_GetSignal_OK(self):
    #     print("")
    #     gl.logger.critical("SIMBroker获取信号信息测试开始.")
    #     # 仓位控制根据当前现金持仓，计算仓位
    #     sizer = FullSizer()
    #     broker = self.reset()
    #     broker.sizer_register(sizer)
    #     broker.add_position(
    #         code="testcode0", datetime="2020-01-01", price=5, volume=1000
    #     )
    #     gl.logger.debug("当前持仓Start" + "=" * 40)
    #     for i in broker.positions:
    #         gl.logger.debug(broker.positions[i])
    #     gl.logger.debug("当前持仓End" + "=" * 40)
    #     params = [
    #         # 0code,1direction,2datetime,3last_price
    #         ("testcode0", Direction.BULL, "2020-01-01", 10),
    #         ("testcode0", Direction.BULL, "2020-01-02", 11),
    #         ("testcode1", Direction.BULL, "2020-01-02", 11.5),
    #         ("testcode0", Direction.BEAR, "2020-01-01", 12),
    #     ]
    #     for i in params:
    #         s = SignalEvent(code=i[0], direction=i[1], datetime=i[2], last_price=i[3])
    #         o = broker.signal_handler(s)
    #         gl.logger.debug(o)

    #     for i in broker.positions:
    #         broker.positions[i].unfreeze_t1()

    #     for i in params:
    #         s = SignalEvent(code=i[0], direction=i[1], datetime=i[2], last_price=i[3])
    #         o = broker.signal_handler(s)
    #         gl.logger.debug(o)

    #     # 生成订单信息，推送给事件引擎
    #     gl.logger.critical("SIMBroker获取信号信息测试完成.")

    # def test_GetOrder_OK(self):
    #     print("")
    #     gl.logger.critical("SIMBroker获取订单事件测试开始.")
    #     # 如果是多头订单，则冻结现金
    #     params = [
    #         # 0code, 1direction, 2price, 3voluem, 4datetime
    #         ("testcode0", Direction.BULL, 10, 10000, "2020-01-01"),
    #         ("testcode0", Direction.BULL, 8, 10000, "2020-01-01"),
    #     ]
    #     for i in params:
    #         broker = self.reset()
    #         matcher = SimulateMatcher(name="单元测试模拟撮合")
    #         broker.matcher_register(matcher)
    #         o = OrderEvent(
    #             code=i[0],
    #             direction=i[1],
    #             order_type=OrderType.MARKET,
    #             price=i[2],
    #             volume=i[3],
    #             datetime=i[4],
    #         )
    #         broker.order_handler(o)
    #         gl.logger.debug(broker)
    #         self.assertEqual(first=broker.frozen_capital, second=float(i[2] * i[3]))

    #     # 如果是空头订单，则冻结持仓
    #     params = [
    #         # 0code, 1direction, 2price, 3voluem, 4datetime
    #         ("testcode0", Direction.BEAR, 10, 10000, "2020-01-01"),
    #     ]
    #     for i in params:
    #         broker = self.reset()
    #         matcher = SimulateMatcher(name="单元测试模拟撮合")
    #         broker.add_position(
    #             code="testcode0", datetime="2020-01-01", price=12, volume=20000
    #         )
    #         for j in broker.positions:
    #             broker.positions[j].unfreeze_t1()
    #         broker.matcher_register(matcher)
    #         o = OrderEvent(
    #             code=i[0],
    #             direction=i[1],
    #             order_type=OrderType.MARKET,
    #             price=i[2],
    #             volume=i[3],
    #             datetime=i[4],
    #         )
    #         broker.order_handler(o)
    #         gl.logger.debug(broker)
    #         # 如果是多头订单，则冻结现金
    #         if i[0] in broker.positions:
    #             self.assertEqual(first=i[3], second=broker.positions[i[0]].frozen_sell)
    #     # 讲订单发送给模拟成交
    #     gl.logger.critical("SIMBroker获取订单事件测试完成.")

    def test_FillHandler(self):
        print("")
        gl.logger.critical("SIMBroker成交事件处理测试开始.")
        params = [
            # 0code, 1direction, 2price, 3volume, 4fee, 5money
            ("testcode0", Direction.BULL, 10, 1000, 101.21, 21.5)
        ]
        b = self.reset()
        for i in params:
            fe = FillEvent(
                code=i[0],
                direction=i[1],
                price=i[2],
                volume=i[3],
                fee=i[4],
                money_remain=i[5],
            )
            b.fill_handler(fe)
            gl.logger.warn("Current Positions")
            for j in b.positions:
                gl.logger.debug(b.positions[j])
        gl.logger.critical("SIMBroker成交事件处理测试完成.")

    # def test_GeneralHandler(self):
    #     print("")
    #     gl.logger.critical("SIMBroker通用事件处理测试开始.")
    #     gl.logger.critical("SIMBroker通用事件处理测试完成.")
