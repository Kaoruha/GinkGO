import unittest

# import time
# import datetime
# import pandas as pd
from ginkgo.libs import GINKGOLOGGER as gl

# from ginkgo.backtest.signal import Signal
# from ginkgo.data.models import MSignal
# from ginkgo.libs.ginkgo_conf import GINKGOCONF
# from ginkgo.data.ginkgo_data import GINKGODATA
# from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.backtest.portfolio import BasePortfolio


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
        self.assertEqual(p.check_position("halo"), True)
        self.assertEqual(p.check_position("halo1"), False)
        self.assertEqual(p.check_position("ha"), False)
