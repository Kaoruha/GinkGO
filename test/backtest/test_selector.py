import datetime
import uuid
import unittest
from ginkgo.backtest.selectors import BaseSelector, FixedSelector
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio


class BaseSelectorTest(unittest.TestCase):
    """
    UnitTest for BaseSelector.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(BaseSelectorTest, self).__init__(*args, **kwargs)

    def test_baseselector_init(self):
        s = BaseSelector()

    def test_baseselector_bind(self):
        p = BasePortfolio()
        s = BaseSelector()
        self.assertEqual(None, s.portfolio)
        s.bind_portfolio(p)
        self.assertNotEqual(None, s.portfolio)


class FixedSelectorTest(unittest.TestCase):
    """
    UnitTest for FixedSelector.
    """

    def __init__(self, *args, **kwargs) -> None:
        super(FixedSelectorTest, self).__init__(*args, **kwargs)

    def test_fixedselector_init(self):
        codes = ["halo", "nihao"]
        s = FixedSelector(codes)

    def test_fixedselector_pick(self):
        codes = ["halo", "nihao"]
        s = FixedSelector(codes)
        r = s.pick()
        self.assertEqual(2, len(r))
