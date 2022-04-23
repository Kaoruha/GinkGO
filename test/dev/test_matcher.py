"""
Author: Kaoru
Date: 2022-03-22 22:14:51
LastEditTime: 2022-04-20 23:54:53
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/test/dev/test_matcher.py
What goes around comes around.
"""
import unittest
from src.backtest.price import Bar
from src.backtest.matcher.simulate_matcher import SimulateMatcher
from src.backtest.events import OrderEvent
from src.backtest.enums import Direction, OrderStatus


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

    def test_SimMatcherTrySIMMatch_OK(self):
        pass

    def test_SimMatcherMatch_OK(self):
        pass

    def test_SimMatcherGetResult_OK(self):
        pass
