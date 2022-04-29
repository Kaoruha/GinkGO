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
            ("testsendorder2", Direction.BEAR, OrderStatus.CREATED, 4),
            ("testsendorder3", Direction.BULL, OrderStatus.CREATED, 5),
            ("testsendorder4", Direction.BEAR, OrderStatus.CANCELLED, 5),
            ("testsendorder5", Direction.BULL, OrderStatus.SUBMITED, 5),
        ]
        for i in param:
            count = 0
            o = OrderEvent(code=i[0], direction=i[1], status=i[2])
            m.get_order(o)
            m.send_order(o)
            for k in m.order_list.values():
                for j in k:
                    if j.status == OrderStatus.SUBMITED:
                        count += 1
            self.assertEqual(first={"count": i[3]}, second={"count": count})

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

    def test_CalPriceMarket_OK(self):
        m = self.reset()
        params = [
            # 0isbull, 1targetvolume,2open,3close,4high,5low,6result(price,volume)
            (True, 1000, 10, 10, 11, 10, (10.5, 1000)),
        ]
        for i in params:
            r = m.cal_price_market(
                is_bull=i[0],
                target_volume=i[1],
                open=i[2],
                close=i[3],
                high=i[4],
                low=i[5],
            )
            self.assertEqual(first=r, second=i[6])

    def test_CalPriceLimit_OK(self):
        m = self.reset()
        params = [
            # 0isbull,1targetprice, 2targetvolume,3open,4close,5high,6low,7result(price,volume)
            (True, 10, 1000, 10, 10, 11, 10, (10, 1000)),
        ]
        for i in params:
            r = m.cal_price_limit(
                is_bull=i[0],
                target_price=i[1],
                target_volume=i[2],
                open=i[3],
                close=i[4],
                high=i[5],
                low=i[6],
            )
            self.assertEqual(first=r, second=i[7])
