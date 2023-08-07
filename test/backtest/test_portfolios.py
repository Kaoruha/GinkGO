import unittest
from ginkgo import GLOG
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.order import Order
from ginkgo.libs.ginkgo_math import cal_fee
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.backtest.portfolios import BasePortfolio
from ginkgo.backtest.position import Position
from ginkgo.libs.ginkgo_math import cal_fee


class PortfolioBaseTest(unittest.TestCase):
    """
    UnitTest for Signal.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioBaseTest, self).__init__(*args, **kwargs)
        self.params = [
            {},
        ]

    def test_portfolio_init(self) -> None:
        p = BasePortfolio()
