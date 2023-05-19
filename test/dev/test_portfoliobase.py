import unittest

# import time
# import datetime
# import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.order import Order
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.backtest.portfolio import BasePortfolio

# from ginkgo.backtest.signal import Signal
# from ginkgo.data.models import MSignal
# from ginkgo.libs.ginkgo_conf import GINKGOCONF
# from ginkgo.data.ginkgo_data import GINKGODATA
# from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class PortfolioBaseTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def test_portfolio_init(self) -> None:
        p = BasePortfolio()
        self.assertEqual(True, True)

    def test_portfolio_checkpos(self) -> None:
        p = BasePortfolio()
        p.position = {"halo": 123}
        self.assertEqual(p._check_position("halo"), True)
        self.assertEqual(p._check_position("halo1"), False)
        self.assertEqual(p._check_position("ha"), False)

    def test_prebuy_limit(self) -> None:
        # 1
        p = BasePortfolio()
        p.cash = 10000
        rs = p.pre_buy_limit("test_code", 10.23, 200, "2020-01-01")
        self.assertEqual("test_code", rs.code)
        self.assertEqual(10.23, rs.limit_price)
        self.assertEqual(200, rs.volume)
        self.assertEqual(datetime_normalize("2020-01-01"), rs.timestamp)
        self.assertEqual(
            p.freeze,
            10.23 * 200 + cal_fee(DIRECTION_TYPES.LONG, 10.23 * 200, p.tax_rate),
        )
        self.assertEqual(
            p.cash,
            10000
            - cal_fee(DIRECTION_TYPES.LONG, 10.23 * 200, p.tax_rate)
            - 10.23 * 200,
        )
        # 2
        p = BasePortfolio()
        p.cash = 10000
