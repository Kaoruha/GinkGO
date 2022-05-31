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
        print("")
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
        print("")
        gl.logger.critical("模拟市价交易测试开始.")
        m = self.reset()
        params = [
            # 0isbull, 1,code, 2targetvolume,3open,4close,5high,6low,7result(price,volume)
            (True, "teststock", 1000, 10, 11, 11, 10, (0, 0)),
            (False, "teststock", 1000, 10, 9, 10.1, 9, (0, 0)),
            (True, "teststock", 1000, 10, 10, 11, 10, (10.5, 1000)),
            (False, "teststock", 1000, 10, 10, 11, 10, (10.5, 1000)),
        ]
        for i in params:
            r = m.cal_price_market(
                code=i[1],
                is_bull=i[0],
                target_volume=i[2],
                open_=i[3],
                close=i[4],
                high=i[5],
                low=i[6],
            )
            self.assertEqual(first=r, second=i[7])
        gl.logger.critical("模拟市价交易测试完成.")

    def test_CalPriceLimit_OK(self):
        print("")
        gl.logger.critical("模拟限价交易测试开始.")
        m = self.reset()
        params = [
            # 0isbull, 1targetprice, 2targetvolume, 3open,
            # 4close, 5high, 6low, 7result(price,volume), 8code
            (True, 10, 1000, 10, 11, 11, 10, (0, 0), "testlimitcode"),  # 涨停想买
            (
                False,
                10.5,
                1000,
                10,
                10,
                10.2,
                9.7,
                (0, 0),
                "testlimitcode",
            ),  # 超最高价想买111111111111111
            (True, 9.8, 1000, 10, 9, 10.2, 9, (9.8, 1000), "testlimitcode"),  # 跌停买价高于平均
            (True, 9.3, 1000, 10, 9, 10.2, 9, (9.4, 1000), "testlimitcode"),  # 跌停买价低于平均
            (False, 10, 1000, 10, 9, 10.2, 9, (0, 0), "testlimitcode"),  # 跌停想卖
            (
                True,
                8.5,
                1000,
                10,
                9,
                10.2,
                9,
                (0, 0),
                "testlimitcode",
            ),  # 超最低价想买
            (
                False,
                9.8,
                1000,
                10,
                10.4,
                10.2,
                9,
                (9.8, 1000),
                "testlimitcode",
            ),  # 卖价低于平均价
            (
                False,
                9.8,
                1000,
                10,
                9.2,
                10.2,
                9,
                (9.7, 1000),
                "testlimitcode",
            ),  # 卖价高于平均价
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
        gl.logger.critical("模拟限价交易测试完成.")

    def test_SimMatcherGetOrder_OK(self):
        print("")
        gl.logger.critical("模拟获取订单测试开始.")
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
            count = 0
            for j in m.order_list.values():
                for h in j:
                    count += 1
            self.assertEqual(first={"count": i[3]}, second={"count": count})
        gl.logger.critical("模拟获取订单测试结束.")

    def test_SimMatcherSendOrder_OK(self):
        print("")
        gl.logger.critical("模拟发送订单测试开始.")
        m = self.reset()
        param = [
            # 0code, 1direction, 2status, 3orderlistcount
            ("testsendorder1", Direction.BULL, OrderStatus.CREATED, True),
            ("testsendorder1", Direction.BULL, OrderStatus.CREATED, True),
            ("testsendorder1", Direction.BEAR, OrderStatus.CREATED, True),
            ("testsendorder1", Direction.BULL, OrderStatus.SUBMITED, False),
            ("testsendorder2", Direction.BEAR, OrderStatus.CREATED, True),
            ("testsendorder3", Direction.BULL, OrderStatus.CREATED, True),
            ("testsendorder4", Direction.BEAR, OrderStatus.CANCELLED, False),
            ("testsendorder5", Direction.BULL, OrderStatus.SUBMITED, False),
        ]
        for i in param:
            o = OrderEvent(code=i[0], direction=i[1], status=i[2])
            m.get_order(o)
            result = m.send_order(o)
            self.assertEqual(first={"result": i[3]}, second={"result": result})
        gl.logger.critical("模拟订单测试结束.")

    def test_SimMatcherSimMatchOrder_OK(self):
        print("")
        gl.logger.critical("模拟撮合订单测试开始.")
        params = [
            # 0order
            # 0code, 1direction, 2type, 3price, 4volume
            # 1bar
            # 0code, 1open, 2close, 3hight, 4low
            # 2price, value
            # 3matchcount
            (
                ("testcode1", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
                ("testcode1", 10, 10.5, 10.6, 10),
                (10.3, 1000),
                1,
            ),  # 正常成交
            (
                ("testcode2", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
                ("testcode1", 10, 10.5, 10.6, 10),
                (0, 0),
                1,
            ),  # bar与order的code不符，撮合失败
            (
                ("testcode1", Direction.BEAR, OrderType.LIMIT, 10.2, 500),
                ("testcode1", 10, 10.5, 10.6, 10),
                (10.2, 500),
                2,
            ),  # 正常成交
        ]
        m = self.reset()
        for i in params:
            op = i[0]
            bp = i[1]
            order = OrderEvent(
                code=op[0], direction=op[1], order_type=op[2], price=op[3], volume=op[4]
            )
            bar = Bar(
                code=bp[0],
                open_price=bp[1],
                close_price=bp[2],
                high_price=bp[3],
                low_price=bp[4],
            )
            fill = m.sim_match_order(order=order, bar=bar)
            self.assertEqual(
                first={
                    "price": i[2][0],
                    "volume": i[2][1],
                    "match_count": i[3],
                },
                second={
                    "price": fill.price,
                    "volume": fill.volume,
                    "match_count": len(m.match_list),
                },
            )

        gl.logger.critical("模拟撮合订单测试结束.")

    def test_SimMatcherTryMatch_OK(self):
        # TODO
        print("")
        gl.logger.critical("模拟尝试撮合测试开始.")
        gl.logger.critical("模拟尝试撮合测试结束.")

    def test_SimMatcherGetResult_OK(self):
        print("")
        gl.logger.critical("模拟获取交易结果测试开始.")
        order_params = [
            # 0code, 1direction, 2type, 3price, 4volume
            ("testorder1", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
            ("testorder1", Direction.BEAR, OrderType.MARKET, 10.3, 500),
            ("testorder2", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
            ("testorder3", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
            ("testorder4", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
            ("testorder5", Direction.BULL, OrderType.LIMIT, 10.3, 1000),
        ]
        bar_params = [
            # ((0code, 1open, 2close, 3high, 4low), result_count)
            (("testorder1", 10, 10.5, 10.6, 10), 2),
            (("testorder2", 10, 10.5, 10.6, 10), 3),
            (("testorder2", 10, 10.5, 10.6, 10), 3),
            (("testorder3", 11, 10.5, 11, 10.4), 4),
        ]
        m = self.reset()

        # Get Orders
        for i in order_params:
            o = OrderEvent(code=i[0], direction=i[1], price=i[3], volume=i[4])
            r = m.get_order(o)
            count = 0
            for j in m.order_list.values():
                for h in j:
                    count += 1
            self.assertEqual(
                first={"result_count": 0}, second={"result_count": len(m.result_list)}
            )

        # Get Bars
        for i in bar_params:
            bar = Bar(
                code=i[0][0],
                open_price=i[0][1],
                close_price=i[0][2],
                high_price=i[0][3],
                low_price=i[0][4],
            )
            m.get_bar(bar=bar)
            m.get_result()
            self.assertEqual(
                first={"result_count": i[1]}, second={"result_count": len(m.match_list)}
            )

        gl.logger.critical("模拟获取交易结果测试结束.")

    def test_SimMatcherClear_OK(self):
        print("")
        gl.logger.critical("模拟清除历史记录测试开始.")
        gl.logger.critical("模拟清除历史记录测试结束.")
