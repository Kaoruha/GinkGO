import unittest
from ginkgo.backtest.price import Bar
from ginkgo.backtest.matcher.simulate_matcher import SimulateMatcher
from ginkgo.backtest.events import OrderEvent
from ginkgo.backtest.enums import Direction, Interval, OrderStatus, OrderType
from ginkgo.libs import GINKGOLOGGER as gl


class SimulateMatcherTest(unittest.TestCase):
    """
    撮合类单元测试
    """

    def __init__(self, *args, **kwargs) -> None:
        super(SimulateMatcherTest, self).__init__(*args, **kwargs)

    def reset(self) -> SimulateMatcher:
        return SimulateMatcher()

    def test_FeeCal_OK(self):
        gl.logger.critical("税费计算测试开始.")
        params = [
            # 0stamp, 1transfer,2commission,3 min,4direction,5price,6volume,7fee
            (0.001, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
            (0.002, 0.0002, 0.0003, 5, Direction.BULL, 1, 100, 5.02),
            (0.002, 0.0002, 0.0003, 5, Direction.BEAR, 10, 10000, 250),
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
        gl.logger.critical("税费计算测试完成.")

    def test_CalPriceMarket_OK(self):
        gl.logger.critical("市价交易测试开始.")
        m = self.reset()
        params = [
            # 0isbull, 1,code, 2targetvolume,3open,4close,5high,6low,7result(price,volume)
            (True,'teststock', 1000, 10, 11, 11, 10, (0, 0)),
            (False,'teststock', 1000, 10, 9, 10.1, 9, (0, 0)),
            (True,'teststock', 1000, 10, 10, 11, 10, (10.5, 1000)),
            (False,'teststock', 1000, 10, 10, 11, 10, (10.5, 1000)),
        ]
        for i in params:
            r = m.cal_price_market(
                code = i[1],
                is_bull=i[0],
                target_volume=i[2],
                open_=i[3],
                close=i[4],
                high=i[5],
                low=i[6],
            )
            self.assertEqual(first=r, second=i[7])
        gl.logger.critical("市价交易测试完成.")


    def test_CalPriceLimit_OK(self):
        gl.logger.critical("限价交易测试开始.")
        m = self.reset()
        params = [
            # 0isbull, 1targetprice, 2targetvolume, 3open, 
            # 4close, 5high, 6low, 7result(price,volume), 8code
            (True, 10, 1000, 10, 11, 11, 10, (0, 0), 'testlimitcode'), # 涨停想买
            (True, 10.5, 1000, 10, 10, 10.2, 9.7, (0, 0), 'testlimitcode'), # 超最高价
            (True, 9.8, 1000, 10, 9, 10.2, 9, (9.8, 1000), 'testlimitcode'), # 跌停买价高于平均
            (True, 9.3, 1000, 10, 9, 10.2, 9, (9.4, 1000), 'testlimitcode'), # 跌停买价低于平均
            (False, 10, 1000, 10, 9, 10.2, 9, (0, 0), 'testlimitcode'), # 跌停想卖
            (False, 8.5, 1000, 10, 9, 10.2, 9, (0, 0), 'testlimitcode'), # 超最低价
            (False, 9.8, 1000, 10, 10.4, 10.2, 9, (9.8, 1000), 'testlimitcode'), # 卖价低于平均价
            (False, 9.8, 1000, 10, 9.2, 10.2, 9, (9.7, 1000), 'testlimitcode'), # 卖价高于平均价
        ]
        for i in params:
            r = m.cal_price_limit(
                code=i[8],
                is_bull=i[0],
                target_price=i[1],
                target_volume=i[2],
                open_=i[3],
                close=i[4],
                high=i[5],
                low=i[6],
            )
            self.assertEqual(first=r, second=i[7])
        gl.logger.critical("限价交易测试完成.")

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



