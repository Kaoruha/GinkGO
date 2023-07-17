# import unittest
# from ginkgo import GLOG
# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.backtest.order import Order
# from ginkgo.libs.ginkgo_math import cal_fee
# from ginkgo.enums import DIRECTION_TYPES
# from ginkgo.backtest.portfolios import BasePortfolio
# from ginkgo.backtest.position import Position
# from ginkgo.libs.ginkgo_math import cal_fee


# class PortfolioBaseTest(unittest.TestCase):
#     """
#     UnitTest for Signal.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(PortfolioBaseTest, self).__init__(*args, **kwargs)
#         self.dev = False

#     def test_portfolio_init(self) -> None:
#         p = BasePortfolio()
#         self.assertEqual(True, True)

#     def test_portfolio_checkpos(self) -> None:
#         p = BasePortfolio()
#         p.position = {"halo": 123}
#         self.assertEqual(p._check_position("halo"), True)
#         self.assertEqual(p._check_position("halo1"), False)
#         self.assertEqual(p._check_position("ha"), False)

#     def test_prebuy_limit(self) -> None:
#         # 1
#         p = BasePortfolio()
#         p.cash = 10000
#         rs = p.pre_buy_limit("test_code", 10.23, 200, "2020-01-01")
#         self.assertEqual("test_code", rs.code)
#         self.assertEqual(10.23, rs.limit_price)
#         self.assertEqual(200, rs.volume)
#         self.assertEqual(datetime_normalize("2020-01-01"), rs.timestamp)
#         self.assertEqual(
#             p.frozen,
#             10.23 * 200 + cal_fee(DIRECTION_TYPES.LONG, 10.23 * 200, p.tax_rate),
#         )
#         self.assertEqual(
#             p.cash,
#             10000
#             - cal_fee(DIRECTION_TYPES.LONG, 10.23 * 200, p.tax_rate)
#             - 10.23 * 200,
#         )
#         # 2
#         p = BasePortfolio()
#         p.cash = 10000
#         rs = p.pre_buy_limit("test_code", 10.23, 2000, "2020-01-01")
#         self.assertEqual(rs, None)

#     def test_prebuy_market(self) -> None:
#         # 1
#         p = BasePortfolio()
#         p.cash = 10000
#         rs = p.pre_buy_market("test_code", 10000, "2020-01-01")
#         self.assertEqual(0, p.cash)
#         self.assertEqual(10000, p.frozen)
#         # 2
#         p = BasePortfolio()
#         p.cash = 10000
#         rs = p.pre_buy_market("test_code", 20000, "2020-01-01")
#         self.assertEqual(10000, p.cash)
#         self.assertEqual(0, p.frozen)

#     def test_buy_done(self) -> None:
#         # 1
#         p = BasePortfolio()
#         p.cash = 10000
#         p.frozen = 1000
#         p.buy_done("stest", 10, 100, 1000, 200)
#         self.assertEqual(0, p.frozen)
#         self.assertEqual(10200, p.cash)
#         self.assertEqual(10, p.position["stest"].price)

#     def test_buy_done(self) -> None:
#         # 1
#         p = BasePortfolio()
#         p.cash = 10000
#         p.frozen = 1000
#         p.buy_cancel(200)
#         self.assertEqual(800, p.frozen)
#         self.assertEqual(10200, p.cash)

#     def test_presell_limit(self) -> None:
#         # 1
#         p = BasePortfolio()
#         p.cash = 10000
#         p.position["test"] = Position("test", 10, 1000)
#         rs = p.pre_sell_limit("test", 11, 100, "2020-01-01")
#         self.assertEqual(10000, p.cash)
#         self.assertEqual(0, p.frozen)
#         self.assertEqual(11, rs.limit_price)
#         self.assertEqual(100, rs.volume)
#         self.assertEqual(100, p.position["test"].frozen)
#         self.assertEqual(900, p.position["test"].volume)

#     def test_presell_market(self) -> None:
#         p = BasePortfolio()
#         p.cash = 10000
#         p.position["test"] = Position("test", 10, 1000)
#         rs = p.pre_sell_market("test", 100, "2020-01-01")
#         self.assertEqual(10000, p.cash)
#         self.assertEqual(0, p.frozen)
#         self.assertEqual(100, rs.volume)
#         self.assertEqual(100, p.position["test"].frozen)
#         self.assertEqual(900, p.position["test"].volume)

#     def test_sold(self) -> None:
#         p = BasePortfolio()
#         p.cash = 10000
#         p.position["test"] = Position("test", 10, 1000)
#         p.pre_sell_market("test", 100, "2020-01-01")
#         p.sold("test", 100, 50)
#         self.assertEqual(
#             p.cash, 15000 - cal_fee(DIRECTION_TYPES.SHORT, 5000, p.tax_rate)
#         )
#         self.assertEqual(900, p.position["test"].volume)
#         self.assertEqual(50, p.position["test"].frozen)

#     def test_sell_cancel(self) -> None:
#         p = BasePortfolio()
#         p.cash = 10000
#         p.position["test"] = Position("test", 10, 1000)
#         p.pre_sell_market("test", 100, "2020-01-01")
#         p.sell_cancel("test", 50)
#         self.assertEqual(p.cash, 10000)
#         self.assertEqual(950, p.position["test"].volume)
#         self.assertEqual(50, p.position["test"].frozen)
