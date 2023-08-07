import unittest
from ginkgo import GLOG
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.order import Order
from ginkgo.backtest.strategies import StrategyBase
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

    def test_portfolio_addstrategy(self) -> None:
        p = BasePortfolio()
        s = StrategyBase()
        p.add_strategy(s)
        self.assertEqual(1, len(p.strategies))
        s2 = StrategyBase()
        p.add_strategy(s2)
        self.assertEqual(2, len(p.strategies))

    def test_portfolio_addposition(self) -> None:
        p = BasePortfolio()
        pos1 = Position("test_code", 10, 1000)
        p.add_position(pos1)
        r = p.position["test_code"]
        self.assertEqual("test_code", r.code)
        self.assertEqual(10, r.price)
        self.assertEqual(10, r.cost)
        self.assertEqual(1000, r.volume)
        pos2 = Position("test_code2", 20, 1000)
        p.add_position(pos2)
        print(p.position)
        self.assertEqual(2, len(p.position))

    def test_portfolio_timegoes(self) -> None:
        m = BasePortfolio()
        m.on_time_goes_by("20200101")
        self.assertEqual(datetime_normalize("20200101"), m.now)
        m.on_time_goes_by(20200103)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200101)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200103)
        self.assertEqual(datetime_normalize("20200103"), m.now)
        m.on_time_goes_by(20200111)
        self.assertEqual(datetime_normalize("20200111"), m.now)

    def test_portfolio_bindengine(self) -> None:
        pass

    def test_portfolio_addindex(self) -> None:
        pass

    def test_portfolio_indexread(self) -> None:
        pass

    def test_portfolio_putevent(self) -> None:
        pass


class PortfolioT1Test(unittest.TestCase):
    def __init__(self, *args, **kwargs) -> None:
        super(PortfolioT1Test, self).__init__(*args, **kwargs)

    def test_portfoliot1_init(self) -> None:
        pass

    def test_portfoliot1_onprice(self) -> None:
        pass

    def test_portfoliot1_onsignal(self) -> None:
        pass

    def test_portfoliot1_onorder(self) -> None:
        pass
