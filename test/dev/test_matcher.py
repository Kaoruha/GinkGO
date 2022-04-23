"""
Author: Kaoru
Date: 2022-03-22 22:14:51
LastEditTime: 2022-04-20 23:54:53
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/dev/test_matcher.py
What goes around comes around.
"""
from typing import OrderedDict
import unittest
from src.backtest.price import Bar
from src.backtest.matcher.simulate_matcher import SimulateMatcher
from src.backtest.events import OrderEvent
from src.backtest.enums import Direction, Interval, OrderStatus, OrderType


class SimulateMatcherTest(unittest.TestCase):
    """
    撮合类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SimulateMatcherTest, self).__init__(*args, **kwargs)

    def reset(self) -> SimulateMatcher:
        return SimulateMatcher()

    def test_SimMatcherGetOrder_OK(self):
        m = self.reset()
        param = [
            # 0code, 1direction, 2status, 3orderlistcount
            ("testgetorder1", Direction.BULL, OrderStatus.CREATED, 1),
            ("testgetorder2", Direction.BEAR, OrderStatus.CREATED, 2),
            ("testgetorder3", Direction.BULL, OrderStatus.CREATED, 3),
            ("testgetorder4", Direction.BULL, OrderStatus.CANCELLED, 3),
            ("testgetorder5", Direction.BULL, OrderStatus.SUBMITED, 3),
        ]
        for i in param:
            o = OrderEvent(code=i[0], direction=i[1], status=i[2])
            r = m.get_order(o)
            self.assertEqual(first={"count": i[3]}, second={"count": r})

    def test_SimMatcherSendOrder_OK(self):
        m = self.reset()
        param = [
            # 0code, 1direction, 2status, 3orderlistcount
            ("testsendorder1", Direction.BULL, OrderStatus.CREATED, 1),
            ("testsendorder1", Direction.BULL, OrderStatus.CREATED, 2),
            ("testsendorder1", Direction.BEAR, OrderStatus.CREATED, 3),
            ("testsendorder1", Direction.BULL, OrderStatus.SUBMITED, 3),
            ("testsendorder2", Direction.BEAR, OrderStatus.CREATED, 1),
            ("testsendorder3", Direction.BULL, OrderStatus.CREATED, 1),
            ("testsendorder4", Direction.BEAR, OrderStatus.CANCELLED, 0),
            ("testsendorder5", Direction.BULL, OrderStatus.SUBMITED, 0),
        ]
        for i in param:
            o = OrderEvent(code=i[0], direction=i[1], status=i[2])
            r = m.send_order(o)
            self.assertEqual(first={"count": i[3]}, second={"count": r})

    def test_FeeCal_OK(self):
        params = [
            # 0stamp, 1transfer,2commission,3 min,4direction,5price,6volume,7fee
            (0.001, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
            (0.002, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
            # TODO 需要更多的边界值
        ]
        for i in params:
            m = SimulateMatcher(
                stamp_tax_rate=i[0],
                transfer_fee_rate=i[1],
                commission_rate=i[2],
                min_commission=i[3],
            )
            f = m.fee_cal(direction=i[4], price=i[5], volume=i[6])
            self.assertEqual(first=i[7], second=f)

    def test_SimMatcherSIMMatch_OK(self):
        order_params = [
            # 0code, 1direction, 2type, 3price, 4volume
            ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1000),
        ]
        bar_params = [
            # 0code, 1 interval, 2 open, 3close, 4high, 5low, 6volume, 7 turnover
            ("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23),
        ]
        m = self.reset()
        for i in order_params:
            order = OrderEvent(
                code=i[0], direction=i[1], order_type=i[2], price=i[3], volume=i[4]
            )
            bar = Bar(code=i[0])
            f = m.sim_match_order(order=order, bar=bar)

    def test_SimMatcherTryMatch_OK(self):
        pass

    def test_SimMatcherGetResult_OK(self):
        pass
