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

    # def test_SimMatcherGetOrder_OK(self):
    #     m = self.reset()
    #     param = [
    #         # 0code, 1direction, 2status, 3orderlistcount
    #         ("testgetorder1", Direction.BULL, OrderStatus.CREATED, 1),
    #         ("testgetorder2", Direction.BEAR, OrderStatus.CREATED, 2),
    #         ("testgetorder3", Direction.BULL, OrderStatus.CREATED, 3),
    #         ("testgetorder4", Direction.BULL, OrderStatus.CANCELLED, 3),
    #         ("testgetorder5", Direction.BULL, OrderStatus.SUBMITED, 3),
    #     ]
    #     for i in param:
    #         o = OrderEvent(code=i[0], direction=i[1], status=i[2])
    #         r = m.get_order(o)
    #         self.assertEqual(first={"count": i[3]}, second={"count": r})

    # def test_SimMatcherSendOrder_OK(self):
    #     m = self.reset()
    #     param = [
    #         # 0code, 1direction, 2status, 3orderlistcount
    #         ("testsendorder1", Direction.BULL, OrderStatus.CREATED, 1),
    #         ("testsendorder1", Direction.BULL, OrderStatus.CREATED, 2),
    #         ("testsendorder1", Direction.BEAR, OrderStatus.CREATED, 3),
    #         ("testsendorder1", Direction.BULL, OrderStatus.SUBMITED, 3),
    #         ("testsendorder2", Direction.BEAR, OrderStatus.CREATED, 4),
    #         ("testsendorder3", Direction.BULL, OrderStatus.CREATED, 5),
    #         ("testsendorder4", Direction.BEAR, OrderStatus.CANCELLED, 5),
    #         ("testsendorder5", Direction.BULL, OrderStatus.SUBMITED, 5),
    #     ]
    #     for i in param:
    #         count = 0
    #         o = OrderEvent(code=i[0], direction=i[1], status=i[2])
    #         m.get_order(o)
    #         m.send_order(o)
    #         for k in m.order_list.values():
    #             for j in k:
    #                 if j.status == OrderStatus.SUBMITED:
    #                     count += 1
    #         self.assertEqual(first={"count": i[3]}, second={"count": count})

    # def test_FeeCal_OK(self):
    #     params = [
    #         # 0stamp, 1transfer,2commission,3 min,4direction,5price,6volume,7fee
    #         (0.001, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
    #         (0.002, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
    #         # TODO 需要更多的边界值
    #     ]
    #     for i in params:
    #         m = SimulateMatcher(
    #             stamp_tax_rate=i[0],
    #             transfer_fee_rate=i[1],
    #             commission_rate=i[2],
    #             min_commission=i[3],
    #         )
    #         f = m.fee_cal(direction=i[4], price=i[5], volume=i[6])
    #         self.assertEqual(first=i[7], second=f)

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

    # def test_SimMatcherSIMMatch_OK(self):
    #     params = [
    #         # 0 0code, 1direction, 2type, 3price, 4volume
    #         # 1 0code, 1 interval, 2 open, 3close, 4high, 5low, 6volume, 7 turnover
    #         # 2 0price, 1volume
    #         # TODO 还需要更多的边界值
    #         (
    #             ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #             ("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23),
    #             (5, 1000),
    #         ),
    #         (
    #             ("testorder2", Direction.BULL, OrderType.LIMIT, 5, 100),
    #             ("testorder2", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23),
    #             (5, 100),
    #         ),
    #         (
    #             ("testorder1", Direction.BULL, OrderType.MARKET, 5, 500),
    #             ("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23),
    #             (5.15, 500),
    #         ),
    #     ]
    #     m = self.reset()
    #     for i in params:
    #         order = OrderEvent(
    #             code=i[0][0],
    #             direction=i[0][1],
    #             order_type=i[0][2],
    #             price=i[0][3],
    #             volume=i[0][4],
    #         )
    #         bar = Bar(
    #             code=i[1][0],
    #             interval=i[1][1],
    #             open_price=i[1][2],
    #             close_price=i[1][3],
    #             high_price=i[1][4],
    #             low_price=i[1][5],
    #             volume=i[1][6],
    #             turnover=i[1][7],
    #         )
    #         f = m.sim_match_order(order=order, bar=bar)
    #         self.assertEqual(
    #             first={"price": i[2][0], "volume": i[2][1]},
    #             second={"price": f.price, "volume": f.volume},
    #         )

    # def test_SimMatcherTryMatch_OK(self):
    #     order_params = [
    #         # 0 0code, 1direction, 2type, 3price, 4volume
    #         ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder1", Direction.BEAR, OrderType.MARKET, 5, 1000),
    #         ("testorder1", Direction.BEAR, OrderType.MARKET, 5, 1000),
    #         ("testorder2", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder2", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder3", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder4", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #     ]
    #     bar_params = [
    #         # 0 0code, 1 interval, 2 open, 3close, 4high, 5low, 6volume, 7 turnover
    #         # 1 count
    #         (("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 4),
    #         (("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 4),
    #         (("testorder2", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 2),
    #         (("testorder3", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 1),
    #         (("testorder5", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 0),
    #     ]
    #     for j in bar_params:
    #         m = self.reset()
    #         for i in order_params:
    #             o = OrderEvent(
    #                 code=i[0], direction=i[1], order_type=i[2], price=i[3], volume=i[4]
    #             )
    #             m.get_order(o)

    #         bar = Bar(
    #             code=j[0][0],
    #             interval=j[0][1],
    #             open_price=j[0][2],
    #             close_price=j[0][3],
    #             high_price=j[0][4],
    #             low_price=j[0][5],
    #             volume=j[0][6],
    #             turnover=j[0][7],
    #         )
    #         m.try_match(bar=bar)
    #         self.assertEqual(
    #             first={"fillevent": j[1]},
    #             second={"fillevent": len(m.match_list)},
    #         )

    # def test_SimMatcherGetResult_OK(self):
    #     order_params = [
    #         # 0 0code, 1direction, 2type, 3price, 4volume
    #         ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1000),
    #         ("testorder1", Direction.BULL, OrderType.LIMIT, 5, 1100),
    #         ("testorder1", Direction.BEAR, OrderType.MARKET, 5, 1200),
    #         ("testorder1", Direction.BEAR, OrderType.MARKET, 5, 1300),
    #         ("testorder2", Direction.BULL, OrderType.LIMIT, 5, 1400),
    #         ("testorder2", Direction.BULL, OrderType.LIMIT, 5, 1500),
    #         ("testorder3", Direction.BULL, OrderType.LIMIT, 5, 1600),
    #         ("testorder4", Direction.BULL, OrderType.LIMIT, 5, 1700),
    #     ]
    #     bar_params = [
    #         # 0 0code, 1 interval, 2 open, 3close, 4high, 5low, 6volume, 7 turnover
    #         # 1 count
    #         (("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 4),
    #         (("testorder1", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 4),
    #         (("testorder2", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 5),
    #         (("testorder3", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 6),
    #         (("testorder5", Interval.DAILY, 5, 5.2, 5.2, 4.8, 10000, 0.23), 6),
    #     ]
    #     for j in bar_params:
    #         m = self.reset()
    #         for i in order_params:
    #             o = OrderEvent(
    #                 code=i[0], direction=i[1], order_type=i[2], price=i[3], volume=i[4]
    #             )
    #             m.get_order(o)
    #             m.send_order(o)

    #         bar = Bar(
    #             code=j[0][0],
    #             interval=j[0][1],
    #             open_price=j[0][2],
    #             close_price=j[0][3],
    #             high_price=j[0][4],
    #             low_price=j[0][5],
    #             volume=j[0][6],
    #             turnover=j[0][7],
    #         )
    #         m.try_match(bar=bar)
    #         self.assertEqual(first=len(m.match_list), second=j[1])
    #         m.get_result()
    #         self.assertEqual(
    #             first={"result": len(m.result_list)},
    #             second={"result": j[1]},
    #         )
